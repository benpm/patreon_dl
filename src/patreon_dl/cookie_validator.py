import logging

from .http_client import PatreonHttpClient

log = logging.getLogger(__name__)


class CookieValidationError(Exception):
    pass


async def validate(client: PatreonHttpClient) -> None:
    """Mirror PatreonCookieValidator.cs: ensure the cookies in the http client
    are sufficient to authenticate against Patreon."""
    cookies = client._client.cookies  # noqa: SLF001 - intentional, we own the client
    names = {c.name for c in cookies.jar}

    if "__cf_bm" not in names:
        log.warning(
            "'__cf_bm' cookie missing — if downloads fail you may need a VPN/proxy (or to stop using one)"
        )
    if "session_id" not in names:
        raise CookieValidationError("session_id cookie not found")
    if "patreon_device_id" not in names:
        raise CookieValidationError("patreon_device_id cookie not found")

    body = await client.download_string("https://www.patreon.com/api/current_user")
    if '"status":"401"' in body.lower():
        raise CookieValidationError("/api/current_user returned 401")
