"""
Base class for resource detail widgets.
"""
# built-in imports
from datetime import datetime
from typing import Any

# Third party imports
from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import ScrollableContainer

# Basil imports
from basil.client import SensuResource


class BaseResourceDetailWidget(ScrollableContainer):
    """
    Abstract base class for resource detail widgets.

    This base class provides common functionality for displaying detailed
    information about a selected Sensu resource in a scrollable container.

    Subclasses must implement:
        format_resource(resource): Format the resource for display

    The base class provides utility methods for common formatting tasks:
        format_timestamp(): Convert Unix timestamp to readable string
        format_duration(): Convert seconds to readable duration
        get_status_markup(): Get colored markup for status codes
        safe_get(): Safely get attributes from objects or dicts
    """

    DEFAULT_CSS = """
    BaseResourceDetailWidget {
        border: solid $primary;
        padding: 1;
    }

    .detail-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .detail-section {
        margin-bottom: 1;
    }

    .section-header {
        text-style: bold;
        color: $secondary;
        margin-top: 1;
        margin-bottom: 1;
    }

    .field-label {
        color: $text-muted;
    }

    .status-ok {
        color: $success;
        text-style: bold;
    }

    .status-warning {
        color: $warning;
        text-style: bold;
    }

    .status-critical {
        color: $error;
        text-style: bold;
    }
    """

    def __init__(self, *args, **kwargs):
        """Initialize the resource detail widget."""
        super().__init__(*args, **kwargs)
        self.current_resource: Optional[SensuResource] = None

    def on_key(self, event) -> None:
        """Override to not consume e, n, s, c, r keys - let them bubble to Screen."""
        if event.key in ('e', 'n', 'c', 'r'):
            # Don't handle these keys, let them bubble up
            return
        # For 's' and other keys, use default ScrollableContainer behavior
        super().on_key(event)  # pylint: disable=no-member

    def compose(self) -> ComposeResult:
        """Create the detail view components."""
        yield Static("Select an item to view details", id="detail-content")

    def format_resource(self, resource: SensuResource) -> str:
        """
        Format a resource for display.

        Args:
            resource: The resource to format

        Returns:
            Rich-formatted string ready for display

        Subclasses MUST override this method.
        """
        raise NotImplementedError("Subclasses must implement format_resource()")

    def show_resource(self, resource: SensuResource) -> None:
        """
        Display details for the given resource.

        Args:
            resource: The resource to display
        """
        self.current_resource = resource
        content = self.query_one("#detail-content", Static)
        formatted = self.format_resource(resource)
        content.update(formatted)

    def clear(self) -> None:
        """Clear the detail view."""
        self.current_resource = None
        content = self.query_one("#detail-content", Static)
        content.update("Select an item to view details")

    # Utility methods for subclasses

    def format_timestamp(self, timestamp: int) -> str:
        """
        Format a Unix timestamp into a readable string.

        Args:
            timestamp: Unix timestamp (seconds since epoch)

        Returns:
            Formatted date/time string, or "N/A" if invalid
        """
        if not timestamp:
            return "N/A"
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:  # pylint: disable=bare-except
            return str(timestamp)

    def format_duration(self, duration: float) -> str:
        """
        Format duration in seconds to a readable string.

        Args:
            duration: Duration in seconds

        Returns:
            Human-readable duration (e.g., "123ms", "1.5s", "2m 30s")
        """
        if duration is None:
            return "N/A"
        if duration < 1:
            return f"{duration*1000:.0f}ms"
        if duration < 60:
            return f"{duration:.2f}s"

        mins = int(duration // 60)
        secs = duration % 60
        return f"{mins}m {secs:.0f}s"

    def get_status_markup(self, status: int, state: str) -> str:
        """
        Get colored markup for status.

        Args:
            status: Status code (0=OK, 1=WARNING, 2=CRITICAL)
            state: State string (e.g., "passing", "failing")

        Returns:
            Rich markup string with colored status
        """
        status_map = {
            0: ("OK", "status-ok"),
            1: ("WARNING", "status-warning"),
            2: ("CRITICAL", "status-critical"),
        }
        status_text, css_class = status_map.get(status, (f"UNKNOWN ({status})", "status-warning"))
        return f"[{css_class}]{status_text}[/{css_class}] ({state})"

    def safe_get(self, obj: Any, attr: str, default: Any = None) -> Any:
        """
        Safely get an attribute from an object, handling both dict and object access.

        Args:
            obj: Object or dict to get attribute from
            attr: Attribute name
            default: Default value if attribute not found

        Returns:
            Attribute value or default
        """
        if obj is None:
            return default

        # Try dict-like access first
        if isinstance(obj, dict):
            return obj.get(attr, default)

        # Try object attribute access
        if hasattr(obj, attr):
            value = getattr(obj, attr, default)
            # Return None as default, not empty values
            if value is None or value == '' or value == [] or value == {}:
                return default
            return value

        return default
