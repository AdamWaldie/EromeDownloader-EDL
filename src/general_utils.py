"""Module that provides utilities to the project.

It includes functions to handle common tasks such as sending HTTP requests, parsing
HTML, creating download directories, and clearing the terminal, making it reusable
across projects.
"""

from __future__ import annotations

import logging
import os
import random
import time

import requests
from bs4 import BeautifulSoup

from .config import USER_AGENT, HTTPStatus


def fetch_page(
    url: str,
    cookies: dict[str, str] | None = None,
    timeout: int = 10,
    retries: int = 4,
) -> BeautifulSoup | None:
    """Fetch the HTML content of a webpage."""
    # Create a new session per worker
    session = requests.Session()

    # Erome rejects the default "python-requests" User-Agent with a 403, so
    # present browser-like headers for the page request.
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.5",
    }

    # Track the most recent failure reason so it can be reported clearly,
    # distinguishing an HTTP status (403/404/429/5xx) from a timeout or a
    # connection error rather than emitting an opaque "skipped".
    last_reason = "unknown error"

    for attempt in range(retries):
        try:
            response = session.get(
                url, cookies=cookies, headers=headers, timeout=timeout,
            )
            if response.status_code in (HTTPStatus.NOT_FOUND, HTTPStatus.GONE):
                logging.warning(
                    "Page unavailable (HTTP %s): %s", response.status_code, url,
                )
                return None

            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")

        except requests.HTTPError as http_err:
            status = (
                http_err.response.status_code
                if http_err.response is not None
                else "unknown"
            )
            last_reason = f"HTTP {status}"
            logging.warning("Fetch failed (%s): %s", last_reason, url)

        except requests.Timeout:
            last_reason = "request timed out"
            logging.warning("Fetch failed (timeout): %s", url)

        except requests.ConnectionError:
            last_reason = "connection error"
            logging.warning("Fetch failed (connection error): %s", url)

        except requests.RequestException as req_err:
            last_reason = type(req_err).__name__
            logging.warning("Fetch failed (%s): %s", last_reason, url)

        # Give up on this URL after exhausting retries, but return None instead
        # of exiting so the caller can skip this album and continue with the
        # remaining URLs. A single blocked/rate-limited request (e.g. a 403/429
        # from Cloudflare) must not abort the whole batch.
        if attempt == retries - 1:
            logging.error(
                "Giving up on %s after %d attempts (%s).",
                url, retries, last_reason,
            )
            return None

        # Otherwise, retry with an exponential backoff
        delay = 2 ** (attempt + 1) + random.uniform(1, 2)  # noqa: S311
        logging.info(
            "Retrying (%d/%d) after %s...", attempt + 1, retries, last_reason,
        )
        time.sleep(delay)

    return None


def clear_terminal() -> None:
    """Clear the terminal screen based on the operating system."""
    commands = {
        "nt": "cls",       # Windows
        "posix": "clear",  # macOS and Linux
    }

    command = commands.get(os.name)
    if command:
        os.system(command)  # noqa: S605
