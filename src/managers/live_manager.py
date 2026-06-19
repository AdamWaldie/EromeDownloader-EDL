"""Module that provides functionality for managing and displaying live updates.

It combines a progress table and a logger table into a real-time display, allowing
dynamic updates of both tables. The `LiveManager` class handles the integration and
refresh of the live view.
"""

from __future__ import annotations

import datetime
import time

from rich.console import Console, Group
from rich.live import Live

from .log_manager import LoggerTable
from .progress_manager import ProgressManager


class LiveManager:
    """Class to manage a live display that combines a progress table and a logger table.

    It allows for real-time updates and refreshes of both progress and logs in a
    terminal.
    """

    def __init__(
        self,
        progress_manager: ProgressManager,
        logger_table: LoggerTable,
        refresh_per_second: int = 10,
    ) -> None:
        """Initialize the progress manager and logger, and set up the live view."""
        self.progress_manager = progress_manager
        self.progress_table = self.progress_manager.create_progress_table()
        self.logger_table = logger_table
        self.console = Console()
        # Rich's Live dashboard only renders when stdout is a real terminal.
        # When running from an IDE run window, a redirected/piped stream, or a
        # notebook, there is no TTY, so the dashboard would render nothing and
        # the script appears to do nothing. Detect that case and fall back to
        # plain printed log lines so there is always visible console output.
        self.plain_output = not self.console.is_terminal
        self.live = Live(
            self._render_live_view(),
            console=self.console,
            refresh_per_second=refresh_per_second,
        )
        self.start_time = time.time()
        self.update_log("Script started", "The script has started execution.")

    def add_overall_task(self, description: str, num_tasks: int) -> None:
        """Call ProgressManager to add an overall task."""
        self.progress_manager.add_overall_task(description, num_tasks)

    def add_task(self, current_task: int = 0, total: int = 100) -> int:
        """Call ProgressManager to add an individual task."""
        return self.progress_manager.add_task(current_task, total)

    def update_task(
        self,
        task_id: int,
        completed: int | None = None,
        advance: int = 0,
        *,
        visible: bool = True,
    ) -> None:
        """Call ProgressManager to update an individual task."""
        self.progress_manager.update_task(task_id, completed, advance, visible=visible)

    def update_log(self, event: str, details: str) -> None:
        """Log an event and refreshes the live display."""
        self.logger_table.log(event, details)
        if self.plain_output:
            # No TTY: the live table is invisible, so print the event directly
            # to give the user feedback on what the script is doing.
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%H:%M:%S",
            )
            print(f"[{timestamp}] {event}: {details}", flush=True)
        self.live.update(self._render_live_view())

    def start(self) -> None:
        """Start the live display."""
        self.live.start()

    def stop(self) -> None:
        """Stop the live display and log the execution time."""
        execution_time = self._compute_execution_time()

        # Log the execution time in hh:mm:ss format
        self.update_log(
            "Script ended",
            f"The script has finished execution. Execution time: {execution_time}",
        )
        self.live.stop()

    # Private methods
    def _render_live_view(self) -> Group:
        """Render the combined live view of the progress table and the logger table."""
        panel_width = self.progress_manager.get_panel_width()
        return Group(
            self.progress_table,
            self.logger_table.render_log_panel(panel_width=2*panel_width),
        )

    def _compute_execution_time(self) -> str:
        """Compute and format the execution time of the script."""
        execution_time = time.time() - self.start_time
        time_delta = datetime.timedelta(seconds=execution_time)

        # Extract hours, minutes, and seconds from the timedelta object
        hours = time_delta.seconds // 3600
        minutes = (time_delta.seconds % 3600) // 60
        seconds = time_delta.seconds % 60

        return f"{hours:02} hrs {minutes:02} mins {seconds:02} secs"


def initialize_managers() -> LiveManager:
    """Initialize and returns the managers for progress tracking and logging."""
    progress_manager = ProgressManager(task_name="Album", item_description="File")
    logger_table = LoggerTable()
    return LiveManager(progress_manager, logger_table)
