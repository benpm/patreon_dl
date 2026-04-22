import asyncio
import logging
import os
import re
from typing import Protocol

from .crawled_url import PatreonCrawledUrl, PatreonCrawledUrlType
from .path_sanitizer import sanitize
from .settings import Settings
from .subdir import create_name_from_pattern

log = logging.getLogger(__name__)

_FILE_ID_RE = re.compile(
    r"https://(.+)\.patreonusercontent\.com/(.+)/patreon-media/p/post/([0-9]+)/([a-z0-9]+)",
    re.IGNORECASE,
)


class RemoteFilenameRetriever(Protocol):
    async def retrieve_remote_file_name(self, url: str) -> str | None: ...
    async def before_start(self, settings: Settings) -> None: ...


_TYPE_PREFIX = {
    PatreonCrawledUrlType.POST_FILE: "post",
    PatreonCrawledUrlType.POST_ATTACHMENT: "attachment",
    PatreonCrawledUrlType.POST_MEDIA: "media",
    PatreonCrawledUrlType.AVATAR_FILE: "avatar",
    PatreonCrawledUrlType.COVER_FILE: "cover",
    PatreonCrawledUrlType.EXTERNAL_URL: "external",
}


class PatreonCrawledUrlProcessor:
    def __init__(self, remote_filename_retriever: RemoteFilenameRetriever) -> None:
        self._retriever = remote_filename_retriever
        self._lock = asyncio.Lock()
        self._file_count: dict[str, int] = {}
        self._settings: Settings | None = None

    async def before_start(self, settings: Settings) -> None:
        self._settings = settings
        self._file_count = {}
        await self._retriever.before_start(settings)

    async def process_crawled_url(self, crawled_url: PatreonCrawledUrl) -> bool:
        assert self._settings is not None
        s = self._settings

        u = crawled_url.url
        if "youtube.com/watch?v=" in u or "youtu.be/" in u:
            log.error("[%s] [NOT SUPPORTED] YOUTUBE link found: %s", crawled_url.post_id, u)
            return False
        if "imgur.com/" in u:
            log.error("[%s] [NOT SUPPORTED] IMGUR link found: %s", crawled_url.post_id, u)
            return False

        filename = crawled_url.filename or ""

        if not crawled_url.is_processed_by_plugin:
            filename = "" if s.is_use_sub_directories else f"{crawled_url.post_id}_"

            try:
                prefix = _TYPE_PREFIX[crawled_url.url_type]
            except KeyError as e:
                raise ValueError(f"Invalid url type: {crawled_url.url_type}") from e

            filename += prefix

            if (
                crawled_url.url_type in (PatreonCrawledUrlType.POST_ATTACHMENT, PatreonCrawledUrlType.POST_MEDIA)
                and not s.is_use_legacy_filenaming
                and crawled_url.file_id
            ):
                filename += f"_{crawled_url.file_id}"

            if crawled_url.filename is None:
                remote_name = await self._retriever.retrieve_remote_file_name(crawled_url.url)
                if remote_name is None:
                    raise RuntimeError(
                        f"[{crawled_url.post_id}] Unable to retrieve name for external entry of type "
                        f"{crawled_url.url_type}: {crawled_url.url}"
                    )
                filename += f"_{remote_name}"
            else:
                filename += f"_{crawled_url.filename}"

            filename = sanitize(filename)

            if len(filename) > s.max_filename_length:
                _, ext = os.path.splitext(filename)
                if len(ext) > 4:
                    log.warning(
                        "File extension for file %s is longer than 4 chars and won't be appended", filename
                    )
                    ext = ""
                filename = filename[: s.max_filename_length] + ext

            key = f"{crawled_url.post_id}_{filename.lower()}"

            async with self._lock:
                seen_before = key in self._file_count
                self._file_count[key] = self._file_count.get(key, 0) + 1

            if seen_before:
                if crawled_url.url_type != PatreonCrawledUrlType.EXTERNAL_URL:
                    matches = _FILE_ID_RE.findall(crawled_url.url)
                    if not matches:
                        raise RuntimeError(
                            f"[{crawled_url.post_id}] Unable to retrieve file id for {crawled_url.url}"
                        )
                    if len(matches) > 1:
                        raise RuntimeError(
                            f"[{crawled_url.post_id}] More than 1 media found in URL {crawled_url.url}"
                        )
                    append_str = matches[0][3]
                else:
                    append_str = str(self._file_count[key])

                base, ext = os.path.splitext(filename)
                filename = f"{base}_{append_str}{ext}"

        subdir = ""
        if (
            s.is_use_sub_directories
            and crawled_url.url_type not in (PatreonCrawledUrlType.AVATAR_FILE, PatreonCrawledUrlType.COVER_FILE)
        ):
            subdir = create_name_from_pattern(
                crawled_url, s.sub_directory_pattern, s.max_subdirectory_name_length
            )

        if not crawled_url.is_processed_by_plugin:
            crawled_url.download_path = os.path.join(s.download_directory, subdir, filename)
        else:
            crawled_url.download_path = os.path.join(s.download_directory, subdir)

        return True
