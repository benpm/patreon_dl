import os
from datetime import datetime

import pytest

from patreon_dl.crawled_url import PatreonCrawledUrl, PatreonCrawledUrlType
from patreon_dl.processor import PatreonCrawledUrlProcessor
from patreon_dl.settings import FileExistsAction, Settings


class _NullRetriever:
    async def retrieve_remote_file_name(self, url: str) -> str | None:
        return None

    async def before_start(self, settings: Settings) -> None:
        return None


def _settings() -> Settings:
    return Settings(
        download_directory="c:\\downloads\\UnitTesting",
        max_download_retries=10,
        retry_multiplier=1,
        file_exists_action=FileExistsAction.KEEP_EXISTING,
        save_avatar_and_cover=True,
        save_descriptions=True,
        save_embeds=True,
        save_json=True,
        is_use_sub_directories=True,
        sub_directory_pattern="[%PostId%] %PublishedAt% %PostTitle%",
        max_filename_length=50,
    )


@pytest.mark.asyncio
async def test_media_filename_is_url_truncated_no_extension():
    settings = _settings()
    crawled = PatreonCrawledUrl(
        post_id="123456",
        title="Test Post",
        published_at=datetime(2020, 7, 7, 20, 0, 15),
        url="https://www.patreon.com/media-u/Z0FBQUFBQmhXZDd3LXMwN0lJUFdVYTVIMEY1OGxzZTgwaFpQcW5TMk5WQVgxd2JVRFZvRXhjMjQ2V09oTW51eUpLQzIyOW1TdHRzYkY2Uk4yclAwX0VsSXBPMFZsNTBTcmZoaGx4OXJkR1Zham1CYl9fOWNVb3AzZGN1Wl9FMmNzcmIxc3hDek4xcHNuRV92LUVqQ0JESE4tcVBNYzlxYkRnWQ1=",
        filename="https://www.patreon.com/media-u/Z0FBQUFBQmhXZDd3a0xfckdEWmFrU0tjZHFUUkZfaDZ1OW92TjFVWFVDNk02c2FvS2FNczZxMS1rSVlaNUotX095dUNhdzJBSmYzMVpDV1luR1BYSXR6OVlZelpFOFFVektEcnpJT1plbElua2kwT1N2ZUMyU1NWaHV0eHQydWhnUXlmVWVLVDFYclBsSDBRaVJ3MDA5d2tzdDRZR3dtb3dBWQ1=",
        url_type=PatreonCrawledUrlType.POST_MEDIA,
    )

    proc = PatreonCrawledUrlProcessor(_NullRetriever())
    await proc.before_start(settings)
    await proc.process_crawled_url(crawled)

    expected = os.path.join(
        "c:\\downloads\\UnitTesting",
        "[123456] 2020-07-07 Test Post",
        "media_https___www.patreon.com_media-u_Z0FBQUFBQmhX",
    )
    assert crawled.download_path == expected


@pytest.mark.asyncio
async def test_media_filename_too_long_truncated_with_extension():
    settings = _settings()
    crawled = PatreonCrawledUrl(
        post_id="123456",
        title="Test Post",
        published_at=datetime(2020, 7, 7, 20, 0, 15),
        url="https://www.patreon.com/media-u/Z0FBQUFBQmhXZDd3LXMwN0lJUFdVYTVIMEY1OGxzZTgwaFpQcW5TMk5WQVgxd2JVRFZvRXhjMjQ2V09oTW51eUpLQzIyOW1TdHRzYkY2Uk4yclAwX0VsSXBPMFZsNTBTcmZoaGx4OXJkR1Zham1CYl9fOWNVb3AzZGN1Wl9FMmNzcmIxc3hDek4xcHNuRV92LUVqQ0JESE4tcVBNYzlxYkRnWQ1=",
        filename="E0OarAVlc0iipzgUC7JdvBCf9fgSmbwk3xRDjRGByTM24SuMl6HkY1DIdGfcvnZhbTb978AHonnwqWNzMPEWBRQp007ateP9ByhB.png",
        url_type=PatreonCrawledUrlType.POST_FILE,
    )

    proc = PatreonCrawledUrlProcessor(_NullRetriever())
    await proc.before_start(settings)
    await proc.process_crawled_url(crawled)

    expected = os.path.join(
        "c:\\downloads\\UnitTesting",
        "[123456] 2020-07-07 Test Post",
        "post_E0OarAVlc0iipzgUC7JdvBCf9fgSmbwk3xRDjRGByTM24.png",
    )
    assert crawled.download_path == expected


@pytest.mark.asyncio
async def test_duplicate_filenames_get_id_appended():
    settings = _settings()
    proc = PatreonCrawledUrlProcessor(_NullRetriever())
    await proc.before_start(settings)

    base_dir = os.path.join("c:\\downloads\\UnitTesting", "[123456] 2020-07-07 Test Post")

    c1 = PatreonCrawledUrl(
        post_id="123456",
        title="Test Post",
        published_at=datetime(2020, 7, 7, 20, 0, 15),
        url="https://c10.patreonusercontent.com/4/patreon-media/p/post/123456/710deacb70e940d999bf2f3022e1e2f0/WAJhIjoxZZJwIjoxfQ%3D%3D/1.png?token-time=1661644800&token-hash=123",
        filename="1.png",
        url_type=PatreonCrawledUrlType.POST_MEDIA,
    )
    await proc.process_crawled_url(c1)
    assert c1.download_path == os.path.join(base_dir, "media_1.png")

    c2 = PatreonCrawledUrl(
        post_id="123456",
        title="Test Post",
        published_at=datetime(2020, 7, 7, 20, 0, 15),
        url="https://c10.patreonusercontent.com/4/patreon-media/p/post/123456/110deacb70e940d999bf2f3022e1e2f0/WAJhIjoxZZJwIjoxfQ%3D%3D/1.png?token-time=1661644800&token-hash=123",
        filename="1.png",
        url_type=PatreonCrawledUrlType.POST_MEDIA,
    )
    await proc.process_crawled_url(c2)
    assert c2.download_path == os.path.join(base_dir, "media_1_110deacb70e940d999bf2f3022e1e2f0.png")

    c3 = PatreonCrawledUrl(
        post_id="123456",
        title="Test Post",
        published_at=datetime(2020, 7, 7, 20, 0, 15),
        url="https://c10.patreonusercontent.com/4/2/patreon-media/p/post/123456/210deacb70e940d999bf2f3022e1e2f0/WAJhIjoxZZJwIjoxfQ%3D%3D/1.png?token-time=1661644800&token-hash=123",
        filename="1.png",
        url_type=PatreonCrawledUrlType.POST_MEDIA,
    )
    await proc.process_crawled_url(c3)
    assert c3.download_path == os.path.join(base_dir, "media_1_210deacb70e940d999bf2f3022e1e2f0.png")
