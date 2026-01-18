"""
Reusable widgets for the Basil UI.
"""
# Base classes
from .base_resource_list import BaseResourceListWidget
from .base_resource_detail import BaseResourceDetailWidget

# Resource-specific widgets
from .events import EventListWidget, EventDetailWidget
from .entities import EntityListWidget, EntityDetailWidget
from .silences import SilenceListWidget, SilenceDetailWidget
from .checks import CheckListWidget, CheckDetailWidget


# Other widgets
from .server_config import ServerConfigWidget
from .path_input import PathInput

__all__ = [
    # Base classes
    'BaseResourceListWidget',
    'BaseResourceDetailWidget',
    # Event widgets
    'EventListWidget',
    'EventDetailWidget',
    # Entity widgets
    'EntityListWidget',
    'EntityDetailWidget',
    # Silence widgets
    'SilenceListWidget',
    'SilenceDetailWidget',
    # Check widgets
    'CheckListWidget',
    'CheckDetailWidget',
    # Other widgets
    'ServerConfigWidget',
    'PathInput',
]
