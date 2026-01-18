"""
Base class for resource list widgets.
"""
# builtin imports
from typing import List, Any, Optional

# third party imports
from textual.widgets import DataTable

# Basil imports
from basil.client import SensuResource


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
        self._initial_sort_applied = False

    def on_mount(self) -> None:
        """Set up the table when mounted."""
        self.setup_columns()
        self._columns_setup = True

    def setup_columns(self) -> None:
        """
        Define columns for this resource type.

        Must call self.add_columns() with column names.
        Example: self.add_columns("Name", "Status", "Connection")

        Subclasses MUST override this method.
        """
        raise NotImplementedError("Subclasses must implement setup_columns()")

    def extract_row_data(self, resource: SensuResource) -> tuple:
        """
        Extract row data from a resource.

        Args:
            resource: The Sensu resource to extract data from

        Returns:
            Tuple of cell values matching the columns defined in setup_columns()

        Subclasses MUST override this method.
        """
        raise NotImplementedError("Subclasses must implement extract_row_data()")

    def get_sort_key(self, resource: SensuResource, column_index: int) -> Any:
        """
        Get sortable value for resource at given column index.

        Args:
            resource: The resource to get sort key for
            column_index: The column index being sorted

        Returns:
            A comparable value for sorting (e.g., string, int, float)

        Subclasses MUST override this method.
        """
        raise NotImplementedError("Subclasses must implement get_sort_key()")

    def apply_row_styling(self, resource: SensuResource, row_data: tuple) -> tuple:  # pylint: disable=unused-argument
        """
        Apply styling to row data.

        Override this method to apply custom styling based on resource state.
        Default implementation returns data unchanged.

        Args:
            resource: The resource for this row
            row_data: The extracted row data tuple

        Returns:
            Row data tuple, potentially with Rich Text styling applied
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
        Preprocess resources before display.

        Override this method to perform any preprocessing needed before displaying
        resources (e.g., calculating derived values, caching related data).

        Args:
            resources: List of resources being loaded
            **kwargs: Additional parameters (e.g., events= for entity check counts)
        """

    def load_resources(self, resources: List[SensuResource], **kwargs) -> None:
        """
        Load resources into the table.

        Args:
            resources: List of resources to display
            **kwargs: Additional parameters for resource-specific preprocessing
        """
        self.resources = resources

        # Allow subclass to preprocess (e.g., entity check counts from events)
        self.preprocess_resources(resources, **kwargs)

        # Apply default sort on first load
        if not self._initial_sort_applied:
            self.apply_default_sort()
            self._initial_sort_applied = True

        # Always clear and reset - this ensures consistency
        self.clear(columns=True)
        self.setup_columns()

        # Add new rows
        for idx, resource in enumerate(resources):
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
        if self.cursor_row < len(self.resources):
            return self.resources[self.cursor_row]
        return None

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """
        Handle column header clicks to sort the table.

        Args:
            event: The header selection event
        """
        event.stop()
        column_index = event.column_index

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
