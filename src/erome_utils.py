"""Module that provides functions for validating and processing Erome album URLs."""

from __future__ import annotations

import logging
import sys
from urllib.parse import urlparse

from .config import HOST_NETLOC, REGIONS


def validate_url(album_url: str) -> str | None:
    """Validate and normalize an Erome album URL."""
    parsed_url = urlparse(album_url.strip())

    # Strip a trailing slash from the path: erome returns a 404 for the
    # ".../a/ID/" form, so ".../a/ID/" must be normalized to ".../a/ID".
    normalized_path = parsed_url.path.rstrip("/")

    # Accept the main host and any regional host, always rewriting to the
    # canonical https://www.erome.com/<path> form.
    if parsed_url.netloc == HOST_NETLOC or parsed_url.netloc in {
        f"{region}.erome.com" for region in REGIONS
    }:
        return f"https://{HOST_NETLOC}{normalized_path}"

    logging.error("Provide a valid Erome URL: %s", album_url)
    return None


def extract_profile_name(profile_url: str) -> str | None:
    """Extract the profile name from the given profile URL."""
    try:
        return profile_url.rstrip("/").split("/")[-1]

    except IndexError:
        logging.exception("Invalid profile URL.")
        sys.exit(1)

    return None


def extract_hostname(url: str) -> str:
    """Extract the hostname from the given URL."""
    parsed_url = urlparse(url)
    return parsed_url.netloc
