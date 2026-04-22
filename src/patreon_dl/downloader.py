"""Top-level orchestrator (replaces UniversalDownloader + Program.RunPatreonDownloader)."""

import logging
import os
from pathlib import Path

from .browser import ensure_storage_state
from .cookie_validator import validate
from .crawled_url import PatreonCrawledUrl
from .crawler import PatreonPageCrawler
from .events import DownloaderStatus, Events, MessageType
from .filename_retriever import PatreonRemoteFilenameRetriever
from .http_client import PatreonHttpClient
from .processor import PatreonCrawledUrlProcessor
from .settings import Settings
from .target_info import retrieve as retrieve_target_info

log = logging.getLogger(__name__)


class Downloader:
    def __init__(self, settings: Settings, events: Events | None = None) -> None:
        self._settings = settings
        self._events = events or Events()
        self._files_done = 0

    async def run(self, url: str, state_path: Path) -> None:
        e = self._events
        e.on_status(DownloaderStatus.INITIALIZATION)

        state = await ensure_storage_state(state_path, self._settings)
        retriever = PatreonRemoteFilenameRetriever()

        async with PatreonHttpClient(self._settings, state) as client:
            await validate(client)

            e.on_status(DownloaderStatus.RETRIEVING_CAMPAIGN_INFORMATION)
            target = await retrieve_target_info(client, url)
            log.info("Campaign: %s (id=%d)", target.name, target.id)

            if not self._settings.download_directory:
                self._settings.download_directory = os.path.join("downloads", target.save_directory)
            Path(self._settings.download_directory).mkdir(parents=True, exist_ok=True)

            processor = PatreonCrawledUrlProcessor(retriever)
            await processor.before_start(self._settings)

            e.on_status(DownloaderStatus.CRAWLING)
            crawler = PatreonPageCrawler(client, self._settings, e)
            crawled = await crawler.crawl(target)

            e.on_status(DownloaderStatus.DOWNLOADING)
            blacklisted = {b.lower() for b in self._settings.url_blacklist if b}
            kept: list[PatreonCrawledUrl] = []
            for cu in crawled:
                low = cu.url.lower()
                if any(b in low for b in blacklisted):
                    log.debug("Blacklisted, skipping: %s", cu.url)
                    continue
                try:
                    if not await processor.process_crawled_url(cu):
                        continue
                except Exception as ex:  # noqa: BLE001
                    log.error("Skipping %s — processor error: %s", cu.url, ex)
                    continue
                kept.append(cu)

            total = len(kept)
            for cu in kept:
                try:
                    await client.download_file(cu.url, cu.download_path)
                    self._files_done += 1
                    e.on_file_downloaded(cu.url, True, total, None)
                    log.info("Downloaded %d/%d: %s", self._files_done, total, cu.url)
                except Exception as ex:  # noqa: BLE001
                    self._files_done += 1
                    e.on_file_downloaded(cu.url, False, total, str(ex))
                    log.error("Failed to download %s: %s", cu.url, ex)
                    e.on_message(MessageType.ERROR, f"Download failed: {ex}", cu.post_id)

        await retriever.aclose()
        e.on_status(DownloaderStatus.DONE)
