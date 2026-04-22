import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

import httpx

from .settings import FileExistsAction, Settings

log = logging.getLogger(__name__)


def _load_cookies_from_storage_state(state: dict[str, Any]) -> httpx.Cookies:
    jar = httpx.Cookies()
    for c in state.get("cookies", []):
        jar.set(name=c["name"], value=c["value"], domain=c.get("domain", ""), path=c.get("path", "/"))
    return jar


class PatreonHttpClient:
    def __init__(self, settings: Settings, storage_state: dict[str, Any]) -> None:
        self._settings = settings
        cookies = _load_cookies_from_storage_state(storage_state)
        proxy = settings.proxy_server_address
        self._client = httpx.AsyncClient(
            cookies=cookies,
            headers={
                "User-Agent": settings.user_agent,
                "Referer": "https://www.patreon.com",
            },
            timeout=httpx.Timeout(60.0, connect=20.0),
            follow_redirects=True,
            proxy=proxy,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "PatreonHttpClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def _request_with_retry(self, method: str, url: str, **kw: Any) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self._settings.max_download_retries):
            try:
                resp = await self._client.request(method, url, **kw)
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise httpx.HTTPStatusError(f"transient {resp.status_code}", request=resp.request, response=resp)
                resp.raise_for_status()
                return resp
            except (httpx.HTTPError,) as e:
                last_exc = e
                wait = self._settings.retry_multiplier * (attempt + 1)
                log.warning("Request failed (%s), retry %d in %ds: %s", method, attempt + 1, wait, e)
                await asyncio.sleep(wait)
        raise RuntimeError(f"Request failed after {self._settings.max_download_retries} retries: {url}") from last_exc

    async def download_string(self, url: str) -> str:
        resp = await self._request_with_retry("GET", url)
        return resp.text

    async def head_size(self, url: str) -> int | None:
        try:
            resp = await self._client.head(url)
            cl = resp.headers.get("Content-Length")
            return int(cl) if cl else None
        except httpx.HTTPError:
            return None

    async def download_file(self, url: str, path: str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        action = self._settings.file_exists_action

        if target.exists() and action is FileExistsAction.KEEP_EXISTING:
            log.debug("Skipping existing %s (KeepExisting)", target)
            return

        if not target.exists() or action is FileExistsAction.ALWAYS_REPLACE:
            await self._stream_to(url, target)
            return

        # BACKUP_IF_DIFFERENT or REPLACE_IF_DIFFERENT — write to .new, compare, decide
        if self._settings.is_check_remote_file_size:
            remote_size = await self.head_size(url)
            if remote_size is not None and remote_size == target.stat().st_size:
                # size match — still need byte compare to be sure (matches BackupIfDifferent semantics)
                pass

        tmp = target.with_suffix(target.suffix + ".new")
        await self._stream_to(url, tmp)

        if _files_equal(tmp, target):
            tmp.unlink()
            return

        if action is FileExistsAction.BACKUP_IF_DIFFERENT:
            bak = target.with_suffix(target.suffix + ".bak")
            i = 0
            while bak.exists():
                i += 1
                bak = target.with_suffix(target.suffix + f".bak{i}")
            shutil.move(str(target), str(bak))
        else:  # REPLACE_IF_DIFFERENT
            target.unlink()

        shutil.move(str(tmp), str(target))

    async def _stream_to(self, url: str, target: Path) -> None:
        last_exc: Exception | None = None
        for attempt in range(self._settings.max_download_retries):
            try:
                async with self._client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    with target.open("wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                            f.write(chunk)
                return
            except httpx.HTTPError as e:
                last_exc = e
                if target.exists():
                    target.unlink()
                wait = self._settings.retry_multiplier * (attempt + 1)
                log.warning("Stream failed, retry %d in %ds: %s", attempt + 1, wait, e)
                await asyncio.sleep(wait)
        raise RuntimeError(f"Failed to download {url}") from last_exc


def _files_equal(a: Path, b: Path) -> bool:
    if a.stat().st_size != b.stat().st_size:
        return False
    with a.open("rb") as fa, b.open("rb") as fb:
        while True:
            ca = fa.read(64 * 1024)
            cb = fb.read(64 * 1024)
            if ca != cb:
                return False
            if not ca:
                return True
