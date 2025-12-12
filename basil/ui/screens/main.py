from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, TabbedContent, TabPane, Static, DataTable
from textual.containers import Horizontal, Vertical, Container
from textual.binding import Binding
from textual.message import Message
from basil.ui.widgets.base_resource_list import BaseResourceListWidget
from basil.ui.widgets.base_resource_detail import BaseResourceDetailWidget
from basil.ui.widgets.events import EventListWidget, EventDetailWidget
from basil.ui.widgets.entities import EntityListWidget, EntityDetailWidget
from basil.ui.widgets.silences import SilenceListWidget, SilenceDetailWidget
from basil.ui.widgets.checks import CheckListWidget, CheckDetailWidget
from basil.ui.widgets.connections import ConnectionListWidget, ConnectionDetailWidget


class CustomTabbedContent(TabbedContent):
    """TabbedContent that doesn't consume our custom key bindings."""

    def on_key(self, event) -> None:
        """Override to not handle e, n, s, c, r keys - let them bubble to Screen."""
        if event.key in ('e', 'n', 's', 'c', 'r'):
            # Don't handle these keys, let them bubble up to the Screen
            return
        # For all other keys, let default behavior handle it


class MainScreen(Screen):
    """
    Main screen with tabbed interface for viewing Sensu resources.
    """

    # Track the current split ratio (0-100, represents percentage for left panel)
    split_ratio = 60  # Default: 60% left, 40% right

    BINDINGS = [
        Binding("e", "switch_tab('events')", "Events", show=True, priority=True),
        Binding("n", "switch_tab('entities')", "Entities", show=True, priority=True),
        Binding("s", "switch_tab('silences')", "Silences", show=True, priority=True),
        Binding("c", "switch_tab('connections')", "Connections", show=True, priority=True),
        Binding("r", "refresh_data", "Refresh", show=True, priority=True),
        Binding("[", "resize_panels('shrink')", "Shrink Left", show=False, priority=True),
        Binding("]", "resize_panels('grow')", "Grow Left", show=False, priority=True),
    ]
    
    CSS = """
    Horizontal.split-view {
        height: 1fr;
    }

    .list-pane {
        width: 60%;
        border-right: solid $primary;
    }

    .detail-pane {
        width: 40%;
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
        self.load_all_data()
        self.load_connections()
    
    def load_all_data(self) -> None:
        """
        Load data for all resource types.
        """
        connection_manager = self.app.connection_manager

        if not connection_manager:
            return

        any_failures = False

        try:
            # Load events first (needed for entity check counts and detail view)
            events_list = self.query_one("#events-list", EventListWidget)
            events = connection_manager.get_all("events")
            if events is not None:  # Only update if fetch succeeded
                events_list.load_resources(events)
            else:
                any_failures = True

            # Load entities and pass events for check counts
            entities_list = self.query_one("#entities-list", EntityListWidget)
            entities = connection_manager.get_all("entities")
            if entities is not None:
                entities_list.load_resources(entities, events=events if events is not None else [])

                # Set events in entity detail widget for check grouping
                entities_detail = self.query_one("#entities-detail", EntityDetailWidget)
                entities_detail.set_events(events if events is not None else [])
            else:
                any_failures = True

            # Load silences
            silences_list = self.query_one("#silences-list", SilenceListWidget)
            silences = connection_manager.get_all("silenced")
            if silences is not None:
                silences_list.load_resources(silences)
            else:
                any_failures = True

            # Load checks
            checks_list = self.query_one("#checks-list", CheckListWidget)
            checks = connection_manager.get_all("checks")
            if checks is not None:
                checks_list.load_resources(checks)
            else:
                any_failures = True

            if any_failures:
                self.notify("Some resources failed to load", severity="warning")

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
            except Exception:
                # Tab doesn't have a detail widget
                pass
    

    
    def action_switch_tab(self, tab_id: str) -> None:
        """
        Switch to a specific tab.
        """
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = tab_id
    
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
                self.notify(f"Connection '{event.connection.get('name')}' already exists", severity="error")
                return

            connections.append(event.connection)
            self.notify(f"Connection '{event.connection.get('name')}' created successfully", severity="information")
        else:
            # Update existing connection
            for i, conn in enumerate(connections):
                if conn.get("name") == event.connection.get("name"):
                    connections[i] = event.connection
                    break

            self.notify(f"Connection '{event.connection.get('name')}' updated successfully", severity="information")

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
            self.notify(f"Connection '{event.connection_name}' deleted successfully", severity="information")

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
        from basil.config_writer import save_encrypted_config

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
        from basil.client import ConnectionManager

        if not hasattr(self.app, 'config') or not self.app.config:
            return

        try:
            # Create a new connection manager with the updated config
            self.app.connection_manager = ConnectionManager(self.app.config)
        except Exception as e:
            self.notify(f"Error reloading connections: {e}", severity="error")
