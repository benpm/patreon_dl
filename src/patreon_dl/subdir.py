from .crawled_url import PatreonCrawledUrl
from .path_sanitizer import sanitize


def create_name_from_pattern(crawled_url: PatreonCrawledUrl, pattern: str, length_limit: int) -> str:
    title = (crawled_url.title or "No Title").strip()
    while len(title) > 1 and title[-1] == ".":
        title = title[:-1].strip()

    s = (
        pattern.lower()
        .replace("%publishedat%", crawled_url.published_at.strftime("%Y-%m-%d"))
        .replace("%posttitle%", title)
        .replace("%postid%", crawled_url.post_id)
    )

    if len(s) > length_limit:
        s = s[: length_limit - 1].rstrip() + "~"

    return sanitize(s)
