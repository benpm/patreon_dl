from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from .crawled_url import PatreonCrawledUrl


class DownloaderStatus(Enum):
    READY = "Ready"
    INITIALIZATION = "Initialization"
    RETRIEVING_CAMPAIGN_INFORMATION = "RetrievingCampaignInformation"
    CRAWLING = "Crawling"
    DOWNLOADING = "Downloading"
    EXPORTING_CRAWL_RESULTS = "ExportingCrawlResults"
    DONE = "Done"


class MessageType(Enum):
    INFO = "Info"
    WARNING = "Warning"
    ERROR = "Error"


@dataclass
class Events:
    on_status: Callable[[DownloaderStatus], None] = lambda _s: None
    on_post_crawl_start: Callable[[str], None] = lambda _id: None
    on_new_url: Callable[[PatreonCrawledUrl], None] = lambda _u: None
    on_message: Callable[[MessageType, str, str | None], None] = lambda _t, _m, _id: None
    on_file_downloaded: Callable[[str, bool, int, str | None], None] = lambda _u, _ok, _total, _err: None
