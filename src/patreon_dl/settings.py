from dataclasses import dataclass, field
from enum import Enum


class FileExistsAction(Enum):
    KEEP_EXISTING = "KeepExisting"
    ALWAYS_REPLACE = "AlwaysReplace"
    BACKUP_IF_DIFFERENT = "BackupIfDifferent"
    REPLACE_IF_DIFFERENT = "ReplaceIfDifferent"


_DEFAULT_BLACKLIST = (
    "patreon.com/posts/|tmblr.co/|t.umblr.com/redirect|mailto:|postybirb.com|picarto.tv|"
    "deviantart.com|https://twitter.com|https://steamcommunity.com|"
    "http://www.furaffinity.net|https://e621.net/post/show|https://e621.net/posts/|"
    "trello.com|https://smutba.se|https://sfmlab.com|http://fav.me|https://inkbunny.net|"
    "https://www.pixiv.net/|pixiv.me|https://x.com|https://www.x.com|http://x.com|"
    "http://www.x.com"
).split("|")


@dataclass
class Settings:
    # Per-run
    download_directory: str = ""
    proxy_server_address: str | None = None

    # Save toggles (mirror PatreonDownloaderSettings defaults)
    save_descriptions: bool = True
    save_embeds: bool = True
    save_json: bool = True
    save_avatar_and_cover: bool = True

    # Filename / subdir
    is_use_sub_directories: bool = False
    sub_directory_pattern: str = "[%PostId%] %PublishedAt% %PostTitle%"
    max_subdirectory_name_length: int = 100
    max_filename_length: int = 100
    fallback_to_content_type_filenames: bool = False
    is_use_legacy_filenaming: bool = False

    # Download behavior
    file_exists_action: FileExistsAction = FileExistsAction.BACKUP_IF_DIFFERENT
    is_check_remote_file_size: bool = True
    max_download_retries: int = 10
    retry_multiplier: int = 5

    # Browser
    is_headless_browser: bool = True
    remote_browser_address: str | None = None

    # HTTP
    user_agent: str = "Patreon/126.9.0.15 (Android; Android 14; Scale/2.10)"
    url_blacklist: list[str] = field(default_factory=lambda: list(_DEFAULT_BLACKLIST))

    # Patreon endpoints (constants)
    login_page_address: str = "https://www.patreon.com/login"
    login_check_address: str = (
        "https://www.patreon.com/api/badges?json-api-version=1.0"
        "&json-api-use-default-includes=false&include=[]"
    )
