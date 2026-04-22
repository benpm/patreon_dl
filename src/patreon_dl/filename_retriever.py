import hashlib
import logging
import mimetypes
import re

import httpx

from .settings import Settings

log = logging.getLogger(__name__)

_URL_RE = re.compile(r"[^/&?]+\.\w{3,4}(?=([?&].*$|$))")


class PatreonRemoteFilenameRetriever:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(follow_redirects=True, timeout=30.0)
        self._use_media_type = False

    async def before_start(self, settings: Settings) -> None:
        self._use_media_type = settings.fallback_to_content_type_filenames

    async def aclose(self) -> None:
        await self._client.aclose()

    async def retrieve_remote_file_name(self, url: str) -> str | None:
        if not url:
            return None

        media_type: str | None = None
        filename: str | None = None
        try:
            resp = await self._client.head(url)
            cd = resp.headers.get("Content-Disposition", "")
            m = re.search(r'filename="?([^";]+)"?', cd)
            if m:
                filename = m.group(1).strip('"')
                log.debug("Content-Disposition returned: %s", filename)
            elif self._use_media_type:
                media_type = resp.headers.get("Content-Type", "").split(";", 1)[0].strip() or None
        except httpx.HTTPError as e:
            log.error("HTTP error retrieving remote filename: %s", e)

        if not filename:
            m = _URL_RE.search(url)
            if m:
                filename = m.group(0)
                # patreon truncates extensions — fix .jpe → .jpeg
                if "patreonusercontent.com/" in url and filename.endswith(".jpe"):
                    filename += "g"
                log.debug("Falling back to url extraction: %s", filename)

        if media_type and not filename:
            ext = mimetypes.guess_extension(media_type) or ""
            digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
            filename = f"gen_{digest}{ext}"
            log.debug("Falling back to content-type+hash name: %s", filename)

        return filename
