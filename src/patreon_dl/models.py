"""Pydantic models for the patreon.com /api/posts and /api/campaigns JSON shapes."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _M(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


# /api/posts ---------------------------------------------------------------


class Embed(_M):
    description: str | None = None
    html: Any = None
    provider: str | None = None
    provider_url: str | None = None
    subject: str | None = None
    url: str | None = None

    def to_text(self) -> str:
        return (
            f"Provider: {self.provider}, Provider URL: {self.provider_url}\n\n"
            f"Subject: {self.subject}\n\n"
            f"Url: {self.url}\n\n"
            f"Description: {self.description}\n\n"
            f"Html: {self.html}\n\n"
        )


class PostImage(_M):
    height: int | None = None
    large_url: str | None = None
    thumb_url: str | None = None
    url: str | None = None
    width: int | None = None


class PostFile(_M):
    name: str | None = None
    url: str | None = None


class RootDataAttributes(_M):
    content_json_string: str | None = None
    current_user_can_view: bool = False
    embed: Embed | None = None
    image: PostImage | None = None
    is_paid: bool = False
    post_file: PostFile | None = None
    published_at: datetime
    title: str | None = None
    url: str | None = None


class _Ref(_M):
    id: str
    type: str


class _RefList(_M):
    data: list[_Ref] = Field(default_factory=list)


class RootDataRelationships(_M):
    attachments_media: _RefList | None = None
    images: _RefList | None = None


class RootData(_M):
    id: str
    type: str
    attributes: RootDataAttributes
    relationships: RootDataRelationships = Field(default_factory=RootDataRelationships)


class IncludedAttributes(_M):
    download_url: str | None = None
    file_name: str | None = None
    url: str | None = None


class Included(_M):
    id: str
    type: str
    attributes: IncludedAttributes = Field(default_factory=IncludedAttributes)


class RootLinks(_M):
    next: str | None = None


class PostsRoot(_M):
    data: list[RootData] = Field(default_factory=list)
    included: list[Included] = Field(default_factory=list)
    links: RootLinks | None = None


# /api/campaigns ---------------------------------------------------------------


class CampaignAttributes(_M):
    avatar_photo_url: str | None = Field(default=None, alias="avatar_photo_url")
    cover_photo_url: str | None = Field(default=None, alias="cover_photo_url")
    name: str | None = None


class CampaignData(_M):
    attributes: CampaignAttributes


class CampaignRoot(_M):
    data: CampaignData
