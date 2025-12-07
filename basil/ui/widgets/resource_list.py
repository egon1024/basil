from textual.app import ComposeResult
from textual.widgets import DataTable, Static
from textual.containers import Container, Vertical, Horizontal
from typing import List
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
    
    def on_mount(self) -> None:
        """
        Set up the table when mounted.
        """
        self._setup_columns()
    
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
        self.clear()
        
        for resource in resources:
            row_data = self._extract_row_data(resource)
            self.add_row(*row_data)
    
    def _extract_row_data(self, resource: SensuResource) -> tuple:
        """
        Extract row data from a resource based on type.
        """
        data = resource.data
        
        if self.resource_type == "events":
            return (
                data.get("entity", {}).get("metadata", {}).get("name", "N/A"),
                data.get("check", {}).get("metadata", {}).get("name", "N/A"),
                str(data.get("check", {}).get("status", "N/A")),
                data.get("check", {}).get("output", "")[:50],  # Truncate output
                resource.connection_name
            )
        elif self.resource_type == "entities":
            subs = data.get("subscriptions", [])
            return (
                data.get("metadata", {}).get("name", "N/A"),
                data.get("entity_class", "N/A"),
                ", ".join(subs[:3]) if subs else "None",
                resource.connection_name
            )
        elif self.resource_type == "silences":
            return (
                data.get("metadata", {}).get("name", "N/A"),
                data.get("reason", "N/A"),
                str(data.get("expire", "N/A")),
                resource.connection_name
            )
        elif self.resource_type == "checks":
            return (
                data.get("metadata", {}).get("name", "N/A"),
                data.get("command", "N/A")[:30],
                str(data.get("interval", "N/A")),
                resource.connection_name
            )
        else:
            return (
                str(data.get("metadata", {}).get("name", data)),
                self.resource_type,
                resource.connection_name
            )
    
    def get_selected_resource(self) -> SensuResource | None:
        """
        Get the currently selected resource.
        """
        if self.cursor_row < len(self.resources):
            return self.resources[self.cursor_row]
        return None
