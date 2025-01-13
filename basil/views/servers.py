"""
This module will contain the code for managing the servers view
"""

# Built in imports

# 3rd party imports
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

# Our imports

class ServersView(Widget):
    def compose(self) -> ComposeResult:
        yield Static("Servers View")