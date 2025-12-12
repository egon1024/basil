from textual.app import ComposeResult
from textual.widgets import Static, Button, Label
from textual.containers import ScrollableContainer, Vertical, Horizontal
from textual.message import Message
from basil.ui.widgets.server_config import ServerConfigWidget
from typing import Dict, Any, Optional


class ConnectionDetailWidget(ScrollableContainer):
    """
    Widget for displaying and editing connection details.
    Supports CRUD operations on connections.
    """

    DEFAULT_CSS = """
    ConnectionDetailWidget {
        border: solid $primary;
        padding: 1;
        height: auto;
    }

    ConnectionDetailWidget > * {
        height: auto;
    }

    ConnectionDetailWidget Vertical {
        height: auto;
    }

    .detail-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        height: auto;
    }

    .button-row {
        height: auto;
        margin-top: 0;
        margin-bottom: 1;
    }

    .button-row Button {
        margin-right: 1;
        min-width: 10;
    }

    #connection-form {
        height: auto;
        margin-bottom: 0;
    }

    #connection-form Vertical {
        height: auto;
    }
    """

    class ConnectionSaved(Message):
        """Message emitted when a connection is saved."""
        def __init__(self, connection: Dict[str, Any], is_new: bool):
            super().__init__()
            self.connection = connection
            self.is_new = is_new

    class ConnectionDeleted(Message):
        """Message emitted when a connection is deleted."""
        def __init__(self, connection_name: str):
            super().__init__()
            self.connection_name = connection_name

    def __init__(self, *args, **kwargs):
        """Initialize the connection detail widget."""
        super().__init__(*args, **kwargs)
        self.current_connection: Optional[Dict[str, Any]] = None
        self.is_editing = False
        self.is_new = False

    def compose(self) -> ComposeResult:
        """Create the detail view components."""
        yield Static("Select a connection to view details", id="detail-title", classes="detail-title")
        yield ServerConfigWidget(id="connection-form")
        with Horizontal(classes="button-row"):
            yield Button("New", variant="success", id="new-button")
            yield Button("Save", variant="primary", id="save-button")
            yield Button("Delete", variant="error", id="delete-button")
            yield Button("Clear", variant="default", id="clear-button")
            yield Button("Cancel", id="cancel-button")

    def on_mount(self) -> None:
        """Initialize the widget when mounted."""
        # Delay UI state update to ensure all widgets are ready
        self.call_after_refresh(self._update_ui_state)

    def show_connection(self, connection: Dict[str, Any]) -> None:
        """
        Display details for the given connection.

        Args:
            connection: The connection configuration to display
        """
        self.current_connection = connection.copy()
        self.is_editing = False
        self.is_new = False
        self._populate_form(connection)
        self._update_ui_state()

    def show_new_connection(self) -> None:
        """Show form for creating a new connection."""
        self.current_connection = None
        self.is_editing = True
        self.is_new = True
        self._clear_form()
        self._update_ui_state()

    def clear(self) -> None:
        """Clear the detail view."""
        self.current_connection = None
        self.is_editing = False
        self.is_new = False
        self._clear_form()
        self._update_ui_state()

    def _populate_form(self, connection: Dict[str, Any]) -> None:
        """
        Populate the form with connection data.

        Args:
            connection: Connection configuration to load into form
        """
        form = self.query_one("#connection-form", ServerConfigWidget)

        # Update title
        title = self.query_one("#detail-title", Static)
        title.update(f"Connection: {connection.get('name', 'Unknown')}")

        # Populate form fields
        form.query_one("#server-name").value = connection.get("name", "")
        form.query_one("#server-url").value = connection.get("url", "")
        form.query_one("#username").value = connection.get("username", "")
        form.query_one("#namespace").value = connection.get("namespace", "default")

        # NEVER populate password field - passwords should never be displayed
        form.query_one("#password-input").value = ""

        # Clear test status
        form.query_one("#test-status", Static).update("")

    def _clear_form(self) -> None:
        """Clear all form fields."""
        form = self.query_one("#connection-form", ServerConfigWidget)

        # Update title
        title = self.query_one("#detail-title", Static)
        if self.is_new:
            title.update("New Connection")
        else:
            title.update("Select a connection to view details")

        # Clear all form fields
        form.query_one("#server-name").value = ""
        form.query_one("#server-url").value = ""
        form.query_one("#username").value = ""
        form.query_one("#password-input").value = ""
        form.query_one("#namespace").value = "default"
        form.query_one("#test-status", Static).update("")

    def _update_ui_state(self) -> None:
        """Update button enabled/disabled state based on current state."""
        try:
            save_button = self.query_one("#save-button", Button)
            delete_button = self.query_one("#delete-button", Button)
            new_button = self.query_one("#new-button", Button)
            clear_button = self.query_one("#clear-button", Button)
            cancel_button = self.query_one("#cancel-button", Button)

            # Always show all buttons, just enable/disable them
            if self.is_new:
                # Creating new connection
                new_button.disabled = True
                save_button.disabled = False
                delete_button.disabled = True
                clear_button.disabled = True
                cancel_button.disabled = False
            elif self.current_connection:
                # Viewing/editing existing connection
                new_button.disabled = False
                save_button.disabled = False
                delete_button.disabled = False
                clear_button.disabled = False
                cancel_button.disabled = True
            else:
                # No selection
                new_button.disabled = False
                save_button.disabled = True
                delete_button.disabled = True
                clear_button.disabled = True
                cancel_button.disabled = True
        except Exception as e:
            # Widgets not yet mounted - log for debugging
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button presses.

        Args:
            event: The button press event
        """
        if event.button.id == "save-button":
            self._save_connection()
        elif event.button.id == "delete-button":
            self._delete_connection()
        elif event.button.id == "new-button":
            self.show_new_connection()
        elif event.button.id == "clear-button":
            self.clear()
        elif event.button.id == "cancel-button":
            self.clear()

    def _save_connection(self) -> None:
        """Save the current connection configuration."""
        form = self.query_one("#connection-form", ServerConfigWidget)
        config = form.get_config()

        # Validate required fields
        if not config.get("name"):
            self.app.notify("Connection name is required", severity="error")
            return

        if not config.get("url"):
            self.app.notify("Server URL is required", severity="error")
            return

        # For existing connections, if password is empty, preserve the old password
        if not self.is_new and self.current_connection and not config.get("password"):
            # Keep the existing password (it's stored in the config file)
            config["password"] = self.current_connection.get("password", "")

        # Validate credentials are present (either from form or preserved)
        if not config.get("username") or not config.get("password"):
            self.app.notify("Username and password are required", severity="error")
            return

        # Emit save message
        self.post_message(self.ConnectionSaved(config, self.is_new))

    def _delete_connection(self) -> None:
        """Delete the current connection."""
        if not self.current_connection:
            return

        connection_name = self.current_connection.get("name")
        if not connection_name:
            return

        # Emit delete message
        self.post_message(self.ConnectionDeleted(connection_name))

    def on_server_config_widget_connection_tested(
        self, event: ServerConfigWidget.ConnectionTested
    ) -> None:
        """
        Handle connection test results from ServerConfigWidget.

        Args:
            event: The connection test event
        """
        # Event is already handled by ServerConfigWidget display
        # We just need to prevent it from bubbling
        event.stop()
