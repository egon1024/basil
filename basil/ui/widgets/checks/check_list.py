from basil.ui.widgets.base_resource_list import BaseResourceListWidget
from basil.client import SensuResource
from typing import Any


class CheckListWidget(BaseResourceListWidget):
    """Widget for displaying a list of Sensu checks."""

    def setup_columns(self) -> None:
        """Set up columns for check display."""
        self.add_columns("Name", "Command", "Interval", "Connection")

    def extract_row_data(self, resource: SensuResource) -> tuple:
        """
        Extract row data from a check resource.

        Args:
            resource: The check resource

        Returns:
            Tuple of (name, command, interval, connection_name)
        """
        data = resource.data

        # Check objects have metadata, command, and interval attributes
        metadata = getattr(data, 'metadata', None)
        name = getattr(metadata, 'name', 'N/A') if metadata else 'N/A'
        command = getattr(data, 'command', 'N/A')[:30]
        interval = str(getattr(data, 'interval', 'N/A'))

        return (
            name,
            command,
            interval,
            resource.connection_name
        )

    def get_sort_key(self, resource: SensuResource, column_index: int) -> Any:
        """
        Get sortable value for resource at given column index.

        Args:
            resource: The check resource
            column_index: The column index being sorted

        Returns:
            Sortable value (int for interval, string for others)
        """
        row_data = self.extract_row_data(resource)
        if column_index < len(row_data):
            value = row_data[column_index]
            # Interval column (index 2) should sort numerically
            if column_index == 2:
                try:
                    return int(str(value))
                except (ValueError, TypeError):
                    return 999999  # Put non-numeric values at the end
            return str(value).lower()
        return ""
