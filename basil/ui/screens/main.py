"""
Main application screen with tabbed interface.
"""
# Built-in imports

# 3rd party imports
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, TabbedContent, TabPane, DataTable
from textual.containers import Horizontal, Container
from textual.binding import Binding

# Basil imports
from basil.client import ConnectionManager
from basil.config_writer import save_encrypted_config
from basil.ui.widgets.base_resource_list import BaseResourceListWidget
from basil.ui.widgets.base_resource_detail import BaseResourceDetailWidget
from basil.ui.widgets.events import EventListWidget, EventDetailWidget
from basil.ui.widgets.entities import EntityListWidget, EntityDetailWidget
from basil.ui.widgets.silences import SilenceListWidget, SilenceDetailWidget
from basil.ui.widgets.checks import CheckListWidget, CheckDetailWidget
from basil.ui.widgets.connections import ConnectionListWidget, ConnectionDetailWidget


class CustomTabbedContent(TabbedContent):
    """TabbedContent that doesn't consume our custom key bindings."""

    def on_key(self, event) -> None:  # pylint: disable=useless-return
        """Override to not handle e, n, s, k, c, r keys - let them bubble to Screen."""
        if event.key in ('e', 'n', 's', 'k', 'c', 'r'):
            # Don't handle these keys, let them bubble up to the Screen
            return
        # For all other keys, don't stop them - they will propagate naturally


class MainScreen(Screen):
    """
    Main screen with tabbed interface for viewing Sensu resources.
    """

    # Track the current split ratio (0-100, represents percentage for left panel)
    split_ratio = 60  # Default: 60% left, 40% right
    detail_visible: bool = False

    BINDINGS = [
        Binding("e", "switch_tab('events')", "Events", show=True, priority=True),
        Binding("n", "switch_tab('entities')", "Entities", show=True, priority=True),
        Binding("s", "switch_tab('silences')", "Silences", show=True, priority=True),
        Binding("k", "switch_tab('checks')", "Checks", show=True, priority=True),
        Binding("c", "switch_tab('connections')", "Connections", show=True, priority=True),
        Binding("r", "refresh_data", "Refresh", show=True, priority=True),
        Binding("[", "resize_panels('shrink')", "Shrink Left", show=False, priority=True),
        Binding("]", "resize_panels('grow')", "Grow Left", show=False, priority=True),
        Binding("escape", "hide_detail", "Close Detail", show=False, priority=True),
    ]

    CSS = """
    Horizontal.split-view {
        height: 1fr;
    }

    .list-pane {
        width: 100%;
        border-right: solid $primary;
    }

    .detail-pane {
        width: 40%;
        height: 100%;
    }

    .hidden {
        display: none;
    }
    """

    def compose(self) -> ComposeResult:
        """
        Create the main UI layout.
        """
        yield Header()

        with CustomTabbedContent(initial="events"):
            with TabPane("Events", id="events"):
                with Horizontal(classes="split-view"):
                    with Container(classes="list-pane"):
                        yield EventListWidget(id="events-list")
                    with Container(classes="detail-pane"):
                        yield EventDetailWidget(id="events-detail")

            with TabPane("Entities", id="entities"):
                with Horizontal(classes="split-view"):
                    with Container(classes="list-pane"):
                        yield EntityListWidget(id="entities-list")
                    with Container(classes="detail-pane"):
                        yield EntityDetailWidget(id="entities-detail")

            with TabPane("Silences", id="silences"):
                with Horizontal(classes="split-view"):
                    with Container(classes="list-pane"):
                        yield SilenceListWidget(id="silences-list")
                    with Container(classes="detail-pane"):
                        yield SilenceDetailWidget(id="silences-detail")

            with TabPane("Checks", id="checks"):
                with Horizontal(classes="split-view"):
                    with Container(classes="list-pane"):
                        yield CheckListWidget(id="checks-list")
                    with Container(classes="detail-pane"):
                        yield CheckDetailWidget(id="checks-detail")

            with TabPane("Connections", id="connections"):
                with Horizontal(classes="split-view"):
                    with Container(classes="list-pane"):
                        yield ConnectionListWidget(id="connections-list")
                    with Container(classes="detail-pane"):
                        yield ConnectionDetailWidget(id="connections-detail")

        yield Footer()

    def on_mount(self) -> None:
        """
        Load initial data when screen is mounted.
        """
        self.update_panel_visibility(False)
        self.load_all_data()
        self.load_connections()
        self._focus_current_list()

    def update_panel_visibility(self, visible: bool) -> None:
        """
        Update the visibility of the detail pane.

        Args:
            visible: Whether the detail pane should be visible
        """
        self.detail_visible = visible
        list_panes = self.query(".list-pane")
        detail_panes = self.query(".detail-pane")

        if visible:
            list_width = f"{self.split_ratio}%"
            detail_width = f"{100 - self.split_ratio}%"

            for pane in list_panes:
                pane.styles.width = list_width
                pane.styles.border_right = ("solid", self.app.current_theme.primary)

            for pane in detail_panes:
                pane.remove_class("hidden")
                pane.styles.display = "block"
                pane.styles.width = detail_width
        else:
            for pane in list_panes:
                pane.styles.width = "100%"
                pane.styles.border_right = None

            for pane in detail_panes:
                pane.add_class("hidden")
                pane.styles.display = "none"

    def load_all_data(self) -> None:
        """
        Load data for all resource types.
        """
        connection_manager = self.app.connection_manager

        if not connection_manager:
            return

        try:
            # Load events first (needed for entity check counts and detail view)
            events_list = self.query_one("#events-list", EventListWidget)
            events_list.load_resources_parallel(connection_manager, "events")

            # Load entities
            entities_list = self.query_one("#entities-list", EntityListWidget)
            entities_list.load_resources_parallel(connection_manager, "entities")

            # Load silences
            silences_list = self.query_one("#silences-list", SilenceListWidget)
            silences_list.load_resources_parallel(connection_manager, "silenced")

            # Load checks
            checks_list = self.query_one("#checks-list", CheckListWidget)
            checks_list.load_resources_parallel(connection_manager, "checks")

        except Exception as e:
            self.notify(f"Error loading data: {e}", severity="error")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        Handle row selection in any resource list.
        """
        # Find which list triggered this
        list_widget = event.data_table

        if not isinstance(list_widget, BaseResourceListWidget):
            return

        # Get the selected resource
        resource = list_widget.get_selected_resource()

        if not resource:
            return

        # Find the corresponding detail widget using ID convention
        # "events-list" -> "events-detail"
        list_id = list_widget.id
        if list_id and list_id.endswith("-list"):
            detail_id = list_id.replace("-list", "-detail")

            try:
                detail_widget = self.query_one(f"#{detail_id}", BaseResourceDetailWidget)
                detail_widget.show_resource(resource)
                self.update_panel_visibility(True)
            except Exception:
                # Tab doesn't have a detail widget
                pass

    def action_switch_tab(self, tab_id: str) -> None:
        """
        Switch to a specific tab.
        """
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = tab_id
        self._focus_current_list(tab_id)

    def action_refresh_data(self) -> None:
        """
        Refresh all data from connections.
        """
        # Clear all detail panels before refreshing
        detail_widgets = self.query(BaseResourceDetailWidget)
        for detail_widget in detail_widgets:
            detail_widget.clear()

        self.load_all_data()
        self.notify("Data refreshed")

    def action_resize_panels(self, direction: str) -> None:
        """
        Resize the split panels.

        Args:
            direction: Either 'grow' to increase left panel or 'shrink' to decrease it
        """
        # Adjust ratio by 5% increments
        if direction == 'grow':
            self.split_ratio = min(90, self.split_ratio + 5)
        elif direction == 'shrink':
            self.split_ratio = max(10, self.split_ratio - 5)

        # Update styles for all list and detail panes
        if self.detail_visible:
            list_panes = self.query(".list-pane")
            detail_panes = self.query(".detail-pane")

            for pane in list_panes:
                pane.styles.width = f"{self.split_ratio}%"

            for pane in detail_panes:
                pane.styles.width = f"{100 - self.split_ratio}%"

        self.notify(f"Panel ratio: {self.split_ratio}% / {100 - self.split_ratio}%")

    def load_connections(self) -> None:
        """Load connections from the current config into the connections list."""
        if not hasattr(self.app, 'config') or not self.app.config:
            return

        connections = self.app.config.get("connections", [])
        connections_list = self.query_one("#connections-list", ConnectionListWidget)
        connections_list.load_connections(connections)

    def on_connection_list_widget_connection_selected(
        self, event: ConnectionListWidget.ConnectionSelected
    ) -> None:
        """
        Handle connection selection in the list.

        Args:
            event: The connection selection event
        """
        connections_detail = self.query_one("#connections-detail", ConnectionDetailWidget)
        connections_detail.show_connection(event.connection)
        self.update_panel_visibility(True)

    def on_connection_detail_widget_connection_saved(
        self, event: ConnectionDetailWidget.ConnectionSaved
    ) -> None:
        """
        Handle connection save event.

        Args:
            event: The connection saved event
        """
        if not hasattr(self.app, 'config') or not self.app.config:
            self.notify("Configuration not loaded", severity="error")
            return

        connections = self.app.config.get("connections", [])

        if event.is_new:
            # Add new connection
            # Check for duplicate names
            if any(c.get("name") == event.connection.get("name") for c in connections):
                self.notify(
                    f"Connection '{event.connection.get('name')}' already exists",
                    severity="error"
                )
                return

            connections.append(event.connection)
            self.notify(
                f"Connection '{event.connection.get('name')}' created successfully",
                severity="information"
            )
        else:
            # Update existing connection
            for i, conn in enumerate(connections):
                if conn.get("name") == event.connection.get("name"):
                    connections[i] = event.connection
                    break

            self.notify(
                f"Connection '{event.connection.get('name')}' updated successfully",
                severity="information"
            )

        # Save updated config
        self._save_config()

        # Reload connection manager with updated config
        self._reload_connection_manager()

        # Reload connections list and clear detail
        self.load_connections()
        connections_detail = self.query_one("#connections-detail", ConnectionDetailWidget)
        connections_detail.clear()

    def on_connection_detail_widget_connection_deleted(
        self, event: ConnectionDetailWidget.ConnectionDeleted
    ) -> None:
        """
        Handle connection delete event.

        Args:
            event: The connection deleted event
        """
        if not hasattr(self.app, 'config') or not self.app.config:
            self.notify("Configuration not loaded", severity="error")
            return

        connections = self.app.config.get("connections", [])

        # Remove the connection
        original_count = len(connections)
        connections[:] = [c for c in connections if c.get("name") != event.connection_name]

        if len(connections) < original_count:
            self.notify(
                f"Connection '{event.connection_name}' deleted successfully",
                severity="information"
            )

            # Save updated config
            self._save_config()

            # Reload connection manager with updated config
            self._reload_connection_manager()

            # Reload connections list and clear detail
            self.load_connections()
            connections_detail = self.query_one("#connections-detail", ConnectionDetailWidget)
            connections_detail.clear()
        else:
            self.notify(f"Connection '{event.connection_name}' not found", severity="warning")

    def _save_config(self) -> None:
        """Save the current configuration to disk."""

        if not hasattr(self.app, 'config') or not self.app.config:
            self.notify("Configuration not loaded", severity="error")
            return

        if not hasattr(self.app, 'config_password') or not self.app.config_password:
            self.notify("Configuration password not available", severity="error")
            return

        if not hasattr(self.app, 'config_path') or not self.app.config_path:
            self.notify("Configuration path not available", severity="error")
            return

        try:
            save_encrypted_config(
                self.app.config,
                self.app.config_password,
                self.app.config_path
            )
        except Exception as e:
            self.notify(f"Error saving configuration: {e}", severity="error")

    def _reload_connection_manager(self) -> None:
        """Reload the connection manager with the current configuration."""

        if not hasattr(self.app, 'config') or not self.app.config:
            return

        try:
            # Create a new connection manager with the updated config
            # pylint: disable=attribute-defined-outside-init
            self.app.connection_manager = ConnectionManager(self.app.config)
        except Exception as e:
            self.notify(f"Error reloading connections: {e}", severity="error")

    def on_base_resource_detail_widget_close(self, event: BaseResourceDetailWidget.Close) -> None:  # pylint: disable=unused-argument
        """Handle close message from detail widget."""
        self.update_panel_visibility(False)
        self._focus_current_list()

    def action_hide_detail(self) -> None:
        """Hide the detail pane."""
        if self.detail_visible:
            self.update_panel_visibility(False)
            self._focus_current_list()

    def _focus_current_list(self, tab_id: str = None) -> None:
        """
        Focus the list widget in the current or specified tab.

        Args:
            tab_id: Optional tab ID. If None, uses the currently active tab.
        """
        if tab_id is None:
            tabbed_content = self.query_one(TabbedContent)
            tab_id = tabbed_content.active

        list_id = f"{tab_id}-list"
        try:
            list_widget = self.query_one(f"#{list_id}", BaseResourceListWidget)
            list_widget.focus()
        except Exception:
            pass
