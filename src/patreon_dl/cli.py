import asyncio
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse

import click
from rich.logging import RichHandler

from .downloader import Downloader
from .events import DownloaderStatus, Events, MessageType
from .settings import FileExistsAction, Settings


def _setup_logging(level: str) -> None:
    log_level = {"Default": logging.INFO, "Debug": logging.DEBUG, "Trace": logging.DEBUG}.get(level, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


def _make_events() -> Events:
    log = logging.getLogger("patreon_dl")

    def on_status(s: DownloaderStatus) -> None:
        msg = {
            DownloaderStatus.INITIALIZATION: "Preparing to download...",
            DownloaderStatus.RETRIEVING_CAMPAIGN_INFORMATION: "Retrieving campaign information...",
            DownloaderStatus.CRAWLING: "Crawling...",
            DownloaderStatus.DOWNLOADING: "Downloading...",
            DownloaderStatus.EXPORTING_CRAWL_RESULTS: "Exporting crawl results...",
            DownloaderStatus.DONE: "Finished",
        }.get(s)
        if msg:
            log.info(msg)

    def on_message(t: MessageType, m: str, _id: str | None) -> None:
        if t is MessageType.INFO:
            log.info(m)
        elif t is MessageType.WARNING:
            log.warning(m)
        else:
            log.error(m)

    return Events(on_status=on_status, on_message=on_message)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--url", required=True, help="Url of the creator's page")
@click.option("--descriptions", "save_descriptions", is_flag=True, default=False, help="Save post descriptions")
@click.option("--embeds", "save_embeds", is_flag=True, default=False, help="Save embedded content metadata")
@click.option("--json", "save_json", is_flag=True, default=False, help="Save json data")
@click.option("--campaign-images", "save_avatar_and_cover", is_flag=True, default=False,
              help="Download campaign's avatar and cover images")
@click.option("--download-directory", default="",
              help="Directory to save all downloaded files in. Default: ./downloads/<CreatorName>")
@click.option("--log-level", type=click.Choice(["Default", "Debug", "Trace"]), default="Default",
              help="Logging level")
@click.option("--log-save", is_flag=True, default=False, help="(no-op in this rewrite)")
@click.option("--file-exists-action",
              type=click.Choice([a.value for a in FileExistsAction]),
              default=FileExistsAction.BACKUP_IF_DIFFERENT.value,
              help="What to do with files already on disk")
@click.option("--use-legacy-file-naming", "is_use_legacy_filenaming", is_flag=True, default=False,
              help="Use legacy filename pattern (no FileId in filename)")
@click.option("--disable-remote-file-size-check", "is_disable_remote_file_size_check", is_flag=True, default=False,
              help="Don't HEAD-check remote file size before downloading")
@click.option("--remote-browser-address", default=None,
              help="Address of an externally launched Chrome with --remote-debugging-port (e.g. ws://127.0.0.1:9222)")
@click.option("--use-sub-directories", is_flag=True, default=False,
              help="Create a subdirectory per post")
@click.option("--sub-directory-pattern", default="[%PostId%] %PublishedAt% %PostTitle%",
              help="Pattern for sub-directory names. %PostId%, %PublishedAt%, %PostTitle%")
@click.option("--max-sub-directory-name-length", "max_subdirectory_name_length", default=100, type=int,
              help="Max length of sub-directory names")
@click.option("--max-filename-length", default=100, type=int,
              help="Max length of filenames (excluding extension)")
@click.option("--filenames-fallback-to-content-type", "fallback_to_content_type_filenames", is_flag=True, default=False,
              help="Fall back to Content-Type + url-hash for filenames if all else fails")
@click.option("--proxy-server-address", default=None,
              help="Proxy server URL, e.g. http://host:port or socks5://host:port")
@click.option("--state-path", default=".patreon-dl-state.json",
              help="Path to save/load Playwright auth state JSON")
def main(**kw: object) -> None:
    """Download content from a patreon.com creator page."""
    _setup_logging(str(kw.pop("log_level")))
    kw.pop("log_save", None)  # no-op
    url = str(kw.pop("url"))
    state_path = Path(str(kw.pop("state_path")))

    fea_str = str(kw.pop("file_exists_action"))
    fea = next(a for a in FileExistsAction if a.value == fea_str)

    is_check_remote_file_size = not bool(kw.pop("is_disable_remote_file_size_check"))

    if not urlparse(url).scheme:
        click.echo(f"Invalid url: {url}", err=True)
        sys.exit(1)

    settings = Settings(
        file_exists_action=fea,
        is_check_remote_file_size=is_check_remote_file_size,
        **{k: v for k, v in kw.items() if v is not None},  # type: ignore[arg-type]
    )

    if settings.is_use_legacy_filenaming and fea in (
        FileExistsAction.BACKUP_IF_DIFFERENT,
        FileExistsAction.REPLACE_IF_DIFFERENT,
    ):
        click.echo("Legacy filenaming cannot be used with BackupIfDifferent / ReplaceIfDifferent", err=True)
        sys.exit(1)

    asyncio.run(Downloader(settings, _make_events()).run(url, state_path))


if __name__ == "__main__":
    main()
