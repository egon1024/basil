from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Vertical, ScrollableContainer
from basil.client import SensuResource
import json


class ResourceDetailWidget(ScrollableContainer):
    """
    Widget for displaying detailed information about a selected resource.
    """
    
    DEFAULT_CSS = """
    ResourceDetailWidget {
        border: solid $primary;
        padding: 1;
    }
    
    .detail-title {
        text-style: bold;
        margin-bottom: 1;
    }
    
    .detail-section {
        margin-bottom: 1;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_resource: SensuResource | None = None
    
    def compose(self) -> ComposeResult:
        """
        Create the detail view components.
        """
        yield Static("Select an item to view details", id="detail-content")
    
    def show_resource(self, resource: SensuResource) -> None:
        """
        Display details for the given resource.
        """
        self.current_resource = resource
        content = self.query_one("#detail-content", Static)
        
        # Build detail view
        lines = []
        lines.append(f"[bold]Connection:[/bold] {resource.connection_name}")
        lines.append(f"[bold]Namespace:[/bold] {resource.connection.namespace}")
        lines.append("")
        
        # Show formatted data
        lines.append("[bold]Resource Data:[/bold]")
        formatted_data = json.dumps(resource.data, indent=2)
        lines.append(formatted_data)
        
        content.update("\n".join(lines))
    
    def clear(self) -> None:
        """
        Clear the detail view.
        """
        self.current_resource = None
        content = self.query_one("#detail-content", Static)
        content.update("Select an item to view details")
