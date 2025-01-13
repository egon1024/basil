from textual.app import App, ComposeResult
from textual.widget import Widget
from textual.widgets import Button, Collapsible, Static, Label
from textual.containers import Vertical, Horizontal


class Sidebar(Widget):

    def compose(self) -> ComposeResult:
        with Collapsible(title="Menu", collapsed=False):
            yield Vertical(
                Button("Servers", name="servers"),
                Button("Entities", name="entities"),
                Button("Events", name="events"),
                Button("Silences", name="silences"),
                Button("Checks", name="checks"),
            )

class MainView(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.content = Static("Select an item from the sidebar")

    async def on_button_pressed(self, message):
        if message.sender.name == "servers":
            self.content.update("Servers View")
        elif message.sender.name == "entities":
            self.content.update("Entities View")
        elif message.sender.name == "events":
            self.content.update("Events View")
        elif message.sender.name == "silences":
            self.content.update("Silences View")
        elif message.sender.name == "checks":
            self.content.update("Checks View")

    def compose(self) -> ComposeResult:
        yield self.content

class MyApp(App):
    def compose(self) -> ComposeResult:
        sidebar = Sidebar()
        sidebar.styles.width = 18
        main_view = MainView()
        layout = Horizontal(sidebar, main_view)

        yield layout
        #yield sidebar
        #yield main_view

if __name__ == "__main__":
    app = MyApp()
    app.run()