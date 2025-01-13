"""
This module will contain the code for managing the checks view
"""

# Built in imports

# 3rd party imports
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

# Our imports

class ChecksView(Widget):
    def compose(self) -> ComposeResult:
        yield Static("Checks View")