"""Acquire patreon.com session cookies via Playwright (replaces PuppeteerEngine)."""

import json
import logging
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from .settings import Settings

log = logging.getLogger(__name__)


async def ensure_storage_state(state_path: Path, settings: Settings) -> dict[str, Any]:
    """Return a Playwright storage_state dict with valid Patreon cookies.

    If `state_path` exists, it's loaded. Otherwise launch a Chromium window pointed
    at patreon.com/login, wait for the user to sign in (until session_id cookie
    appears and /api/current_user returns 200), save state to disk, and return it.
    """
    if state_path.exists():
        log.info("Loading saved auth state from %s", state_path)
        with state_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    log.info("No saved auth state — launching browser for login")
    async with async_playwright() as pw:
        if settings.remote_browser_address:
            browser = await pw.chromium.connect_over_cdp(settings.remote_browser_address)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
        else:
            browser = await pw.chromium.launch(headless=False)
            context = await browser.new_context(user_agent=settings.user_agent)

        page = await context.new_page()
        await page.goto(settings.login_page_address)
        log.info("Sign in to Patreon in the browser window. The app will continue automatically once authenticated.")

        # Poll for session_id cookie + a successful login-check response.
        await _wait_for_login(context, settings)

        state_path.parent.mkdir(parents=True, exist_ok=True)
        state = await context.storage_state(path=str(state_path))
        await browser.close()
        log.info("Saved auth state to %s", state_path)
        return state


async def _wait_for_login(context: Any, settings: Settings, poll_seconds: float = 1.5) -> None:
    import asyncio

    while True:
        cookies = await context.cookies("https://www.patreon.com")
        if any(c["name"] == "session_id" for c in cookies):
            try:
                resp = await context.request.get(settings.login_check_address)
                if resp.ok:
                    return
            except Exception as e:  # noqa: BLE001
                log.debug("Login-check request failed (likely not logged in yet): %s", e)
        await asyncio.sleep(poll_seconds)
