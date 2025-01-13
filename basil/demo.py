#!/usr/bin/env python3

"""
Main module for the basil package.
"""

# Built in imports
import getpass

# 3rd party imports
from fawlty.sensu_client import SensuClient
import fawlty.resources 
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Label
from textual.containers import HorizontalGroup, VerticalScroll

# Our imports
from basil.server_config import ServerConfig

def main():
    """
    Main function for the basil package.
    """
    #config = ServerConfig(config_file='/home/egon/.config/basil/servers.yaml')

    #client = SensuClient(server=config.servers[0].server)
    #client.login(config.servers[0].username, config.servers[0].password)
    #print(entity.Entity.get(client, namespace="default"))

    #events = client.resource_get(
    #    cls=fawlty.resources.event.Event,
    #    get_url=fawlty.resources.event.Event.get_url(namespace="default")
    #)

    app = EntityApp()
    app.run()


class EntityApp(App):
    def compose(self) -> ComposeResult:
        config = ServerConfig(config_file='/home/egon/.config/basil/servers.yaml')

        client = SensuClient(server=config.servers[0].server)
        client.login(config.servers[0].username, config.servers[0].password)
        widgets = []
        events = client.resource_get(
            cls=fawlty.resources.event.Event,
            get_url=fawlty.resources.event.Event.get_url(namespace="default")
        )
        for e in events:
            er = EventWidget(event=e)
            widgets.append(er)

        yield Header()
        yield Footer()
        yield VerticalScroll(*widgets)
    

class EventWidget(HorizontalGroup):

    def __init__(self, event: fawlty.resources.event.Event) -> None:
        super().__init__()
        self.event = event
        if self.event.check.state == "passing":
            self.styles.background = "green"
            self.one = Label(" * ", id="one")
        else:
            self.styles.background = "red"
            self.one = Label("XXX", id="one")

        self.two = Label(f"{self.event.entity.metadata.name}/{self.event.check.metadata.name}: ", id="two")
        self.three = Label(f"{self.event.check.state}", id="three")


    def compose(self) -> ComposeResult:
        yield self.one
        yield self.two
        yield self.three

if __name__ == '__main__':
    main()