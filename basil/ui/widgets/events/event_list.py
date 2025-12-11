from basil.ui.widgets.base_resource_list import BaseResourceListWidget
from basil.client import SensuResource
from rich.text import Text
from typing import Any


class EventListWidget(BaseResourceListWidget):
    """Widget for displaying a list of Sensu events."""

    def setup_columns(self) -> None:
        """Set up columns for event display."""
        self.add_columns("Entity", "Check", "Status", "Output", "Connection")

    def extract_row_data(self, resource: SensuResource) -> tuple:
        """
        Extract row data from an event resource.

        Args:
            resource: The event resource

        Returns:
            Tuple of (entity_name, check_name, status, output, connection_name)
        """
        data = resource.data

        # Event objects have entity and check attributes
        entity_name = getattr(getattr(data, 'entity', None), 'metadata', None)
        entity_name = getattr(entity_name, 'name', 'N/A') if entity_name else 'N/A'

        check_name = getattr(getattr(data, 'check', None), 'metadata', None)
        check_name = getattr(check_name, 'name', 'N/A') if check_name else 'N/A'

        check = getattr(data, 'check', None)
        status = str(getattr(check, 'status', 'N/A')) if check else 'N/A'
        output = getattr(check, 'output', '')[:50] if check else ''

        return (
            entity_name,
            check_name,
            status,
            output,
            resource.connection_name
        )

    def apply_row_styling(self, resource: SensuResource, row_data: tuple) -> tuple:
        """
        Apply styling to event rows based on status.

        Status 0: passing (dark green background, white text)
        Status 1: warning (yellow background, black text)
        Status 2: error (red background, white text)
        Other: unknown (blue background, white text)

        Args:
            resource: The event resource
            row_data: The extracted row data

        Returns:
            Styled row data with Rich Text objects
        """
        data = resource.data
        check = getattr(data, 'check', None)

        # Determine styling based on status
        if check:
            status = getattr(check, 'status', None)
            if status == 0:
                bg_color = "dark_green"
                fg_color = "white"
            elif status == 1:
                bg_color = "yellow"
                fg_color = "black"
            elif status == 2:
                bg_color = "dark_red"
                fg_color = "white"
            else:
                bg_color = "blue"
                fg_color = "white"
        else:
            # No check data, apply unknown styling
            bg_color = "blue"
            fg_color = "white"

        # Apply styling to each cell in the row with padding for full-width coloring
        styled_data = []
        for cell in row_data:
            # Pad text to ensure background fills the cell
            text_content = str(cell)
            # Add extra spaces to fill the cell width
            padded_text = text_content.ljust(len(text_content) + 1)
            styled_data.append(Text(padded_text, style=f"{fg_color} on {bg_color}", no_wrap=False, overflow="ellipsis"))

        return tuple(styled_data)

    def apply_default_sort(self) -> None:
        """
        Apply default sort for events: status (desc), then entity (asc), then check (asc).
        """
        def multi_sort_key(resource: SensuResource):
            row_data = self.extract_row_data(resource)
            # Extract entity (index 0), check (index 1), and status (index 2)
            entity = str(row_data[0]).lower() if len(row_data) > 0 else ""
            check = str(row_data[1]).lower() if len(row_data) > 1 else ""
            status = 0
            if len(row_data) > 2:
                try:
                    status = int(str(row_data[2]))
                except (ValueError, TypeError):
                    status = 999
            # Return tuple: negative status for descending, entity and check for ascending
            return (-status, entity, check)

        self.resources.sort(key=multi_sort_key)

    def get_sort_key(self, resource: SensuResource, column_index: int) -> Any:
        """
        Get sortable value for resource at given column index.

        Args:
            resource: The event resource
            column_index: The column index being sorted

        Returns:
            Sortable value (int for status, string for others)
        """
        row_data = self.extract_row_data(resource)
        if column_index < len(row_data):
            value = row_data[column_index]
            # Handle Text objects from styled data
            if hasattr(value, 'plain'):
                value = value.plain
            # Convert to string and handle numeric sorting for status
            str_value = str(value)
            # Try to convert to int for numeric columns (like status)
            if column_index == 2:  # Status column
                try:
                    return int(str_value)
                except (ValueError, TypeError):
                    return 999  # Put non-numeric values at the end
            return str_value.lower()
        return ""
