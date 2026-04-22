# patreon-dl

Download content posted by creators on patreon.com.

You need a valid Patreon account. Free posts are available to any logged-in account. Paid posts only download if you have an active subscription to that creator.

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — all Python management is handled by uv; do not use system Python directly.

## Installation

```bash
git clone <repo>
cd patreon-dl
uv sync
uv run playwright install chromium
```

That's it. No virtual environment to activate, no `pip install`.

## Authentication

patreon-dl uses a real browser (Chromium) to log you in and capture session cookies. This handles Cloudflare bot protection automatically.

**First run:** A Chromium window opens. Log into your Patreon account normally. Once logged in, the window closes and downloading begins. Your session is saved to `.patreon-dl-state.json`.

**Subsequent runs:** The saved session is reused headlessly — no browser window appears.

**Re-authentication:** Delete `.patreon-dl-state.json` and run again to force a new login.

**Headless servers:** Use `--remote-browser-address` to connect to an externally-launched Chrome (see [Advanced](#advanced)).

## Usage

```bash
uv run patreon-dl --url <creator_page_url>
```

### Supported URL formats

```
https://www.patreon.com/m/<numbers>/posts
https://www.patreon.com/user?u=<numbers>
https://www.patreon.com/user/posts?u=<numbers>
https://www.patreon.com/<creator_name>/posts
```

### Examples

**Download everything from a creator:**
```bash
uv run patreon-dl --url https://www.patreon.com/somecreator/posts
```

**Specify a download directory:**
```bash
uv run patreon-dl --url https://www.patreon.com/somecreator/posts \
  --download-directory ./my-downloads
```

Default directory when not specified: `./downloads/<CreatorName>`

**Save all sidecar data:**
```bash
uv run patreon-dl --url https://www.patreon.com/somecreator/posts \
  --descriptions \
  --embeds \
  --json \
  --campaign-images
```

**Organize by post with subdirectories:**
```bash
uv run patreon-dl --url https://www.patreon.com/somecreator/posts \
  --use-sub-directories
```

Creates a folder per post: `[PostId] YYYY-MM-DD Post Title/`

**Full example — everything enabled:**
```bash
uv run patreon-dl \
  --url https://www.patreon.com/somecreator/posts \
  --download-directory ./downloads \
  --descriptions \
  --embeds \
  --campaign-images \
  --json \
  --use-sub-directories \
  --file-exists-action KeepExisting
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--url` | *(required)* | Creator page URL |
| `--download-directory` | `./downloads/<name>` | Where to save files |
| `--descriptions` | off | Save each post's content as `description.json` |
| `--embeds` | off | Save embedded content metadata (provider, URL, etc.) as `embed.txt` |
| `--json` | off | Save the raw API JSON response for each crawled page as `page_N.json` |
| `--campaign-images` | off | Download the creator's avatar and cover image |
| `--use-sub-directories` | off | Create one subdirectory per post inside the download directory |
| `--sub-directory-pattern` | `[%PostId%] %PublishedAt% %PostTitle%` | Pattern for subdirectory names. Tokens: `%PostId%`, `%PublishedAt%`, `%PostTitle%` |
| `--max-sub-directory-name-length` | `100` | Truncate subdirectory names to this many characters |
| `--max-filename-length` | `100` | Truncate filenames to this many characters (extension is preserved) |
| `--file-exists-action` | `BackupIfDifferent` | What to do when a file already exists on disk (see below) |
| `--disable-remote-file-size-check` | off | Skip the HEAD request that compares remote vs. local file sizes |
| `--filenames-fallback-to-content-type` | off | If all filename detection methods fail, generate a name from Content-Type + URL hash |
| `--use-legacy-file-naming` | off | Omit the internal file ID from attachment/media filenames (compatibility with older downloads) |
| `--proxy-server-address` | none | Proxy URL, e.g. `http://host:port`, `socks5://host:port` |
| `--remote-browser-address` | none | WebSocket address of an externally launched Chrome (advanced, see below) |
| `--state-path` | `.patreon-dl-state.json` | Where to save/load the browser auth state |
| `--log-level` | `Default` | `Default` (info only), `Debug`, or `Trace` |

### `--file-exists-action` values

| Value | Behavior |
|-------|----------|
| `KeepExisting` | Skip the download if the file already exists. Most bandwidth-efficient. |
| `AlwaysReplace` | Always re-download and overwrite. Uses the most bandwidth. |
| `BackupIfDifferent` | Download and compare to existing file. If different, rename old file to `<name>.bak` and save new one. **(default)** |
| `ReplaceIfDifferent` | Same as `BackupIfDifferent` but deletes the old file instead of keeping a backup. |

> `--use-legacy-file-naming` is incompatible with `BackupIfDifferent` and `ReplaceIfDifferent`.

## Output structure

### Without `--use-sub-directories`

All files land flat in the download directory, prefixed with the post ID:

```
downloads/CreatorName/
  123456_post_image.png
  123456_attachment_myfile.zip
  123456_media_photo.jpg
  789012_post_video.mp4
  avatar.png           (if --campaign-images)
  cover.jpg            (if --campaign-images)
  123456_description.json   (if --descriptions)
  123456_embed.txt          (if --embeds)
  page_1.json               (if --json)
```

### With `--use-sub-directories`

Each post gets its own folder. Files inside are named without the post-ID prefix:

```
downloads/CreatorName/
  [123456] 2024-03-15 My Post Title/
    post_image.png
    attachment_myfile.zip
    media_photo.jpg
    description.json
    embed.txt
  [789012] 2024-03-10 Another Post/
    post_video.mp4
  avatar.png
  cover.jpg
  page_1.json
```

## File naming

Files are named using a `<type>_<filename>` scheme:

| URL type | Prefix | Example |
|----------|--------|---------|
| Post file | `post_` | `post_artwork.png` |
| Attachment | `attachment_<id>_` | `attachment_abc123_archive.zip` |
| Media | `media_<id>_` | `media_def456_photo.jpg` |
| External embed URL | `external_` | `external_link.html` |
| Avatar | `avatar` | `avatar.png` |
| Cover | `cover` | `cover.jpg` |

If a post contains multiple files with the same name, the internal Patreon media ID is appended to distinguish them: `media_photo_a1b2c3d4.jpg`.

Filenames exceeding `--max-filename-length` are truncated, preserving the extension.

## URL blacklist

A built-in blacklist skips external links to social and hosting sites that can't be downloaded directly (Twitter/X, DeviantArt, Pixiv, FurAffinity, etc.). These URLs are logged but not downloaded.

## Advanced

### Running on a headless server

If you can't open a browser window on the machine running patreon-dl, use a remote Chrome instance:

**On the remote machine (or locally via SSH tunnel):**
```bash
chrome --headless --remote-debugging-port=9222 --user-data-dir=/tmp/chromedata
# Then log in manually via http://localhost:9222 or via SSH-forwarded port
```

**Run patreon-dl pointing at it:**
```bash
uv run patreon-dl --url https://www.patreon.com/somecreator/posts \
  --remote-browser-address ws://127.0.0.1:9222
```

Note: when using a remote browser you must be already logged in — the login wait-loop is still active but it connects to the existing session rather than opening a new tab.

### Using a proxy

```bash
uv run patreon-dl --url https://www.patreon.com/somecreator/posts \
  --proxy-server-address socks5://127.0.0.1:1080
```

Supported schemes: `http`, `https`, `socks4`, `socks5`.

## Development

```bash
# Run tests
uv run pytest

# Run tests with verbose output
uv run pytest -v
```

## License

See `LICENSE.md`.
