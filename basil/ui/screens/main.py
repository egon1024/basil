from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, TabbedContent, TabPane, Static, DataTable
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.message import Message
from basil.ui.widgets.resource_list import ResourceListWidget
from basil.ui.widgets.resource_detail import ResourceDetailWidget


class CustomTabbedContent(TabbedContent):
    """TabbedContent that doesn't consume our custom key bindings."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Disable automatic tab switching when focus changes
        self.can_focus_children = False
    
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
    
    BINDINGS = [
        Binding("e", "switch_tab('events')", "Events", show=True, priority=True),
        Binding("n", "switch_tab('entities')", "Entities", show=True, priority=True),
        Binding("s", "switch_tab('silences')", "Silences", show=True, priority=True),
        Binding("c", "switch_tab('connections')", "Connections", show=True, priority=True),
        Binding("r", "refresh_data", "Refresh", show=True, priority=True),
    ]
    
    CSS = """
    Horizontal.split-view {
        height: 1fr;
    }
    
    .list-pane {
        width: 3fr;
    }
    
    .detail-pane {
        width: 2fr;
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
                    yield ResourceListWidget("events", id="events-list", classes="list-pane")
                    yield ResourceDetailWidget(id="events-detail", classes="detail-pane")
            
            with TabPane("Entities", id="entities"):
                with Horizontal(classes="split-view"):
                    yield ResourceListWidget("entities", id="entities-list", classes="list-pane")
                    yield ResourceDetailWidget(id="entities-detail", classes="detail-pane")
            
            with TabPane("Silences", id="silences"):
                with Horizontal(classes="split-view"):
                    yield ResourceListWidget("silences", id="silences-list", classes="list-pane")
                    yield ResourceDetailWidget(id="silences-detail", classes="detail-pane")
            
            with TabPane("Checks", id="checks"):
                with Horizontal(classes="split-view"):
                    yield ResourceListWidget("checks", id="checks-list", classes="list-pane")
                    yield ResourceDetailWidget(id="checks-detail", classes="detail-pane")
            
            with TabPane("Connections", id="connections"):
                yield Static("Connections view - showing active connections", id="connections-content")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """
        Load initial data when screen is mounted.
        """
        self.load_all_data()
    
    def load_all_data(self) -> None:
        """
        Load data for all resource types.
        """
        connection_manager = self.app.connection_manager
        
        if not connection_manager:
            return
        
        # Load events
        events_list = self.query_one("#events-list", ResourceListWidget)
        events = connection_manager.get_all("events")
        events_list.load_resources(events)
        
        # Load entities
        entities_list = self.query_one("#entities-list", ResourceListWidget)
        entities = connection_manager.get_all("entities")
        entities_list.load_resources(entities)
        
        # Load silences
        silences_list = self.query_one("#silences-list", ResourceListWidget)
        silences = connection_manager.get_all("silenced")
        silences_list.load_resources(silences)
        
        # Load checks
        checks_list = self.query_one("#checks-list", ResourceListWidget)
        checks = connection_manager.get_all("checks")
        checks_list.load_resources(checks)
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        Handle row selection in any resource list.
        """
        # Find which list triggered this
        list_widget = event.data_table
        
        if not isinstance(list_widget, ResourceListWidget):
            return
        
        # Get the selected resource
        resource = list_widget.get_selected_resource()
        
        if not resource:
            return
        
        # Find the corresponding detail widget
        resource_type = list_widget.resource_type
        detail_id = f"{resource_type}-detail"
        
        try:
            detail_widget = self.query_one(f"#{detail_id}", ResourceDetailWidget)
            detail_widget.show_resource(resource)
        except Exception:
            # Connections tab doesn't have a detail widget
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
        self.load_all_data()
        self.notify("Data refreshed")
