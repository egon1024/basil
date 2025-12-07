from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, ScrollableContainer
from textual.widgets import Input, Button, Static, Label
from pathlib import Path
from basil.ui.widgets.server_config import ServerConfigWidget


class ConfigCreateScreen(Screen):
    """
    Screen for creating a new encrypted config file.
    Multi-step process: password confirmation → server setup → save
    """
    
    CSS = """
    ConfigCreateScreen {
        align: center middle;
    }
    
    #create-container {
        width: 70;
        max-height: 90vh;
        border: solid $primary;
        padding: 1 2;
        overflow-y: auto;
    }
    
    #title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    
    .input-label {
        margin-top: 1;
        margin-bottom: 0;
    }
    
    Input {
        margin-bottom: 1;
    }
    
    #action-button {
        width: 100%;
        margin-top: 1;
    }
    
    #error-message {
        color: $error;
        text-align: center;
        margin-top: 1;
        height: auto;
    }
    
    #info-message {
        color: $text-muted;
        text-align: center;
        margin-bottom: 1;
        height: auto;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.step = 1  # 1: password confirm, 2: server setup
        self.password_confirmed = False
        self.connection_tested = False
        self.server_config = None
    
    def compose(self) -> ComposeResult:
        """
        Create the UI - starts with password entry (twice).
        """
        with ScrollableContainer(id="create-container"):
            yield Label("Create New Configuration", id="title")
            yield Static(
                "Enter a password to encrypt your configuration file.",
                id="info-message"
            )
            yield Label("Password:", classes="input-label")
            yield Input(
                password=True,
                placeholder="Enter password",
                id="password-new"
            )
            yield Label("Confirm Password:", classes="input-label")
            yield Input(
                password=True,
                placeholder="Re-enter password",
                id="password-confirm"
            )
            yield Button("Continue", variant="primary", id="action-button")
            yield Static("", id="error-message")
    
    def on_mount(self) -> None:
        """
        Initialize with password from app.
        """
        # Password is already entered in ConfigLoadScreen
        pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button press based on current step.
        """
        if event.button.id == "action-button":
            if self.step == 1:
                self._confirm_password()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Handle Enter key in input fields.
        """
        if self.step == 1:
            # In password confirmation step, submit the form
            self._confirm_password()
    
    def _confirm_password(self) -> None:
        """
        Verify password confirmation matches.
        """
        password_new = self.query_one("#password-new", Input).value
        password_confirm = self.query_one("#password-confirm", Input).value
        error_display = self.query_one("#error-message", Static)
        
        if not password_new:
            error_display.update("Please enter a password")
            return
        
        if not password_confirm:
            error_display.update("Please confirm your password")
            return
        
        if password_confirm != password_new:
            error_display.update("Passwords do not match")
            return
        
        # Store the password
        self.app.new_config_password = password_new
        
        # Password confirmed, move to server setup
        self.password_confirmed = True
        self.step = 2
        self._show_server_setup()
    
    def _show_server_setup(self) -> None:
        """
        Switch to server configuration step.
        """
        container = self.query_one("#create-container", ScrollableContainer)
        container.remove_children()
        
        # Mount new widgets with unique IDs
        container.mount(Label("Create New Configuration", id="title-step2"))
        container.mount(Static(
            "Configure your first Sensu server connection.",
            id="info-message-step2"
        ))
        container.mount(ServerConfigWidget(id="server-widget"))
        container.mount(Static("", id="error-message-step2"))
    
    def on_server_config_widget_connection_tested(
        self, message: ServerConfigWidget.ConnectionTested
    ) -> None:
        """
        Handle connection test result.
        """
        if message.success:
            self.connection_tested = True
            self.server_config = message.config
            # Automatically save and proceed after successful test
            self._save_config()
        else:
            self.connection_tested = False
    
    def _save_config(self) -> None:
        """
        Save the encrypted configuration file.
        """
        if not self.connection_tested or not self.server_config:
            error_display = self.query_one("#error-message-step2", Static)
            error_display.update("Please test the connection first")
            return
        
        try:
            from basil.config_writer import save_encrypted_config
            from basil.client import ConnectionManager
            
            # Build config structure
            config = {
                "connections": [self.server_config]
            }
            
            # Save encrypted config
            save_encrypted_config(
                config,
                self.app.new_config_password,
                self.app.new_config_path
            )
            
            # Load the config and switch to main screen
            connection_manager = ConnectionManager(config)
            self.app.connection_manager = connection_manager
            
            # Clear temporary data
            delattr(self.app, 'new_config_path')
            delattr(self.app, 'new_config_password')
            
            # Switch to main screen
            self.app.push_screen("main")
            
        except Exception as e:
            error_display = self.query_one("#error-message-step2", Static)
            error_display.update(f"Failed to save config: {e}")
