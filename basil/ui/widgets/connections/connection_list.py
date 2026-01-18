"""
Widget for displaying a list of Connections.
"""
# built-in imports
from typing import Any, List, Dict, Optional

# Basil imports
from textual.widgets import DataTable
from textual.message import Message


class ConnectionListWidget(DataTable):
    """Widget for displaying a list of configured connections."""

    class ConnectionSelected(Message):
        """Message emitted when a connection is selected."""
        def __init__(self, connection: Dict[str, Any]):
            super().__init__()
            self.connection = connection

    def __init__(self, *args, **kwargs):
        """Initialize the connection list widget."""
        super().__init__(*args, **kwargs)
        self.connections: List[Dict[str, Any]] = []
        self.cursor_type = "row"

    def on_mount(self) -> None:
        """Set up the table when mounted."""
        self.add_columns("Name", "URL", "Namespace", "Status")

    def load_connections(self, connections: List[Dict[str, Any]]) -> None:
        """
        Load connections into the table.

        Args:
            connections: List of connection configurations
        """
        self.connections = connections
        self.clear()
        self.add_columns("Name", "URL", "Namespace", "Status")

        for idx, conn in enumerate(connections):
            name = conn.get("name", "N/A")
            url = conn.get("url", "N/A")
            namespace = conn.get("namespace", "default")

            # Determine status - check if this connection is in the active connection manager
            status = "[green]Connected[/green]"  # For now, assume all are connected

            row_key = f"row_{idx}"
            self.add_row(name, url, namespace, status, key=row_key)

    def get_selected_connection(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently selected connection.

        Returns:
            The selected connection dict, or None if no valid selection
        """
        if self.cursor_row < len(self.connections):
            return self.connections[self.cursor_row]
        return None

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:  # pylint: disable=unused-argument
        """
        Handle row selection.

        Args:
            event: The row selection event
        """
        connection = self.get_selected_connection()
        if connection:
            self.post_message(self.ConnectionSelected(connection))
