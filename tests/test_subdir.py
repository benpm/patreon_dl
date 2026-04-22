from datetime import datetime

from patreon_dl.crawled_url import PatreonCrawledUrl, PatreonCrawledUrlType
from patreon_dl.subdir import create_name_from_pattern


def _url() -> PatreonCrawledUrl:
    return PatreonCrawledUrl(
        post_id="123456",
        title="Test Post",
        published_at=datetime(2020, 7, 7, 20, 0, 15),
        url="http://google.com",
        filename="test.png",
        url_type=PatreonCrawledUrlType.POST_MEDIA,
    )


def test_create_name_from_pattern_filled():
    assert (
        create_name_from_pattern(_url(), "[%PostId%] %PublishedAt% %PostTitle%", 100)
        == "[123456] 2020-07-07 Test Post"
    )


def test_create_name_from_pattern_wrong_case():
    assert (
        create_name_from_pattern(_url(), "[%postId%] %PubliSHedAt% %Posttitle%", 100)
        == "[123456] 2020-07-07 Test Post"
    )


def test_create_name_from_pattern_null_title():
    u = _url()
    u.title = None
    assert (
        create_name_from_pattern(u, "[%PostId%] %PublishedAt% %PostTitle%", 100)
        == "[123456] 2020-07-07 No Title"
    )
