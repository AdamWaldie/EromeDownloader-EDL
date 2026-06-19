"""Utilities for handling file downloads with progress tracking."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from requests import Response

from src.managers.live_manager import LiveManager

from .config import LARGE_FILE_CHUNK_SIZE, MAX_WORKERS, THRESHOLDS


def get_chunk_size(file_size: int) -> int:
    """Determine the optimal chunk size based on the file size.
    
    OPTIMIZED: Now uses larger chunk sizes from config including 1MB for large files.
    """
    for threshold, chunk_size in THRESHOLDS:
        if file_size < threshold:
            return chunk_size

    return LARGE_FILE_CHUNK_SIZE


def save_file_with_progress(
    response: Response,
    download_path: str,
    task: int,
    live_manager: LiveManager,
    name: str | None = None,
) -> int:
    """Save the content of a response to a file while tracking download progress.

    Registers the download with the live manager's stall watchdog so a frozen
    transfer can be identified, and returns the number of bytes written.
    """
    file_size = int(response.headers.get("content-length", -1))
    chunk_size = get_chunk_size(file_size)
    total_downloaded = 0
    label = name if name is not None else Path(download_path).name

    live_manager.start_download(task, label, file_size)
    try:
        with Path(download_path).open("wb") as file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    file.write(chunk)
                    total_downloaded += len(chunk)
                    # content-length may be missing (-1); only show a percentage
                    # when the total size is known to avoid bogus values.
                    if file_size > 0:
                        progress_percentage = (total_downloaded / file_size) * 100
                        live_manager.update_task(task, completed=progress_percentage)
                    live_manager.record_progress(task, total_downloaded)
    finally:
        live_manager.finish_download(task)

    return total_downloaded


def _collect_results(
    futures: dict,
    live_manager: LiveManager,
    num_items: int,
) -> None:
    """Wait for every submitted download and surface any per-file failure.

    Reading ``future.result()`` is what makes a download error visible: the
    ThreadPoolExecutor stores exceptions on the future, so without this the
    failure is swallowed silently. A failed file is logged and its task is
    forced to a finished state so the overall progress advances past it and the
    album can complete instead of stalling.
    """
    for future in as_completed(futures):
        task_id, file_number, item = futures[future]
        try:
            future.result()
        except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            live_manager.update_log(
                "Download failed",
                f"File {file_number}/{num_items}: {item} - {exc}",
            )
            live_manager.update_task(task_id, completed=100, visible=False)


def run_in_parallel(
    func: callable,
    items: list,
    live_manager: LiveManager,
    identifier: str,
    *args: tuple,
) -> None:
    """Execute a function in parallel for a list of items, using multiple workers."""
    num_items = len(items)
    futures = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        live_manager.add_overall_task(identifier, num_items)

        for current_task, item in enumerate(items):
            task_id = live_manager.add_task(current_task=current_task)
            file_number = current_task + 1
            future = executor.submit(func, item, task_id, live_manager, *args)
            futures[future] = (task_id, file_number, item)

        _collect_results(futures, live_manager, num_items)


def run_in_parallel_ordered(
    func: callable,
    items: list,
    live_manager: LiveManager,
    identifier: str,
    *args: tuple,
) -> None:
    """Execute a function in parallel while maintaining sequential file numbering.

    This function passes the file number and total count to the download function
    so files can be named sequentially (e.g., "Album (001).mp4", "Album (002).jpg")

    Args:
        func: Function to execute (should accept file_number and total_files params)
        items: List of items to process (download links)
        live_manager: Live manager for progress tracking
        identifier: Identifier for the overall task
        *args: Additional arguments to pass (download_path, album_url, album_name)
    """
    num_items = len(items)
    futures = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        live_manager.add_overall_task(identifier, num_items)

        for current_task, item in enumerate(items):
            task_id = live_manager.add_task(current_task=current_task)
            file_number = current_task + 1  # 1-indexed file numbering

            # Pass file_number and total_files to the download function
            future = executor.submit(
                func, item, task_id, live_manager, *args, file_number, num_items,
            )
            futures[future] = (task_id, file_number, item)

        _collect_results(futures, live_manager, num_items)
