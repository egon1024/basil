from textual.app import ComposeResult
from textual.widgets import DataTable, Static
from textual.containers import Container, Vertical, Horizontal
from typing import List
from rich.text import Text
from basil.client import SensuResource


class ResourceListWidget(DataTable):
    """
    Reusable widget for displaying a list of Sensu resources.
    """
    
    def __init__(self, resource_type: str, *args, **kwargs):
        """
        Initialize the resource list.
        
        Args:
            resource_type: Type of resource (e.g., 'events', 'entities')
        """
        super().__init__(*args, **kwargs)
        self.resource_type = resource_type
        self.resources: List[SensuResource] = []
        self.cursor_type = "row"
        self._columns_setup = False
        self._sort_column = None
        self._sort_reverse = False
        self._initial_sort_applied = False
    
    def on_mount(self) -> None:
        """
        Set up the table when mounted.
        """
        self._setup_columns()
        self._columns_setup = True
    
    def _setup_columns(self) -> None:
        """
        Set up columns based on resource type.
        """
        if self.resource_type == "events":
            self.add_columns("Entity", "Check", "Status", "Output", "Connection")
        elif self.resource_type == "entities":
            self.add_columns("Name", "Class", "Subscriptions", "Connection")
        elif self.resource_type == "silences":
            self.add_columns("Name", "Reason", "Expire", "Connection")
        elif self.resource_type == "checks":
            self.add_columns("Name", "Command", "Interval", "Connection")
        else:
            # Generic columns
            self.add_columns("Name", "Type", "Connection")
    
    def load_resources(self, resources: List[SensuResource]) -> None:
        """
        Load resources into the table.
        """
        self.resources = resources
        
        # Apply default sort for events on first load
        if self.resource_type == "events" and not self._initial_sort_applied:
            self._apply_default_event_sort()
            self._initial_sort_applied = True
        
        # Always clear and reset - this ensures consistency
        self.clear(columns=True)
        self._setup_columns()
        
        # Add new rows
        for idx, resource in enumerate(resources):
            row_data = self._extract_row_data(resource)
            row_key = f"row_{idx}"
            
            # Apply styling for events based on status
            if self.resource_type == "events":
                row_data = self._style_event_row_data(resource, row_data)
            
            self.add_row(*row_data, key=row_key)
    
    def _extract_row_data(self, resource: SensuResource) -> tuple:
        """
        Extract row data from a resource based on type.
        """
        data = resource.data
        
        if self.resource_type == "events":
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
        elif self.resource_type == "entities":
            # Entity objects have metadata and subscriptions attributes
            metadata = getattr(data, 'metadata', None)
            name = getattr(metadata, 'name', 'N/A') if metadata else 'N/A'
            entity_class = getattr(data, 'entity_class', 'N/A')
            subs = getattr(data, 'subscriptions', [])
            
            return (
                name,
                entity_class,
                ", ".join(subs[:3]) if subs else "None",
                resource.connection_name
            )
        elif self.resource_type == "silences":
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
        elif self.resource_type == "checks":
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
        else:
            # Generic fallback
            metadata = getattr(data, 'metadata', None)
            name = getattr(metadata, 'name', str(data)) if metadata else str(data)
            
            return (
                name,
                self.resource_type,
                resource.connection_name
            )
    
    def _style_event_row_data(self, resource: SensuResource, row_data: tuple) -> tuple:
        """
        Apply styling to event rows based on status.
        
        Status 0: passing (dark green background, white text)
        Status 1: warning (yellow background, black text)
        Status 2: error (red background, black text)
        Other: unknown (blue background, white text)
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
    
    def get_selected_resource(self) -> SensuResource | None:
        """
        Get the currently selected resource.
        """
        if self.cursor_row < len(self.resources):
            return self.resources[self.cursor_row]
        return None
    
    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """
        Handle column header clicks to sort the table.
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
        """
        def get_sort_key(resource: SensuResource):
            row_data = self._extract_row_data(resource)
            if column_index < len(row_data):
                value = row_data[column_index]
                # Handle Text objects from styled data
                if hasattr(value, 'plain'):
                    value = value.plain
                # Convert to string and handle numeric sorting for status
                str_value = str(value)
                # Try to convert to int for numeric columns (like status)
                if self.resource_type == "events" and column_index == 2:  # Status column
                    try:
                        return int(str_value)
                    except (ValueError, TypeError):
                        return 999  # Put non-numeric values at the end
                return str_value.lower()
            return ""
        
        self.resources.sort(key=get_sort_key, reverse=reverse)
    
    def _apply_default_event_sort(self) -> None:
        """
        Apply default sort for events: status (desc), then entity (asc), then check (asc).
        """
        def multi_sort_key(resource: SensuResource):
            row_data = self._extract_row_data(resource)
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
