"""
Widget for displaying a list of Silences.
"""
# built-in imports
from typing import Any

# Basil imports
from basil.ui.widgets.base_resource_list import BaseResourceListWidget
from basil.client import SensuResource


class SilenceListWidget(BaseResourceListWidget):  # pylint: disable=too-many-ancestors
    """Widget for displaying a list of Sensu silences."""

    def setup_columns(self) -> None:
        """Set up columns for silence display."""
        self.add_columns("Connection", "Name", "Reason", "Expire")

    def extract_row_data(self, resource: SensuResource) -> tuple:
        """
        Extract row data from a silence resource.

        Args:
            resource: The silence resource

        Returns:
            Tuple of (connection_name, name, reason, expire)
        """
        data = resource.data

        # Silence objects have metadata, reason, and expire attributes
        metadata = getattr(data, 'metadata', None)
        name = getattr(metadata, 'name', 'N/A') if metadata else 'N/A'
        reason = getattr(data, 'reason', 'N/A')
        expire_value = getattr(data, 'expire', 'N/A')
        expire = 'Never' if expire_value == -1 else str(expire_value)

        return (
            resource.connection_name,
            name,
            reason,
            expire
        )

    def get_sort_key(self, resource: SensuResource, column_index: int) -> Any:
        """
        Get sortable value for resource at given column index.

        Args:
            resource: The silence resource
            column_index: The column index being sorted

        Returns:
            Sortable value (string for all columns)
        """
        row_data = self.extract_row_data(resource)
        if column_index < len(row_data):
            value = row_data[column_index]
            return str(value).lower()
        return ""
