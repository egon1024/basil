"""
Widget for configuring Sensu server connection details.
"""
# Built-in imports
from typing import Dict, Any

# 3rd party imports
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Button, Static, Label
from textual.widget import Widget
from textual.message import Message

# Basil imports
from basil.utils.connection_test import test_sensu_connection

class ServerConfigWidget(Widget):
    """
    Reusable widget for configuring a Sensu server connection.
    """

    DEFAULT_CSS = """
    ServerConfigWidget {
        padding: 1;
        height: auto;
    }

    ServerConfigWidget Vertical {
        height: auto;
    }

    .input-label {
        margin-top: 1;
        margin-bottom: 0;
    }

    Input, Select {
        margin-bottom: 1;
    }

    #test-button {
        width: 100%;
        margin-top: 1;
    }

    #test-status {
        text-align: center;
        margin-top: 1;
        height: auto;
    }
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the widget.
        """
        super().__init__(*args, **kwargs)
        self.auth_type = "api_key"  # or "username_password"

    def compose(self) -> ComposeResult:
        """
        Create the server config form.
        """
        with Vertical():
            yield Label("Server Name:", classes="input-label")
            yield Input(placeholder="e.g., production", id="server-name")

            yield Label("Server URL:", classes="input-label")
            yield Input(placeholder="https://sensu.example.com", id="server-url")

            yield Label("Username:", classes="input-label")
            yield Input(placeholder="Enter username", id="username")

            yield Label("Password:", classes="input-label")
            yield Input(password=True, placeholder="Enter password", id="password-input")

            yield Label("Namespace:", classes="input-label")
            yield Input(value="default", placeholder="default", id="namespace")

            yield Button("Test Connection", variant="primary", id="test-button")
            yield Static("", id="test-status")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle test connection button.
        """
        if event.button.id == "test-button":
            self._test_connection()

    def _test_connection(self) -> None:
        """
        Test the connection with current settings.
        """

        config = self.get_config()
        status_display = self.query_one("#test-status", Static)

        # Validate required fields
        if not config.get("name"):
            status_display.update("[red]Error: Server name is required[/red]")
            return

        if not config.get("url"):
            status_display.update("[red]Error: Server URL is required[/red]")
            return

        if not config.get("username") or not config.get("password"):
            status_display.update("[red]Error: Username and password are required[/red]")
            return

        status_display.update("[yellow]Testing connection...[/yellow]")

        # Test connection
        success, message = test_sensu_connection(config)

        if success:
            status_display.update(f"[green]✓ {message}[/green]")
            # Emit custom event that connection test succeeded
            self.post_message(ServerConfigWidget.ConnectionTested(True, config))
        else:
            status_display.update(f"[red]✗ {message}[/red]")
            self.post_message(ServerConfigWidget.ConnectionTested(False, config))

    def get_config(self) -> Dict[str, Any]:
        """
        Get the current server configuration.
        """
        config = {
            "name": self.query_one("#server-name", Input).value.strip(),
            "url": self.query_one("#server-url", Input).value.strip(),
            "namespace": self.query_one("#namespace", Input).value.strip() or "default",
            "username": self.query_one("#username", Input).value.strip(),
            "password": self.query_one("#password-input", Input).value
        }

        return config

    class ConnectionTested(Message):
        """
        Message emitted when connection test completes.
        """
        def __init__(self, success: bool, config: Dict[str, Any]):
            super().__init__()
            self.success = success
            self.config = config
