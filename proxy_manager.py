# proxy_manager.py — Proxy pool management with rotation, failover, and health checks

import asyncio
import os
from dataclasses import dataclass, field
from typing import Optional

import httpx

from config import PROXIES_FILE, PROXY_MAX_FAILURES, PROXY_HEALTH_CHECK_TIMEOUT


@dataclass
class ProxyEntry:
    """Represents a single proxy with its health state."""
    url: str
    fail_count: int = 0
    is_active: bool = True
    last_error: Optional[str] = None


class ProxyManager:
    """
    Manages a pool of proxies with round-robin rotation, failure tracking,
    and health checking.

    Proxy sources (in priority order):
    1. PROXY_URL environment variable (single proxy)
    2. proxies.txt file (one proxy URL per line)

    If no proxies are configured, get_proxy() returns None and the
    TwitterClient falls back to a direct connection.
    """

    def __init__(self):
        self.proxies: list[ProxyEntry] = []
        self._current_index: int = 0
        self._load_proxies()

    def _load_proxies(self) -> None:
        """Load proxies from env var and/or proxies file."""
        loaded = []

        # Source 1: Single proxy from environment variable
        env_proxy = os.getenv("PROXY_URL")
        if env_proxy and env_proxy.strip():
            loaded.append(ProxyEntry(url=env_proxy.strip()))
            print(f"[PROXY] Loaded 1 proxy from PROXY_URL environment variable")

        # Source 2: Proxy pool from file
        if os.path.exists(PROXIES_FILE):
            with open(PROXIES_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        # Avoid duplicates if same URL is in both env and file
                        if not any(p.url == line for p in loaded):
                            loaded.append(ProxyEntry(url=line))
            file_count = len(loaded) - (1 if env_proxy else 0)
            if file_count > 0:
                print(f"[PROXY] Loaded {file_count} proxies from {PROXIES_FILE}")

        self.proxies = loaded

        if not self.proxies:
            print("[PROXY] No proxies configured -- using direct connection")
        else:
            print(f"[PROXY] Total proxies available: {len(self.proxies)}")

    def get_proxy(self) -> Optional[str]:
        """
        Get the next active proxy URL using round-robin rotation.
        Returns None if no proxies are configured or all are disabled.
        """
        if not self.proxies:
            return None

        active = [p for p in self.proxies if p.is_active]
        if not active:
            print("[PROXY] All proxies are disabled! Attempting to reset...")
            self._reset_all()
            active = [p for p in self.proxies if p.is_active]
            if not active:
                return None

        # Round-robin through active proxies
        self._current_index = self._current_index % len(active)
        proxy = active[self._current_index]
        self._current_index = (self._current_index + 1) % len(active)

        return proxy.url

    def mark_failed(self, proxy_url: str) -> None:
        """
        Record a failure for a proxy. Disables it after PROXY_MAX_FAILURES
        consecutive failures.
        """
        entry = self._find(proxy_url)
        if not entry:
            return

        entry.fail_count += 1
        if entry.fail_count >= PROXY_MAX_FAILURES:
            entry.is_active = False
            print(f"[PROXY] Proxy disabled after {PROXY_MAX_FAILURES} failures: {self._mask(proxy_url)}")
        else:
            print(
                f"[PROXY] Proxy failure {entry.fail_count}/{PROXY_MAX_FAILURES}: "
                f"{self._mask(proxy_url)}"
            )

    def mark_success(self, proxy_url: str) -> None:
        """Reset failure counter on successful use."""
        entry = self._find(proxy_url)
        if entry:
            entry.fail_count = 0
            entry.is_active = True

    async def health_check(self) -> dict:
        """
        Test all proxies against httpbin and return a status report.
        Returns a dict with overall status and per-proxy results.
        """
        if not self.proxies:
            return {"status": "no_proxies_configured", "proxies": []}

        results = []
        tasks = [self._check_single(p) for p in self.proxies]
        checked = await asyncio.gather(*tasks, return_exceptions=True)

        for proxy, result in zip(self.proxies, checked):
            if isinstance(result, Exception):
                results.append({
                    "proxy": self._mask(proxy.url),
                    "status": "error",
                    "error": str(result),
                    "is_active": proxy.is_active,
                    "fail_count": proxy.fail_count,
                })
            else:
                results.append(result)

        healthy = sum(1 for r in results if r["status"] == "healthy")
        return {
            "status": "ok" if healthy > 0 else "all_unhealthy",
            "total": len(self.proxies),
            "healthy": healthy,
            "unhealthy": len(self.proxies) - healthy,
            "proxies": results,
        }

    async def _check_single(self, entry: ProxyEntry) -> dict:
        """Health-check a single proxy against httpbin.org."""
        masked = self._mask(entry.url)
        try:
            async with httpx.AsyncClient(
                proxy=entry.url,
                timeout=PROXY_HEALTH_CHECK_TIMEOUT,
            ) as client:
                resp = await client.get("https://httpbin.org/ip")
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "proxy": masked,
                        "status": "healthy",
                        "external_ip": data.get("origin", "unknown"),
                        "is_active": entry.is_active,
                        "fail_count": entry.fail_count,
                    }
                else:
                    return {
                        "proxy": masked,
                        "status": "unhealthy",
                        "http_status": resp.status_code,
                        "is_active": entry.is_active,
                        "fail_count": entry.fail_count,
                    }
        except Exception as e:
            return {
                "proxy": masked,
                "status": "unhealthy",
                "error": str(e),
                "is_active": entry.is_active,
                "fail_count": entry.fail_count,
            }

    def get_status(self) -> dict:
        """Return current proxy pool status (no network calls)."""
        if not self.proxies:
            return {"configured": False, "total": 0, "active": 0}

        active = sum(1 for p in self.proxies if p.is_active)
        return {
            "configured": True,
            "total": len(self.proxies),
            "active": active,
            "disabled": len(self.proxies) - active,
            "proxies": [
                {
                    "proxy": self._mask(p.url),
                    "is_active": p.is_active,
                    "fail_count": p.fail_count,
                }
                for p in self.proxies
            ],
        }

    def _reset_all(self) -> None:
        """Reset all proxies to active (last resort when all are disabled)."""
        for p in self.proxies:
            p.fail_count = 0
            p.is_active = True
        print("[PROXY] All proxies reset to active")

    def _find(self, proxy_url: str) -> Optional[ProxyEntry]:
        """Find a proxy entry by URL."""
        for p in self.proxies:
            if p.url == proxy_url:
                return p
        return None

    @staticmethod
    def _mask(url: str) -> str:
        """Mask credentials in proxy URL for safe logging."""
        try:
            # http://user:pass@host:port -> http://***:***@host:port
            if "@" in url:
                scheme_and_creds, host_part = url.rsplit("@", 1)
                scheme = scheme_and_creds.split("://")[0]
                return f"{scheme}://***:***@{host_part}"
        except (ValueError, IndexError):
            pass
        return url