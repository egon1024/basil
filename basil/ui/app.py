from textual.app import App
from textual.binding import Binding
from basil.ui.screens.profile_select import ProfileSelectScreen
from basil.ui.screens.config_load import ConfigLoadScreen
from basil.ui.screens.config_create import ConfigCreateScreen
from basil.ui.screens.main import MainScreen


class BasilApp(App):
    """
    Main Basil application.
    """
    
    TITLE = "Basil - Sensu Terminal Client"
    CSS_PATH = "app.css"
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
    ]
    
    def __init__(self):
        super().__init__()
        self.connection_manager = None
        self.current_profile = None
    
    def on_mount(self) -> None:
        """
        Called when app starts.
        """
        # Install screens
        self.install_screen(ProfileSelectScreen(), name="profile_select")
        self.install_screen(ConfigLoadScreen(), name="config_load")
        self.install_screen(ConfigCreateScreen(), name="config_create")
        self.install_screen(MainScreen(), name="main")
        
        # Start with profile selection screen
        self.push_screen("profile_select")
