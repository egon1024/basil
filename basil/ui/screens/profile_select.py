# Built-in imports
from datetime import datetime
from pathlib import Path

# 3rd party imports
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal
from textual.widgets import Button, Static, Label, DataTable, Input
from textual.binding import Binding

# Basil imports
from basil.profile_manager import ProfileManager, Profile
from basil.ui.widgets.path_input import PathInput


class ProfileSelectScreen(Screen):
    """
    Screen for selecting or managing configuration profiles.
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("n", "new_profile", "New Profile", show=True),
        Binding("i", "import_profile", "Import", show=True),
        Binding("d", "delete_profile", "Delete", show=True),
        Binding("enter", "load_profile", "Load", show=True),
    ]

    CSS = """
    ProfileSelectScreen {
        align: center middle;
    }

    #profile-container {
        width: 80;
        height: auto;
        max-height: 90vh;
        border: solid $primary;
        padding: 1 2;
    }

    #title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }

    #profiles-table {
        height: 20;
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

    #error-message {
        color: $error;
        text-align: center;
        margin-top: 1;
        height: auto;
    }

    #info-message {
        color: $accent;
        text-align: center;
        margin-top: 1;
        height: auto;
    }
    """

    def __init__(self):
        super().__init__()
        self.profile_manager = ProfileManager()
        self.selected_profile_name = None

    def compose(self) -> ComposeResult:
        """
        Create the UI components.
        """
        with Container(id="profile-container"):
            yield Label("Configuration Profiles", id="title")
            yield Label("Select a profile or create a new one", id="subtitle")

            # Table to display profiles
            table = DataTable(id="profiles-table")
            table.cursor_type = "row"
            table.zebra_stripes = True
            yield table

            with Horizontal(id="button-container"):
                yield Button("Load", variant="primary", id="load-button")
                yield Button("New", variant="success", id="new-button")
                yield Button("Import", variant="default", id="import-button")
                yield Button("Delete", variant="error", id="delete-button")

            yield Static("", id="error-message")
            yield Static("", id="info-message")

    def on_mount(self) -> None:
        """
        Load profiles when screen is mounted.
        """
        self._load_profiles()

        # Set focus to the Load button so pressing Enter will load the profile
        load_button = self.query_one("#load-button", Button)
        load_button.focus()

    def _load_profiles(self) -> None:
        """
        Load and display profiles in the table.
        """
        table = self.query_one("#profiles-table", DataTable)
        table.clear(columns=True)

        # Add columns
        table.add_columns("Name", "Description", "Last Used")

        # Load profiles
        profiles = self.profile_manager.list_profiles()

        if not profiles:
            error_display = self.query_one("#info-message", Static)
            error_display.update("No profiles found. Create a new profile to get started.")
            return

        # Verify config files exist and remove profiles with missing files
        valid_profiles = []
        deleted_profiles = []

        for profile in profiles:
            config_path = Path(profile.path).expanduser()
            if config_path.exists():
                valid_profiles.append(profile)
            else:
                # Delete profile with missing config file
                try:
                    self.profile_manager.delete_profile(profile.name, delete_file=False)
                    deleted_profiles.append(profile.name)
                except Exception:
                    # If deletion fails, still skip adding it to the table
                    pass

        # Show info if any profiles were deleted
        if deleted_profiles:
            info_display = self.query_one("#info-message", Static)
            deleted_names = ", ".join(deleted_profiles)
            info_display.update(f"Removed profiles with missing config files: {deleted_names}")

        # Check if we have any valid profiles left
        if not valid_profiles:
            error_display = self.query_one("#info-message", Static)
            error_display.update("No valid profiles found. Create a new profile to get started.")
            return

        # Sort by last used (most recent first)
        valid_profiles.sort(key=lambda p: p.last_used, reverse=True)

        # Add rows
        for profile in valid_profiles:
            # Format last used timestamp
            try:
                dt = datetime.fromisoformat(profile.last_used)
                last_used_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                last_used_str = profile.last_used

            table.add_row(
                profile.name,
                profile.description[:40] if profile.description else "",
                last_used_str,
                key=profile.name
            )

        # Select the first row (most recently used profile)
        if table.row_count > 0:
            table.move_cursor(row=0)
            # The first profile in the sorted list is the most recently used
            self.selected_profile_name = valid_profiles[0].name
            info_display = self.query_one("#info-message", Static)

            # Only update if we didn't already show deletion message
            if not deleted_profiles:
                info_display.update(f"Selected: {self.selected_profile_name}")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        Handle row selection in the profiles table.
        """
        self.selected_profile_name = event.row_key.value

        # Clear messages
        self.query_one("#error-message", Static).update("")
        self.query_one("#info-message", Static).update(f"Selected: {self.selected_profile_name}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button presses.
        """
        if event.button.id == "load-button":
            self.action_load_profile()
        elif event.button.id == "new-button":
            self.action_new_profile()
        elif event.button.id == "import-button":
            self.action_import_profile()
        elif event.button.id == "delete-button":
            self.action_delete_profile()

    def action_load_profile(self) -> None:
        """
        Load the selected profile.
        """
        if not self.selected_profile_name:
            error_display = self.query_one("#error-message", Static)
            error_display.update("Please select a profile to load")
            return

        profile = self.profile_manager.get_profile(self.selected_profile_name)
        if not profile:
            error_display = self.query_one("#error-message", Static)
            error_display.update(f"Profile '{self.selected_profile_name}' not found")
            return

        # Check if config file exists
        config_path = Path(profile.path).expanduser()
        if not config_path.exists():
            error_display = self.query_one("#error-message", Static)
            error_display.update(f"Config file not found: {config_path}")
            return

        # Store profile info and switch to config load screen
        self.app.current_profile = profile
        self.app.push_screen("config_load")

    def action_new_profile(self) -> None:
        """
        Create a new profile.
        """
        # Switch to new profile dialog
        self.app.push_screen(NewProfileDialog(self.profile_manager, self._on_profile_created))

    def action_import_profile(self) -> None:
        """
        Import an existing config file as a new profile.
        """
        self.app.push_screen(ImportProfileDialog(self.profile_manager, self._on_profile_imported))

    def action_delete_profile(self) -> None:
        """
        Delete the selected profile.
        """
        if not self.selected_profile_name:
            error_display = self.query_one("#error-message", Static)
            error_display.update("Please select a profile to delete")
            return

        # Confirm deletion
        def handle_response(confirmed: bool, delete_file: bool) -> None:
            if confirmed:
                try:
                    self.profile_manager.delete_profile(self.selected_profile_name, delete_file)
                    self.selected_profile_name = None
                    self._load_profiles()
                    info_display = self.query_one("#info-message", Static)
                    info_display.update("Profile deleted successfully")
                except Exception as e:
                    error_display = self.query_one("#error-message", Static)
                    error_display.update(f"Failed to delete profile: {e}")

        self.app.push_screen(
            DeleteConfirmDialog(
                f"Delete profile '{self.selected_profile_name}'?",
                handle_response
            )
        )

    def _on_profile_created(self, profile: Profile) -> None:
        """
        Callback when a new profile is created.
        """
        self._load_profiles()
        info_display = self.query_one("#info-message", Static)
        info_display.update(f"Profile '{profile.name}' created")

        # Store profile and proceed to config creation
        self.app.current_profile = profile
        self.app.push_screen("config_create")

    def _on_profile_imported(self, profile: Profile) -> None:
        """
        Callback when a profile is imported.
        """
        self._load_profiles()
        info_display = self.query_one("#info-message", Static)
        info_display.update(f"Profile '{profile.name}' imported")

    def action_quit(self) -> None:
        """
        Exit the application.
        """
        self.app.exit()


class NewProfileDialog(Screen):
    """
    Dialog for creating a new profile.
    """

    CSS = """
    NewProfileDialog {
        align: center middle;
    }

    #dialog-container {
        width: 60;
        height: auto;
        border: solid $primary;
        padding: 1 2;
        background: $surface;
    }

    #dialog-title {
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

    #button-container {
        layout: horizontal;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }

    #error-message {
        color: $error;
        text-align: center;
        margin-top: 1;
        height: auto;
    }
    """

    def __init__(self, profile_manager: ProfileManager, callback):
        super().__init__()
        self.profile_manager = profile_manager
        self.callback = callback

    def compose(self) -> ComposeResult:
        """
        Create dialog UI.
        """
        with Container(id="dialog-container"):
            yield Label("New Profile", id="dialog-title")
            yield Label("Profile Name:", classes="input-label")
            yield Input(
                placeholder="e.g., production, staging",
                id="profile-name"
            )
            yield Label("Description (optional):", classes="input-label")
            yield Input(
                placeholder="Brief description of this profile",
                id="profile-description"
            )
            with Horizontal(id="button-container"):
                yield Button("Create", variant="primary", id="create-button")
                yield Button("Cancel", variant="default", id="cancel-button")
            yield Static("", id="error-message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button press.
        """
        if event.button.id == "create-button":
            self._create_profile()
        elif event.button.id == "cancel-button":
            self.app.pop_screen()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Handle Enter key in input fields.
        """
        self._create_profile()

    def _create_profile(self) -> None:
        """
        Create the new profile.
        """
        name_input = self.query_one("#profile-name", Input)
        description_input = self.query_one("#profile-description", Input)
        error_display = self.query_one("#error-message", Static)

        name = name_input.value.strip()
        description = description_input.value.strip()

        if not name:
            error_display.update("Profile name is required")
            return

        if self.profile_manager.profile_exists(name):
            error_display.update(f"Profile '{name}' already exists")
            return

        # Create profile with generated path
        config_path = self.profile_manager.get_config_path(name)
        profile = Profile(name, description, str(config_path))

        try:
            self.profile_manager.add_profile(profile)
            self.app.pop_screen()
            self.callback(profile)
        except Exception as e:
            error_display.update(f"Failed to create profile: {e}")


class ImportProfileDialog(Screen):
    """
    Dialog for importing an existing config file.
    """

    CSS = """
    ImportProfileDialog {
        align: center middle;
    }

    #dialog-container {
        width: 70;
        height: auto;
        border: solid $primary;
        padding: 1 2;
        background: $surface;
    }

    #dialog-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    .input-label {
        margin-top: 1;
        margin-bottom: 0;
    }

    Input, PathInput {
        margin-bottom: 1;
    }

    #button-container {
        layout: horizontal;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }

    #error-message {
        color: $error;
        text-align: center;
        margin-top: 1;
        height: auto;
    }
    """

    def __init__(self, profile_manager: ProfileManager, callback):
        super().__init__()
        self.profile_manager = profile_manager
        self.callback = callback

    def compose(self) -> ComposeResult:
        """
        Create dialog UI.
        """
        # Get the default config directory
        default_config_dir = str(self.profile_manager.profiles_file.parent / "configs")

        with Container(id="dialog-container"):
            yield Label("Import Profile", id="dialog-title")
            yield Label("Profile Name:", classes="input-label")
            yield Input(
                placeholder="Name for this profile",
                id="profile-name",
                select_on_focus=False
            )
            yield Label("Description (optional):", classes="input-label")
            yield Input(
                placeholder="Brief description",
                id="profile-description",
                select_on_focus=False
            )
            yield Label("Config File Path (Tab to autocomplete):", classes="input-label")
            yield PathInput(
                placeholder="Path to existing .enc file",
                id="config-path",
                default_dir=default_config_dir
            )
            with Horizontal(id="button-container"):
                yield Button("Import", variant="primary", id="import-button")
                yield Button("Cancel", variant="default", id="cancel-button")
            yield Static("", id="error-message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button press.
        """
        if event.button.id == "import-button":
            self._import_profile()
        elif event.button.id == "cancel-button":
            self.app.pop_screen()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Handle Enter key in input fields.
        """
        self._import_profile()

    def _import_profile(self) -> None:
        """
        Import the profile.
        """
        name_input = self.query_one("#profile-name", Input)
        description_input = self.query_one("#profile-description", Input)
        path_input = self.query_one("#config-path", Input)
        error_display = self.query_one("#error-message", Static)

        name = name_input.value.strip()
        description = description_input.value.strip()
        config_path = path_input.value.strip()

        if not name:
            error_display.update("Profile name is required")
            return

        if not config_path:
            error_display.update("Config file path is required")
            return

        # Check if file exists
        path = Path(config_path).expanduser()
        if not path.exists():
            error_display.update(f"File not found: {config_path}")
            return

        if self.profile_manager.profile_exists(name):
            error_display.update(f"Profile '{name}' already exists")
            return

        # Create profile with the provided path
        profile = Profile(name, description, str(path))

        try:
            self.profile_manager.add_profile(profile)
            self.app.pop_screen()
            self.callback(profile)
        except Exception as e:
            error_display.update(f"Failed to import profile: {e}")


class DeleteConfirmDialog(Screen):
    """
    Confirmation dialog for deleting a profile.
    """

    CSS = """
    DeleteConfirmDialog {
        align: center middle;
    }

    #dialog-container {
        width: 60;
        height: auto;
        border: solid $error;
        padding: 1 2;
        background: $surface;
    }

    #dialog-message {
        text-align: center;
        margin-bottom: 1;
    }

    #checkbox-container {
        layout: horizontal;
        height: auto;
        align: center middle;
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
        self.delete_file = False

    def compose(self) -> ComposeResult:
        """
        Create dialog UI.
        """
        with Container(id="dialog-container"):
            yield Static(self.message, id="dialog-message")
            with Horizontal(id="checkbox-container"):
                yield Button(
                    "☐ Also delete config file",
                    variant="default",
                    id="toggle-delete-file"
                )
            with Horizontal(id="button-container"):
                yield Button("Delete", variant="error", id="yes-button")
                yield Button("Cancel", variant="default", id="no-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button press.
        """
        if event.button.id == "toggle-delete-file":
            self.delete_file = not self.delete_file
            button = event.button
            button.label = "☑ Also delete config file" if self.delete_file else "☐ Also delete config file"
        elif event.button.id == "yes-button":
            self.app.pop_screen()
            self.callback(True, self.delete_file)
        elif event.button.id == "no-button":
            self.app.pop_screen()
            self.callback(False, False)