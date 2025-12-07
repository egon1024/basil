from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical
from textual.widgets import Input, Button, Static, Label
from pathlib import Path
import platform


class ConfigLoadScreen(Screen):
    """
    Screen for loading and decrypting the configuration file.
    """
    
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
            yield Label("Password:", classes="input-label")
            yield Input(
                password=True,
                placeholder="Enter decryption password",
                id="password"
            )
            yield Label("Config File Path:", classes="input-label")
            yield Input(
                value=self._get_default_config_path(),
                placeholder="Path to encrypted config file",
                id="config-path"
            )
            yield Button("Load Configuration", variant="primary", id="load-button")
            yield Static("", id="error-message")
    
    def _get_default_config_path(self) -> str:
        """
        Get platform-specific default config path.
        """
        system = platform.system()
        
        if system == "Windows":
            base = Path.home() / "AppData" / "Roaming"
        elif system == "Darwin":  # macOS
            base = Path.home() / ".config"
        else:  # Linux and others
            base = Path.home() / ".config"
        
        return str(base / "basil" / "config.enc")
    
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
        config_path_input = self.query_one("#config-path", Input)
        password_input = self.query_one("#password", Input)
        error_display = self.query_one("#error-message", Static)
        
        config_path = Path(config_path_input.value.strip())
        password = password_input.value
        
        # Clear previous errors
        error_display.update("")
        
        # Validate inputs
        if not password:
            error_display.update("Please enter a password")
            return
        
        if not config_path_input.value.strip():
            error_display.update("Please enter a config file path")
            return
        
        # Check if file exists
        if not config_path.exists():
            # Ask user if they want to create a new config
            self._confirm_create_config(config_path, password)
            return
        
        # Attempt to load and decrypt
        try:
            from basil.config import ConfigLoader
            from basil.client import ConnectionManager
            
            loader = ConfigLoader(config_path)
            config = loader.load(password)
            
            # Create ConnectionManager with loaded config
            connection_manager = ConnectionManager(config)
            
            # Store in app and switch to main screen
            self.app.connection_manager = connection_manager
            self.app.push_screen("main")
            
        except FileNotFoundError as e:
            error_display.update(f"File error: {e}")
        except Exception as e:
            error_display.update(f"Failed to load config: {e}")
    
    def _confirm_create_config(self, config_path: Path, password: str) -> None:
        """
        Ask user if they want to create a new config file.
        """
        def handle_response(create: bool) -> None:
            if create:
                # Store only the path - password will be entered fresh in ConfigCreateScreen
                self.app.new_config_path = config_path
                self.app.push_screen("config_create")
            else:
                error_display = self.query_one("#error-message", Static)
                error_display.update(f"Config file not found: {config_path}")
        
        self.app.push_screen(
            ConfirmDialog(
                f"Config file not found:\n{config_path}\n\nCreate new config file?",
                handle_response
            )
        )


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
