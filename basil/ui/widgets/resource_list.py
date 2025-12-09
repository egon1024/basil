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
        self._columns_setup = False
    
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
        
        # Always clear and reset - this ensures consistency
        self.clear(columns=True)
        self._setup_columns()
        
        # Add new rows
        for resource in resources:
            row_data = self._extract_row_data(resource)
            self.add_row(*row_data)
    
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
    
    def get_selected_resource(self) -> SensuResource | None:
        """
        Get the currently selected resource.
        """
        if self.cursor_row < len(self.resources):
            return self.resources[self.cursor_row]
        return None
