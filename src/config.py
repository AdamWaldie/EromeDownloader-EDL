"""Configuration module for managing constants and settings used across the project.

These configurations aim to improve modularity and readability by consolidating settings
into a single location.
"""

from argparse import ArgumentParser, Namespace
from collections import deque
from dataclasses import dataclass, field
from enum import IntEnum
import os

# ============================
# Paths and Files
# ============================
DOWNLOAD_FOLDER = "Downloads"
URLS_FILE = "URLs.txt"
SESSION_LOG = "session_log.txt"
DUMP_FILE = "profile_dump.txt"

# ============================
# Host Configuration
# ============================
HOST_NETLOC = "www.erome.com"
HOST_PAGE = f"https://{HOST_NETLOC}"

REGIONS = [
    "cn", "cz", "de", "es", "fr", "gr", "it",
    "nl", "jp", "pt", "pl", "rt", "ru", "se",
]

# ============================
# UI & Table Settings
# ============================
BUFFER_SIZE = 5
PROGRESS_COLUMNS_SEPARATOR = "•"

PROGRESS_MANAGER_COLORS = {
    "title_color": "light_cyan3",
    "overall_border_color": "bright_blue",
    "task_border_color": "medium_purple",
}

LOG_MANAGER_CONFIG = {
    "colors": {
        "title_color": "light_cyan3",
        "border_color": "cyan",
    },
    "min_column_widths": {
        "Timestamp": 10,
        "Event": 15,
        "Details": 30,
    },
    "column_styles": {
        "Timestamp": "pale_turquoise4",
        "Event": "pale_turquoise1",
        "Details": "pale_turquoise4",
    },
}

# ============================
# Download Performance
# ============================
CPU_CORES = os.cpu_count() or 4

# OPTIMIZED: Increased max workers for better parallelization
# I/O bound → 2× cores, but keep it reasonable for stability
MAX_WORKERS = min(16, CPU_CORES * 2)  # Back to 16 for better stability

# OPTIMIZED: Async connections
ASYNC_CONNECTIONS = 12  # Keep at reasonable level

KB = 1024
MB = 1024 * KB

THRESHOLDS = [
    (1 * MB, 64 * KB),
    (10 * MB, 128 * KB),
    (100 * MB, 256 * KB),
]

# OPTIMIZED: Increased chunk size for large files
LARGE_FILE_CHUNK_SIZE = 1 * MB  # Increased from 512 * KB to 1 MB

# ============================
# Retry / Timeout
# ============================
MAX_RETRIES = 4
RETRY_BACKOFF_BASE = 1.8

# BALANCED: Not too aggressive, not too conservative
CONNECT_TIMEOUT = 10  # Back to original - connection should be fast
READ_TIMEOUT = 30     # Back to original - most files download quickly

# ============================
# Async toggle
# ============================
USE_ASYNC_DOWNLOADER = False

# ============================
# HTTP
# ============================
class HTTPStatus(IntEnum):
    OK = 200
    FORBIDDEN = 403
    NOT_FOUND = 404
    GONE = 410
    TOO_MANY_REQUESTS = 429
    INTERNAL_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    SERVER_DOWN = 521

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) "
    "Gecko/20100101 Firefox/109.0"
)

# ============================
# Rate limiting
# ============================
# HTTP statuses that indicate the request was rate limited or temporarily
# blocked (Cloudflare/erome). These are retried with a back-off rather than
# treated as a hard failure.
RATE_LIMIT_STATUSES = (
    int(HTTPStatus.TOO_MANY_REQUESTS),
    int(HTTPStatus.FORBIDDEN),
    int(HTTPStatus.SERVICE_UNAVAILABLE),
    int(HTTPStatus.SERVER_DOWN),
)
# Base seconds to wait when rate limited and no Retry-After header is provided.
RATE_LIMIT_BACKOFF = 5
# Upper bound on a single back-off wait, so we never sleep absurdly long.
RATE_LIMIT_MAX_BACKOFF = 120
# Small politeness delay (seconds) between albums to avoid tripping limits.
INTER_ALBUM_DELAY = 1.0

# ============================
# Stall / hang detection
# ============================
# Seconds without any download progress before a stall is reported.
STALL_TIMEOUT = 45
# How often (seconds) the watchdog checks active downloads for stalls.
STALL_CHECK_INTERVAL = 5

# ============================
# File System Configuration
# ============================
MAX_FILENAME_LENGTH = 200  # Maximum length for filenames/folder names

# ============================
# Data Classes
# ============================
@dataclass
class ProgressConfig:
    task_name: str
    item_description: str
    color: str = PROGRESS_MANAGER_COLORS["title_color"]
    panel_width = 40
    overall_buffer: deque = field(default_factory=lambda: deque(maxlen=BUFFER_SIZE))

# ============================
# Arguments
# ============================
def parse_arguments() -> Namespace:
    parser = ArgumentParser(description="Process album downloads.")
    parser.add_argument("-u", "--url", dest="url", type=str)
    parser.add_argument("-p", "--profile", dest="profile", type=str)
    parser.add_argument("--custom-path", dest="custom_path", type=str, default=None)
    return parser.parse_args()
