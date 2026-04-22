import logging
import re
from dataclasses import dataclass

from .http_client import PatreonHttpClient
from .models import CampaignRoot
from .path_sanitizer import sanitize

log = logging.getLogger(__name__)

_CAMPAIGN_ID_RE = re.compile(
    r'\\?"self\\?": ?\\?"https://www\.patreon\.com/api/campaigns/(\d+)\\?"'
)


@dataclass
class PatreonCrawlTargetInfo:
    id: int
    name: str
    avatar_url: str | None
    cover_url: str | None

    @property
    def save_directory(self) -> str:
        return sanitize(self.name) if self.name else "unknown"


async def retrieve(client: PatreonHttpClient, url: str) -> PatreonCrawlTargetInfo:
    if not url:
        raise ValueError("url cannot be empty")

    page_html = await client.download_string(url)
    m = _CAMPAIGN_ID_RE.search(page_html)
    if not m:
        raise RuntimeError(
            "Unable to retrieve campaign id (regex did not match). Patreon may have changed page layout."
        )
    campaign_id = int(m.group(1))

    campaign_url = (
        f"https://www.patreon.com/api/campaigns/{campaign_id}"
        "?include=access_rules.tier.null"
        "&fields[access_rule]=access_rule_type%2Camount_cents%2Cpost_count"
        "&fields[reward]=title%2Cid%2Camount_cents"
        "&json-api-version=1.0"
    )
    body = await client.download_string(campaign_url)
    root = CampaignRoot.model_validate_json(body)
    attrs = root.data.attributes
    return PatreonCrawlTargetInfo(
        id=campaign_id,
        name=attrs.name or f"campaign_{campaign_id}",
        avatar_url=attrs.avatar_photo_url,
        cover_url=attrs.cover_photo_url,
    )
