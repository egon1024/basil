from basil.ui.widgets.base_resource_list import BaseResourceListWidget
from basil.client import SensuResource
from typing import Any


class SilenceListWidget(BaseResourceListWidget):
    """Widget for displaying a list of Sensu silences."""

    def setup_columns(self) -> None:
        """Set up columns for silence display."""
        self.add_columns("Name", "Reason", "Expire", "Connection")

    def extract_row_data(self, resource: SensuResource) -> tuple:
        """
        Extract row data from a silence resource.

        Args:
            resource: The silence resource

        Returns:
            Tuple of (name, reason, expire, connection_name)
        """
        data = resource.data

        # Silence objects have metadata, reason, and expire attributes
        metadata = getattr(data, 'metadata', None)
        name = getattr(metadata, 'name', 'N/A') if metadata else 'N/A'
        reason = getattr(data, 'reason', 'N/A')
        expire = str(getattr(data, 'expire', 'N/A'))

        return (
            name,
            reason,
            expire,
            resource.connection_name
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
