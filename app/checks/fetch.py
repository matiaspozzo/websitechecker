import asyncio
import time
from dataclasses import dataclass, field

import aiohttp

RETRY_BACKOFF_SECONDS = [5, 15, 30]


@dataclass
class FetchResult:
    ok: bool
    status: int | None = None
    body: str | None = None
    latency_ms: int | None = None
    final_url: str | None = None
    redirected: bool = False
    error: str | None = None


async def fetch_with_retry(http: aiohttp.ClientSession, url: str) -> FetchResult:
    """GET url, retrying up to len(RETRY_BACKOFF_SECONDS) times with backoff before
    giving up, to avoid declaring an incident on a single transient blip."""
    last_error: str | None = None
    delays = [0, *RETRY_BACKOFF_SECONDS]

    for i, delay in enumerate(delays):
        if delay:
            await asyncio.sleep(delay)
        start = time.monotonic()
        try:
            async with http.get(url, allow_redirects=True) as resp:
                body = await resp.text(errors="replace")
                latency_ms = int((time.monotonic() - start) * 1000)
                if resp.status >= 400:
                    last_error = f"HTTP {resp.status}"
                    if i < len(delays) - 1:
                        continue
                    return FetchResult(
                        ok=False,
                        status=resp.status,
                        body=body,
                        latency_ms=latency_ms,
                        final_url=str(resp.url),
                        redirected=bool(resp.history),
                        error=last_error,
                    )
                return FetchResult(
                    ok=True,
                    status=resp.status,
                    body=body,
                    latency_ms=latency_ms,
                    final_url=str(resp.url),
                    redirected=bool(resp.history),
                )
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            last_error = str(exc) or exc.__class__.__name__
            if i < len(delays) - 1:
                continue
            return FetchResult(ok=False, error=last_error)

    return FetchResult(ok=False, error=last_error)
