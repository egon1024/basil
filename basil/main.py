"""
Main application
"""

# Built in imports

# 3rd party imports
from textual.widgets import Button, Collapsible, Static, Label
from textual.containers import Vertical, Horizontal
from textual.app import App, ComposeResult
from textual.widget import Widget
from textual.message import Message

# Our imports
import basil.views

class Sidebar(Widget):

    def compose(self) -> ComposeResult:
        with Collapsible(title="", collapsed=False):
            yield Vertical(
                Button("Servers", name="servers"),
                Button("Entities", name="entities"),
                Button("Events", name="events"),
                Button("Silences", name="silences"),
                Button("Checks", name="checks"),
                classes="centered"
            )

class MainView(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.default_view = Static("Select an item from the sidebar")
        self.servers_view = basil.views.servers.ServersView()
        self.entities_view = basil.views.entities.EntitiesView()
        self.events_view = basil.views.events.EventsView()
        self.silences_view = basil.views.silences.SilencesView()
        self.checks_view = basil.views.checks.ChecksView()
        self.content = self.default_view

    async def on_button_pressed(self, message: Message) -> None:
        if message.button.name == "servers":
            self.update_content(self.servers_view)
        elif message.button.name == "entities":
            self.update_content(self.entities_view)
        elif message.button.name == "events":
            self.update_content(self.events_view)
        elif message.button.name == "silences":
            self.update_content(self.silences_view)
        elif message.button.name == "checks":
            self.update_content(self.checks_view)

    def update_content(self, new_content: Widget) -> None:
        self.content.remove()
        self.content = new_content
        self.mount(self.content)

    def compose(self) -> ComposeResult:
        yield self.content

class MyApp(App):
    def compose(self) -> ComposeResult:
        sidebar = Sidebar()
        sidebar.styles.width = 18
        main_view = MainView()
        yield Horizontal(sidebar, main_view)

    async def on_button_pressed(self, message: Message) -> None:
        await self.query_one(MainView).on_button_pressed(message)

if __name__ == "__main__":
    MyApp().run()