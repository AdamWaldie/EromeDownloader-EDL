"""Module that provides a command-line tool for downloading from an Erome album URL.

The script validates the provided album URL, collects links to the media files, and
downloads them to a specified local directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import requests

from src.config import HOST_PAGE, USER_AGENT, READ_TIMEOUT, CONNECT_TIMEOUT
from src.download_utils import run_in_parallel_ordered, save_file_with_progress
from src.erome_utils import extract_hostname
from src.file_utils import create_download_directory
from src.general_utils import fetch_page

if TYPE_CHECKING:
    from bs4 import BeautifulSoup
    from requests.models import Response

    from src.managers.live_manager import LiveManager


def get_cookies_header() -> dict[str, str]:
    """Build a cookies header dict from a request object."""
    response = requests.get(HOST_PAGE, timeout=10)
    laravel_session = response.cookies.get("laravel_session")
    xsrf_token = response.cookies.get("XSRF-TOKEN")
    cookies_value = f'XSRF-TOKEN="{xsrf_token}"; laravel_session="{laravel_session}"'
    return {"Cookies": cookies_value}


def configure_session(
    url: str,
    hostname: str,
    album_url: str | None = None,
    timeout: int = CONNECT_TIMEOUT,
    read_timeout: int = READ_TIMEOUT,
) -> Response:
    """Configure a request using a global session."""
    origin_url = f"https://{hostname}"
    return requests.Session().get(
        url,
        stream=True,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": album_url if album_url else origin_url,
            "Origin": origin_url,
            "Connection": "keep-alive",
        },
        timeout=(timeout, read_timeout),
    )


def extract_profile_name(soup: BeautifulSoup) -> str:
    """Extract the profile/uploader name from the album page.
    
    Args:
        soup: BeautifulSoup object of the album page
        
    Returns:
        Profile name or 'Unknown' if not found
    """
    try:
        # PRIMARY METHOD: Look for <a> tag with id="user_name"
        user_link = soup.find("a", {"id": "user_name"})
        if user_link:
            username = user_link.get_text(strip=True)
            if username:
                return username
        
        # FALLBACK 1: Look for <a> tag with class="user"
        profile_link = soup.find("a", class_="user")
        if profile_link:
            username = profile_link.get_text(strip=True)
            if username:
                return username
        
        # FALLBACK 2: Look for username in meta tags
        meta_author = soup.find("meta", {"name": "author"})
        if meta_author and meta_author.get("content"):
            return meta_author.get("content")
        
        # FALLBACK 3: Look in page title pattern
        title_tag = soup.find("title")
        if title_tag:
            title_text = title_tag.get_text()
            # Pattern: "Album Name - Username's albums"
            if " - " in title_text and "'s albums" in title_text:
                parts = title_text.split(" - ")
                if len(parts) > 1:
                    username = parts[1].replace("'s albums", "").strip()
                    if username:
                        return username
    except Exception:
        pass
    
    return "Unknown"


def extract_and_format_album_title(soup: BeautifulSoup, album_id: str, max_length: int = 200) -> str:
    """Extract and format the album title with album ID and profile name.
    
    Args:
        soup: BeautifulSoup object of the album page
        album_id: The album ID extracted from the URL
        max_length: Maximum length for the folder name (default: 200)
    
    Returns:
        Formatted album title in format: "album name (album ID) [profile name]"
        If too long, prioritizes: (album ID) [profile name] over album name
    """
    # Extract the album title from meta tag (original method)
    title_container = soup.find("meta", {"property": "og:title", "content": True})
    album_title = title_container.get("content").strip() if title_container else "Untitled"
    
    # Extract profile name
    profile_name = extract_profile_name(soup)
    
    # Sanitize the album title and profile name (remove invalid characters for filenames)
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        album_title = album_title.replace(char, "")
        profile_name = profile_name.replace(char, "")
    
    # Build the components
    id_part = f"({album_id})"
    profile_part = f"[{profile_name}]"
    
    # Full desired format
    full_name = f"{album_title} {id_part} {profile_part}"
    
    # If it fits within max_length, return it
    if len(full_name) <= max_length:
        return full_name
    
    # If too long, prioritize ID and profile over album name
    # Calculate space needed for ID and profile with separators
    required_space = len(id_part) + len(profile_part) + 2  # +2 for spaces
    
    # Calculate available space for album title
    available_for_title = max_length - required_space
    
    if available_for_title > 10:  # Only include truncated title if we have reasonable space
        truncated_title = album_title[:available_for_title - 3] + "..."
        return f"{truncated_title} {id_part} {profile_part}"
    else:
        # If extremely tight on space, just use ID and profile
        return f"{id_part} {profile_part}"


def get_album_name_for_files(soup: BeautifulSoup) -> str:
    """Extract just the album name (without ID/profile) for file naming.
    
    Args:
        soup: BeautifulSoup object of the album page
        
    Returns:
        Sanitized album name suitable for file naming
    """
    # Extract the album title from meta tag
    title_container = soup.find("meta", {"property": "og:title", "content": True})
    album_title = title_container.get("content").strip() if title_container else "Untitled"
    
    # Sanitize the album title (remove invalid characters for filenames)
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        album_title = album_title.replace(char, "")
    
    return album_title


def extract_download_links(soup: BeautifulSoup) -> list[str]:
    """Extract download links for image and video sources from the album URL.
    
    IMPORTANT: Returns links in the order they appear on the page to preserve sequence.
    """
    download_links = []
    seen = set()  # Track URLs we've already added to avoid duplicates
    
    # Process images first (they typically appear before videos in the HTML)
    image_items = soup.find_all("img", {"class": "img-back"})
    for image_item in image_items:
        url = image_item.get("data-src")
        if url and url not in seen:
            download_links.append(url)
            seen.add(url)
    
    # Then process videos
    video_items = soup.find_all("source")
    for video_item in video_items:
        url = video_item.get("src")
        if url and url not in seen:
            download_links.append(url)
            seen.add(url)
    
    return download_links


def generate_sequential_filename(
    album_name: str,
    file_number: int,
    total_files: int,
    file_extension: str,
    max_length: int = 200,
) -> str:
    """Generate a sequential filename based on album name and file position.
    
    Args:
        album_name: Name of the album
        file_number: Position of this file in the sequence (1-indexed)
        total_files: Total number of files in the album
        file_extension: File extension (e.g., '.mp4', '.jpg')
        max_length: Maximum filename length
        
    Returns:
        Formatted filename: "album name (###).ext"
        If too long, truncates album name to prioritize the number
    """
    # Determine padding based on total files (e.g., 001-100 needs 3 digits)
    num_digits = len(str(total_files))
    padded_number = str(file_number).zfill(num_digits)
    
    # Build the filename
    number_part = f"({padded_number})"
    full_name = f"{album_name} {number_part}{file_extension}"
    
    # If it fits, return it
    if len(full_name) <= max_length:
        return full_name
    
    # If too long, truncate album name while keeping the number
    # Calculate space needed for number and extension
    required_space = len(number_part) + len(file_extension) + 1  # +1 for space
    available_for_name = max_length - required_space
    
    if available_for_name > 5:  # Keep some album name if possible
        truncated_name = album_name[:available_for_name - 3] + "..."
        return f"{truncated_name} {number_part}{file_extension}"
    else:
        # If extremely tight, just use number
        return f"{number_part}{file_extension}"


def download_item(
    download_link: str,
    task_id: int,
    live_manager: LiveManager,
    download_path: str,
    album_url: str,
    album_name: str,
    file_number: int,
    total_files: int,
) -> None:
    """Download a file from the specified download link with sequential naming.
    
    Args:
        download_link: URL of the file to download
        task_id: Task ID for progress tracking
        live_manager: Live manager for progress updates
        download_path: Directory to save the file
        album_url: URL of the album (for headers)
        album_name: Name of the album (for filename)
        file_number: Position of this file (1-indexed)
        total_files: Total number of files in album
    """
    # Extract the file extension from the original URL
    parsed_url = urlparse(download_link)
    original_filename = Path(parsed_url.path).name
    file_extension = Path(original_filename).suffix  # e.g., '.mp4', '.jpg'
    
    # Generate sequential filename
    filename = generate_sequential_filename(
        album_name, file_number, total_files, file_extension
    )
    
    hostname = extract_hostname(download_link)
    final_path = Path(download_path) / filename

    with configure_session(download_link, hostname, album_url) as response:
        save_file_with_progress(response, final_path, task_id, live_manager)


def download_album(
    album_url: str,
    live_manager: LiveManager,
    profile: str | None = None,
    custom_path: str | None = None,
) -> None:
    """Download an album from the given URL."""
    # Cookies used only to fetch soup for download links
    cookies = get_cookies_header()
    soup = fetch_page(album_url, cookies=cookies)
    if soup is None:
        return

    album_id = album_url.rstrip("/").split("/")[-1]
    
    # Get folder name (with ID and profile)
    album_title = extract_and_format_album_title(soup, album_id)
    album_path = album_title if not profile else Path(profile) / album_title
    download_path = create_download_directory(album_path, custom_path=custom_path)
    
    # Get album name for individual file naming (without ID/profile)
    album_name_for_files = get_album_name_for_files(soup)

    # Get download links in order
    download_links = extract_download_links(soup)
    if download_links is None or len(download_links) == 0:
        return

    # Download files with sequential naming
    run_in_parallel_ordered(
        download_item,
        download_links,
        live_manager,
        album_id,
        download_path,
        album_url,
        album_name_for_files,
    )
