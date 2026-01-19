"""
Base class for resource list widgets.
"""
# builtin imports
from typing import List, Any, Optional, Dict, Tuple

# third party imports
from rich.text import Text
from textual import work
from textual.widgets import DataTable
from textual.worker import Worker, WorkerState

# Basil imports
from basil.client import SensuResource, SensuConnection

class BaseResourceListWidget(DataTable):
    """
    Abstract base class for resource list widgets.

    This base class provides common functionality for displaying lists of
    Sensu resources in a DataTable format with sorting and selection support.

    Subclasses must implement:
        setup_columns(): Define column headers for the resource type
        extract_row_data(resource): Extract data tuple for one row
        get_sort_key(resource, column_index): Get sortable value for a column

    Subclasses may override:
        apply_row_styling(resource, row_data): Apply styling to row (default: no styling)
        apply_default_sort(): Apply default sorting (default: no sorting)
        preprocess_resources(resources, **kwargs): Preprocess before display (default: no-op)
    """

    def __init__(self, *args, **kwargs):
        """Initialize the resource list widget."""
        super().__init__(*args, **kwargs)
        self.resources: List[SensuResource] = []
        self.cursor_type = "row"
        self._columns_setup = False
        self._sort_column = None
        self._sort_reverse = False
        self._sort_reverse = False
        self._initial_sort_applied = False
        self._original_column_labels: Dict[Any, str] = {}
        self._using_default_sort = False

        # Worker tracking for parallel loading
        self.pending_results: Dict[str, List[SensuResource]] = {}
        self.completed_worker_count: int = 0
        self.expected_worker_count: int = 0
        self.active_workers: List[Worker] = []
        self.is_loading: bool = False
        self._batch_timer = None
        self._load_kwargs: Dict[str, Any] = {}

    def on_mount(self) -> None:
        """Set up the table when mounted."""
        self.setup_columns()
        self._columns_setup = True

    def add_column(self, label: str, *args, **kwargs) -> Any:
        """Override to store original label."""
        key = super().add_column(label, *args, **kwargs)
        # Store clean label without sort indicators for future updates
        clean_label = str(label).replace(" ▲", "").replace(" ▼", "")
        self._original_column_labels[key] = clean_label
        return key

    def _update_sort_indicators(self) -> None:
        """Update column headers with sort indicators."""
        if not self.columns:
            return

        col_keys = list(self.columns.keys())

        for idx, key in enumerate(col_keys):
            col = self.columns[key]
            # Use original label or current if not found (fallback)
            original_label = self._original_column_labels.get(key, str(col.label))

            if idx == self._sort_column:
                # Add indicator
                arrow = " ▼" if self._sort_reverse else " ▲"
                col.label = Text(f"{original_label}{arrow}")
            else:
                # Reset to original
                col.label = Text(original_label)

        self.refresh()

    def setup_columns(self) -> None:
        """
        Define columns for this resource type.

        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement setup_columns()")

    def extract_row_data(self, resource: SensuResource) -> tuple:
        """
        Extract data for a row from a resource.

        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement extract_row_data()")

    def get_sort_key(self, resource: SensuResource, column_index: int) -> Any:
        """
        Get the value to sort by for a given column.

        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement get_sort_key()")

    def apply_row_styling(self, resource: SensuResource, row_data: tuple) -> tuple:  # pylint: disable=unused-argument
        """
        Apply styling to row data.

        Default implementation returns row_data unchanged.
        """
        return row_data

    def apply_default_sort(self) -> None:
        """
        Apply default sort order.

        Override this method if your resource type needs a default sort order.
        Default implementation does nothing (displays in load order).
        """

    def preprocess_resources(self, resources: List[SensuResource], **kwargs) -> None:
        """
        Preprocess resources before they are displayed.
        Useful for bulk data fetching or augmentation.
        """

    def load_resources(self, resources: List[SensuResource], **kwargs) -> None:
        """
        Load a list of resources into the table.

        Args:
            resources: The list of resource objects to display
            **kwargs: Additional arguments passed to preprocess_resources
        """
        self.resources = resources
        self.clear()

        # Pre-process resources (e.g., fetch extra data)
        self.preprocess_resources(self.resources, **kwargs)

        # Apply default sort if needed and not already sorted,
        # OR re-apply existing user sort if present
        if self._using_default_sort:
            self.apply_default_sort()
        elif self._sort_column is not None:
            self._sort_resources(self._sort_column, self._sort_reverse)
        else:
            self.apply_default_sort()
            self._using_default_sort = True
            # Mark initial sort as applied (though we don't check it anymore, good for state)
            self._initial_sort_applied = True

        # Update sort indicators in headers
        self._update_sort_indicators()

        for idx, resource in enumerate(self.resources):
            row_data = self.extract_row_data(resource)
            row_data = self.apply_row_styling(resource, row_data)
            row_key = f"row_{idx}"
            self.add_row(*row_data, key=row_key)

    def get_selected_resource(self) -> Optional[SensuResource]:
        """
        Get the currently selected resource.

        Returns:
            The selected SensuResource, or None if no valid selection
        """

        if 0 <= self.cursor_row < len(self.resources):
            return self.resources[self.cursor_row]

        return None

    @work(thread=True, exclusive=False)
    async def fetch_from_connection_worker(
        self,
        connection: SensuConnection,
        resource_type: str
    ) -> Tuple[str, List[SensuResource]]:
        """
        Fetch resources from one connection in a worker thread.

        Args:
            connection: The SensuConnection to fetch from
            resource_type: Type of resource to fetch

        Returns:
            Tuple of (connection_name, resources)
        """
        # Get connection manager from app
        connection_manager = self.app.connection_manager
        results = connection_manager.get_from_connection(connection, resource_type)

        return (connection.name, results)

    def load_resources_parallel(
        self,
        connection_manager,
        resource_type: str,
        timeout: float = 10.0,
        **kwargs
    ) -> None:
        """
        Load resources from all connections in parallel.

        Uses accumulator pattern with batched updates.

        Args:
            connection_manager: The ConnectionManager instance
            resource_type: Type of resource to fetch
            timeout: Maximum seconds to wait for all workers
            **kwargs: Additional parameters passed to preprocess_resources
        """
        # Cancel any existing workers and timers
        self.cancel_workers()

        # Reset accumulator
        self.pending_results = {}
        self.completed_worker_count = 0
        connections = connection_manager.get_all_connections()
        self.expected_worker_count = len(connections)
        self.is_loading = True

        # Store kwargs for reuse during batched updates
        self._load_kwargs = kwargs

        if self.expected_worker_count == 0:
            # No connections configured
            self.clear()
            self.add_row("No connections configured")
            return

        # Show loading state
        self.clear()
        self.add_row(f"Loading from {len(connections)} server(s)...")

        # Start a worker for each connection
        for conn in connections:
            worker = self.fetch_from_connection_worker(conn, resource_type)
            self.active_workers.append(worker)

        # Set timeout timer
        self.set_timer(timeout, self._timeout_handler)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker completion."""
        if not self.is_loading:
            return

        if event.state == WorkerState.SUCCESS:
            # Accumulate result
            conn_name, resources = event.worker.result
            self.pending_results[conn_name] = resources
            self.completed_worker_count += 1

            # Check if all workers completed
            if self.completed_worker_count >= self.expected_worker_count:
                self._finalize_load()
            else:
                # Schedule batch update if not already scheduled
                if not self._batch_timer:
                    self._batch_timer = self.set_timer(0.5, self._flush_updates)

        elif event.state == WorkerState.ERROR:
            # Log error but continue waiting for other workers
            self.log.error(f"Worker failed: {event.worker.error}")
            self.completed_worker_count += 1

            # Still check if we should finalize (count failed workers)
            if self.completed_worker_count >= self.expected_worker_count:
                self._finalize_load()

    def _flush_updates(self) -> None:
        """Flush currently available results to the UI."""
        self._batch_timer = None
        if not self.is_loading:
            return

        # Combine available results
        all_resources = []
        for resources in self.pending_results.values():
            all_resources.extend(resources)

        # Update UI with currently available data
        # Note: We don't clear loading state yet
        self.load_resources(all_resources, **getattr(self, '_load_kwargs', {}))

        # Add loading indicator at the bottom if still loading
        pending_count = self.expected_worker_count - len(self.pending_results)
        if pending_count > 0:
            # We can't easily add a row that isn't a resource in DataTable easily if typed
            # but we can maybe set the title or subtitle?
            # For now, just having partial data is better than nothing.
            pass

    def _finalize_load(self) -> None:
        """Combine all results and update UI once."""
        # Cancel batch timer if running
        if self._batch_timer:
            self._batch_timer.stop()
            self._batch_timer = None

        # Combine all results
        all_resources = []
        for resources in self.pending_results.values():
            all_resources.extend(resources)

        # Call existing load_resources with combined data
        self.load_resources(all_resources, **getattr(self, '_load_kwargs', {}))

        # Cleanup
        self.is_loading = False
        self.pending_results = {}
        self.active_workers = []
        self._load_kwargs = {}

    def _timeout_handler(self) -> None:
        """Called if workers don't complete within timeout."""
        if self.is_loading:
            self.log.warning(
                f"Timeout: {len(self.pending_results)}/{self.expected_worker_count} "
                f"servers responded"
            )
            self._finalize_load()

    def cancel_workers(self) -> None:
        """Cancel all active workers."""
        for worker in self.active_workers:
            worker.cancel()
        self.active_workers = []
        self.is_loading = False
        if self._batch_timer:
            self._batch_timer.stop()
            self._batch_timer = None

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """
        Handle column header clicks to sort the table.

        Args:
            event: The header selection event
        """
        event.stop()
        column_index = event.column_index

        # User manual sort - disable default sort tracking
        self._using_default_sort = False

        # Toggle sort direction if clicking same column
        if self._sort_column == column_index:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column_index
            self._sort_reverse = False

        # Sort resources and reload
        self._sort_resources(column_index, self._sort_reverse)
        self.load_resources(self.resources)

    def _sort_resources(self, column_index: int, reverse: bool = False) -> None:
        """
        Sort resources by the specified column.

        Args:
            column_index: The column index to sort by
            reverse: Whether to reverse the sort order
        """
        def get_sort_key_wrapper(resource: SensuResource):
            return self.get_sort_key(resource, column_index)

        self.resources.sort(key=get_sort_key_wrapper, reverse=reverse)
