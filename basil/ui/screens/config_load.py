from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical
from textual.widgets import Input, Button, Static, Label
from textual.binding import Binding
from pathlib import Path
import platform


class ConfigLoadScreen(Screen):
    """
    Screen for loading and decrypting the configuration file.
    """
    
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
    ]
    
    CSS = """
    ConfigLoadScreen {
        align: center middle;
    }
    
    #config-container {
        width: 60;
        height: auto;
        border: solid $primary;
        padding: 1 2;
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
    
    #load-button {
        width: 100%;
        margin-top: 1;
    }
    
    #error-message {
        color: $error;
        text-align: center;
        margin-top: 1;
        height: auto;
    }
    """
    
    def compose(self) -> ComposeResult:
        """
        Create the UI components.
        """
        with Container(id="config-container"):
            yield Label("Load Configuration", id="title")
            yield Static("", id="profile-info")
            yield Label("Password:", classes="input-label")
            yield Input(
                password=True,
                placeholder="Enter decryption password",
                id="password"
            )
            yield Button("Load Configuration", variant="primary", id="load-button")
            yield Static("", id="error-message")
    
    def on_mount(self) -> None:
        """
        Display profile information when screen is mounted.
        """
        if hasattr(self.app, 'current_profile'):
            profile = self.app.current_profile
            profile_info = self.query_one("#profile-info", Static)
            profile_info.update(f"Profile: {profile.name}\n{profile.description}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle load button press.
        """
        if event.button.id == "load-button":
            self._attempt_load()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Handle Enter key in input fields.
        """
        self._attempt_load()
    
    def _attempt_load(self) -> None:
        """
        Attempt to load and decrypt the configuration.
        """
        password_input = self.query_one("#password", Input)
        error_display = self.query_one("#error-message", Static)
        
        password = password_input.value
        
        # Clear previous errors
        error_display.update("")
        
        # Validate inputs
        if not password:
            error_display.update("Please enter a password")
            return
        
        # Get profile from app
        if not hasattr(self.app, 'current_profile'):
            error_display.update("No profile selected")
            return
        
        profile = self.app.current_profile
        config_path = Path(profile.path).expanduser()
        
        # Check if file exists
        if not config_path.exists():
            error_display.update(f"Config file not found: {config_path}")
            return
        
        # Attempt to load and decrypt
        try:
            from basil.config import ConfigLoader
            from basil.client import ConnectionManager
            from basil.profile_manager import ProfileManager
            
            loader = ConfigLoader(config_path)
            config = loader.load(password)
            
            # Update profile's last used timestamp
            profile_manager = ProfileManager()
            profile_manager.update_last_used(profile.name)
            
            # Create ConnectionManager with loaded config
            connection_manager = ConnectionManager(config)
            
            # Store in app and switch to main screen
            self.app.connection_manager = connection_manager
            
            # Clean up profile reference
            if hasattr(self.app, 'current_profile'):
                delattr(self.app, 'current_profile')
            
            self.app.push_screen("main")
            
        except FileNotFoundError as e:
            error_display.update(f"File error: {e}")
        except Exception as e:
            error_display.update(f"Failed to load config: {e}")
    
    def action_quit(self) -> None:
        """
        Exit the application.
        """
        self.app.exit()


class ConfirmDialog(Screen):
    """
    Simple confirmation dialog.
    """
    
    CSS = """
    ConfirmDialog {
        align: center middle;
    }
    
    #dialog-container {
        width: 60;
        height: auto;
        border: solid $primary;
        padding: 1 2;
        background: $surface;
    }
    
    #dialog-message {
        text-align: center;
        margin-bottom: 1;
    }
    
    #button-container {
        layout: horizontal;
        height: auto;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, message: str, callback):
        super().__init__()
        self.message = message
        self.callback = callback
    
    def compose(self) -> ComposeResult:
        """
        Create dialog UI.
        """
        from textual.containers import Container, Horizontal
        from textual.widgets import Button
        
        with Container(id="dialog-container"):
            yield Static(self.message, id="dialog-message")
            with Horizontal(id="button-container"):
                yield Button("Yes", variant="primary", id="yes-button")
                yield Button("No", variant="default", id="no-button")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button press.
        """
        result = event.button.id == "yes-button"
        self.app.pop_screen()
        self.callback(result)
