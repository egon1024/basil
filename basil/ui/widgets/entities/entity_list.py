# built-in imports
from typing import Any, List

# Third party imports
from rich.text import Text

# Basil imports
from basil.ui.widgets.base_resource_list import BaseResourceListWidget
from basil.client import SensuResource


class EntityListWidget(BaseResourceListWidget):
    """Widget for displaying a list of Sensu entities."""

    def __init__(self, *args, **kwargs):
        """Initialize the entity list widget."""
        super().__init__(*args, **kwargs)
        self._entity_check_counts = {}  # Cache for entity check status counts

    def setup_columns(self) -> None:
        """Set up columns for entity display."""
        self.add_columns("Connection", "Name", "Class", "Checks", "Subscriptions")

    def preprocess_resources(self, resources: List[SensuResource], **kwargs) -> None:
        """
        Preprocess resources before display.

        For entities, we calculate check status counts from events if provided.

        Args:
            resources: List of entity resources
            **kwargs: Must contain 'events' parameter with list of event resources
        """
        events = kwargs.get('events', None)
        if events is not None:
            self._calculate_entity_check_counts(events)

    def _calculate_entity_check_counts(self, events: List[SensuResource]) -> None:
        """
        Calculate check status counts for each entity from events.

        Args:
            events: List of event resources
        """
        self._entity_check_counts = {}

        for event in events:
            data = event.data
            # Get entity name from event
            entity_name = getattr(getattr(data, 'entity', None), 'metadata', None)
            entity_name = getattr(entity_name, 'name', None) if entity_name else None

            if not entity_name:
                continue

            # Create a key combining entity name and connection
            entity_key = (entity_name, event.connection_name)

            # Initialize counts if not present
            if entity_key not in self._entity_check_counts:
                self._entity_check_counts[entity_key] = {"ok": 0, "warning": 0, "critical": 0}

            # Get check status
            check = getattr(data, 'check', None)
            if check:
                status = getattr(check, 'status', None)
                if status == 0:
                    self._entity_check_counts[entity_key]["ok"] += 1
                elif status == 1:
                    self._entity_check_counts[entity_key]["warning"] += 1
                elif status == 2:
                    self._entity_check_counts[entity_key]["critical"] += 1

    def _format_check_counts(self, counts: dict) -> Text:
        """
        Format check counts with colors matching event row styling.

        Args:
            counts: Dictionary with 'ok', 'warning', and 'critical' counts

        Returns:
            Rich Text object with colored counts
        """
        ok_count = counts.get("ok", 0)
        warn_count = counts.get("warning", 0)
        crit_count = counts.get("critical", 0)

        # Build the text with colors similar to event rows
        parts = []
        if ok_count > 0:
            parts.append(Text(str(ok_count), style="white on dark_green"))
        else:
            parts.append(Text(str(ok_count), style="dim"))

        parts.append(Text("/", style="dim"))

        if warn_count > 0:
            parts.append(Text(str(warn_count), style="black on yellow"))
        else:
            parts.append(Text(str(warn_count), style="dim"))

        parts.append(Text("/", style="dim"))

        if crit_count > 0:
            parts.append(Text(str(crit_count), style="white on dark_red"))
        else:
            parts.append(Text(str(crit_count), style="dim"))

        # Combine all parts into a single Text object
        result = Text()
        for part in parts:
            result.append_text(part)

        return result

    def extract_row_data(self, resource: SensuResource) -> tuple:
        """
        Extract row data from an entity resource.

        Args:
            resource: The entity resource

        Returns:
            Tuple of (connection_name, name, entity_class, check_counts, subscriptions)
        """
        data = resource.data

        # Entity objects have metadata and subscriptions attributes
        metadata = getattr(data, 'metadata', None)
        name = getattr(metadata, 'name', 'N/A') if metadata else 'N/A'
        entity_class = getattr(data, 'entity_class', 'N/A')
        subs = getattr(data, 'subscriptions', [])

        # Get check counts for this entity
        entity_key = (name, resource.connection_name)
        counts = self._entity_check_counts.get(entity_key, {"ok": 0, "warning": 0, "critical": 0})

        # Format check counts with colors
        check_counts = self._format_check_counts(counts)

        return (
            resource.connection_name,
            name,
            entity_class,
            check_counts,
            ", ".join(subs[:3]) if subs else "None"
        )

    def apply_row_styling(self, resource: SensuResource, row_data: tuple) -> tuple:
        """
        Apply styling to entity rows based on check status.

        Entities are colored based on their worst check status:
        - Critical: Any critical checks (red background, white text)
        - Warning: Any warning checks and no critical (yellow background, black text)
        - OK: Only OK checks (dark green background, white text)
        - No checks: No status (dim styling)

        Args:
            resource: The entity resource
            row_data: The extracted row data

        Returns:
            Styled row data with Rich Text objects
        """
        data = resource.data
        metadata = getattr(data, 'metadata', None)
        name = getattr(metadata, 'name', 'N/A') if metadata else 'N/A'

        # Get check counts for this entity
        entity_key = (name, resource.connection_name)
        counts = self._entity_check_counts.get(entity_key, {"ok": 0, "warning": 0, "critical": 0})

        # Determine styling based on worst status
        if counts.get("critical", 0) > 0:
            bg_color = "dark_red"
            fg_color = "white"
        elif counts.get("warning", 0) > 0:
            bg_color = "yellow"
            fg_color = "black"
        elif counts.get("ok", 0) > 0:
            bg_color = "dark_green"
            fg_color = "white"
        else:
            # No checks - use dim styling
            bg_color = None
            fg_color = "dim"

        # Apply styling to each cell in the row
        styled_data = []
        for cell in row_data:
            # Handle Text objects (like the formatted check counts)
            if isinstance(cell, Text):
                # For Text objects, we need to update their style
                styled_text = Text(cell.plain)
                if bg_color:
                    styled_text.stylize(f"{fg_color} on {bg_color}")
                else:
                    styled_text.stylize(fg_color)
                styled_data.append(styled_text)
            else:
                # For regular strings
                text_content = str(cell)
                padded_text = text_content.ljust(len(text_content) + 1)
                if bg_color:
                    styled_data.append(Text(padded_text, style=f"{fg_color} on {bg_color}", no_wrap=False, overflow="ellipsis"))
                else:
                    styled_data.append(Text(padded_text, style=fg_color, no_wrap=False, overflow="ellipsis"))

        return tuple(styled_data)

    def get_sort_key(self, resource: SensuResource, column_index: int) -> Any:
        """
        Get sortable value for resource at given column index.

        Args:
            resource: The entity resource
            column_index: The column index being sorted

        Returns:
            Sortable value (string for most columns)
        """
        row_data = self.extract_row_data(resource)
        if column_index < len(row_data):
            value = row_data[column_index]
            # Handle Text objects from styled data
            if hasattr(value, 'plain'):
                value = value.plain
            return str(value).lower()
        return ""
