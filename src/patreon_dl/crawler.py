"""Crawl Patreon /api/posts pages, emitting PatreonCrawledUrl entries."""

import asyncio
import logging
import os
import random
from pathlib import Path
from typing import Callable

from .crawled_url import PatreonCrawledUrl, PatreonCrawledUrlType
from .events import Events, MessageType
from .http_client import PatreonHttpClient
from .models import PostsRoot, RootData
from .settings import Settings
from .subdir import create_name_from_pattern
from .target_info import PatreonCrawlTargetInfo

log = logging.getLogger(__name__)

# Verbatim from PatreonPageCrawler.cs:33-41
_CRAWL_START_URL = (
    "https://www.patreon.com/api/posts?"
    "include=user%2Cattachments_media%2Ccampaign%2Cpoll.choices%2Cpoll.current_user_responses.user"
    "%2Cpoll.current_user_responses.choice%2Cpoll.current_user_responses.poll"
    "%2Caccess_rules.tier.null%2Cimages.null%2Caudio.null"
    "&fields[post]=change_visibility_at%2Ccomment_count%2Ccontent%2Ccurrent_user_can_delete"
    "%2Ccurrent_user_can_view%2Ccurrent_user_has_liked%2Cembed%2Cimage%2Cis_paid%2Clike_count"
    "%2Cmin_cents_pledged_to_view%2Cpost_file%2Cpost_metadata%2Cpublished_at%2Cpatron_count"
    "%2Cpatreon_url%2Cpost_type%2Cpledge_url%2Cthumbnail_url%2Cteaser_text%2Ctitle"
    "%2Cupgrade_url%2Curl%2Cwas_posted_by_campaign_owner%2Ccontent_json_string"
    "&fields[user]=image_url%2Cfull_name%2Curl"
    "&fields[campaign]=show_audio_post_download_links%2Cavatar_photo_url%2Cearnings_visibility"
    "%2Cis_nsfw%2Cis_monthly%2Cname%2Curl"
    "&fields[access_rule]=access_rule_type%2Camount_cents"
    "&fields[media]=id%2Cimage_urls%2Cdownload_url%2Cmetadata%2Cfile_name"
    "&sort=-published_at"
    "&filter[is_draft]=false&filter[contains_exclusive_posts]=true"
    "&json-api-use-default-includes=false&json-api-version=1.0"
)


class PatreonPageCrawler:
    def __init__(self, client: PatreonHttpClient, settings: Settings, events: Events) -> None:
        self._client = client
        self._settings = settings
        self._events = events

    async def crawl(self, target: PatreonCrawlTargetInfo) -> list[PatreonCrawledUrl]:
        if target.id < 1:
            raise ValueError("Campaign ID cannot be less than 1")
        if not target.name:
            raise ValueError("Campaign name cannot be null or empty")

        log.debug("Crawling campaign %s", target.name)
        results: list[PatreonCrawledUrl] = []

        if self._settings.save_avatar_and_cover:
            if target.avatar_url:
                results.append(PatreonCrawledUrl(
                    post_id="0", url=target.avatar_url, url_type=PatreonCrawledUrlType.AVATAR_FILE,
                ))
            if target.cover_url:
                results.append(PatreonCrawledUrl(
                    post_id="0", url=target.cover_url, url_type=PatreonCrawledUrlType.COVER_FILE,
                ))

        next_page = _CRAWL_START_URL + f"&filter[campaign_id]={target.id}"
        page = 0
        while next_page:
            page += 1
            log.debug("Page #%d: %s", page, next_page)
            body = await self._client.download_string(next_page)

            if self._settings.save_json:
                Path(self._settings.download_directory).mkdir(parents=True, exist_ok=True)
                Path(self._settings.download_directory, f"page_{page}.json").write_text(body, encoding="utf-8")

            crawled, next_page = await self._parse_page(body)
            results.extend(crawled)

            await asyncio.sleep(0.5 * random.randint(1, 2))

        log.debug("Finished crawl, %d urls", len(results))
        return results

    async def _parse_page(self, body: str) -> tuple[list[PatreonCrawledUrl], str | None]:
        root = PostsRoot.model_validate_json(body)
        crawled: list[PatreonCrawledUrl] = []
        skipped_includes: set[str] = set()

        for entry in root.data:
            self._events.on_post_crawl_start(entry.id)
            log.info("-> %s", entry.id)
            if entry.type != "post":
                msg = f"Invalid type for data: {entry.type}, skipping"
                log.error("[%s] %s", entry.id, msg)
                self._events.on_message(MessageType.ERROR, msg, entry.id)
                continue

            if not entry.attributes.current_user_can_view:
                log.warning("[%s] current user cannot view this post", entry.id)
                if entry.relationships.attachments_media:
                    skipped_includes.update(d.id for d in entry.relationships.attachments_media.data)
                if entry.relationships.images:
                    skipped_includes.update(d.id for d in entry.relationships.images.data)
                self._events.on_message(MessageType.WARNING, "Current user cannot view this post", entry.id)
                continue

            base = PatreonCrawledUrl(
                post_id=entry.id,
                title=entry.attributes.title,
                published_at=entry.attributes.published_at,
            )

            additional_dir = self._settings.download_directory
            if self._settings.is_use_sub_directories and (
                self._settings.save_descriptions or (entry.attributes.embed and self._settings.save_embeds)
            ):
                additional_dir = os.path.join(
                    self._settings.download_directory,
                    create_name_from_pattern(
                        base, self._settings.sub_directory_pattern, self._settings.max_subdirectory_name_length
                    ),
                )
                os.makedirs(additional_dir, exist_ok=True)

            if self._settings.save_descriptions and entry.attributes.content_json_string is not None:
                fname = "description.json" if self._settings.is_use_sub_directories else f"{entry.id}_description.json"
                try:
                    Path(additional_dir, fname).write_text(entry.attributes.content_json_string, encoding="utf-8")
                except OSError as e:
                    log.error("[%s] Unable to save description: %s", entry.id, e)
                    self._events.on_message(MessageType.ERROR, f"Unable to save description: {e}", entry.id)

            if entry.attributes.embed:
                if self._settings.save_embeds:
                    fname = "embed.txt" if self._settings.is_use_sub_directories else f"{entry.id}_embed.txt"
                    try:
                        Path(additional_dir, fname).write_text(entry.attributes.embed.to_text(), encoding="utf-8")
                    except OSError as e:
                        log.error("[%s] Unable to save embed: %s", entry.id, e)
                        self._events.on_message(MessageType.ERROR, f"Unable to save embed: {e}", entry.id)

                if entry.attributes.embed.url:
                    sub = base.clone()
                    sub.url = entry.attributes.embed.url
                    sub.url_type = PatreonCrawledUrlType.EXTERNAL_URL
                    crawled.append(sub)
                    log.info("[%s] new embed entry: %s", entry.id, sub.url)
                    self._events.on_new_url(sub.clone())

            # Attachments
            if entry.relationships.attachments_media:
                for ref in entry.relationships.attachments_media.data:
                    if ref.type != "media":
                        msg = f"invalid attachment type for {ref.id}"
                        log.error("[%s] %s", entry.id, msg)
                        self._events.on_message(MessageType.ERROR, msg, entry.id)
                        continue
                    inc = next((i for i in root.included if i.type == "media" and i.id == ref.id), None)
                    if inc is None:
                        msg = f"attachment data not found for {ref.id}"
                        log.error("[%s] %s", entry.id, msg)
                        self._events.on_message(MessageType.ERROR, msg, entry.id)
                        continue
                    if not inc.attributes.download_url:
                        continue
                    sub = base.clone()
                    sub.url = inc.attributes.download_url
                    sub.filename = inc.attributes.file_name
                    sub.url_type = PatreonCrawledUrlType.POST_ATTACHMENT
                    sub.file_id = inc.id
                    crawled.append(sub)
                    log.info("[%s A-%s] new attachment: %s", entry.id, ref.id, sub.url)
                    self._events.on_new_url(sub.clone())

            # Media
            if entry.relationships.images:
                for ref in entry.relationships.images.data:
                    if ref.type != "media":
                        continue
                    inc = next((i for i in root.included if i.type == "media" and i.id == ref.id), None)
                    if inc is None or not inc.attributes.download_url:
                        continue
                    sub = base.clone()
                    sub.url = inc.attributes.download_url
                    sub.filename = inc.attributes.file_name
                    sub.url_type = PatreonCrawledUrlType.POST_MEDIA
                    sub.file_id = inc.id
                    crawled.append(sub)
                    log.info("[%s M-%s] new media: %s", entry.id, ref.id, sub.url)
                    self._events.on_new_url(sub.clone())

            # Post-level file
            if entry.attributes.post_file and entry.attributes.post_file.url:
                base.url = entry.attributes.post_file.url
                base.filename = entry.attributes.post_file.name
            elif entry.attributes.image:
                if entry.attributes.image.large_url:
                    base.url = entry.attributes.image.large_url
                elif entry.attributes.image.url:
                    base.url = entry.attributes.image.url

            if base.url:
                base.url_type = PatreonCrawledUrlType.POST_FILE
                crawled.append(base)
                log.info("[%s] new post entry: %s", entry.id, base.url)
                self._events.on_new_url(base.clone())

        return crawled, root.links.next if root.links else None
