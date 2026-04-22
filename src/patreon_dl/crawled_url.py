from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class PatreonCrawledUrlType(Enum):
    UNKNOWN = "Unknown"
    POST_FILE = "File"
    POST_ATTACHMENT = "Attachment"
    POST_MEDIA = "Media"
    EXTERNAL_URL = "External Url"
    COVER_FILE = "Cover"
    AVATAR_FILE = "Avatar"


@dataclass
class PatreonCrawledUrl:
    url: str = ""
    filename: str | None = None
    download_path: str = ""
    post_id: str = ""
    file_id: str | None = None
    title: str | None = None
    published_at: datetime = field(default_factory=lambda: datetime(1970, 1, 1))
    url_type: PatreonCrawledUrlType = PatreonCrawledUrlType.UNKNOWN
    is_processed_by_plugin: bool = False

    @property
    def url_type_friendly(self) -> str:
        return self.url_type.value

    def clone(self) -> "PatreonCrawledUrl":
        return PatreonCrawledUrl(
            url=self.url,
            filename=self.filename,
            post_id=self.post_id,
            file_id=self.file_id,
            title=self.title,
            published_at=self.published_at,
            url_type=self.url_type,
        )
