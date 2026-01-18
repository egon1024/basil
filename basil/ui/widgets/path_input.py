"""
Custom path input widget with autocomplete support.
"""
# built-in imports
from pathlib import Path
from typing import Optional, List

# third party imports
from textual.widgets import Input
from textual.events import Key


class PathInput(Input):
    """
    Input widget with file path autocomplete functionality.
    """

    def __init__(
        self,
        *args,
        default_dir: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize PathInput.

        Args:
            default_dir: Default directory path to use as starting value
            *args: Additional positional arguments for Input
            **kwargs: Additional keyword arguments for Input
        """
        # Disable select_on_focus by default for better UX
        kwargs.setdefault('select_on_focus', False)

        super().__init__(*args, **kwargs)

        self.default_dir = default_dir

    def on_mount(self) -> None:
        """
        Set default directory value when mounted.
        """
        if self.default_dir and not self.value:
            self.value = str(Path(self.default_dir).expanduser())

    def _get_path_completions(self, current_path: str) -> List[str]:
        """
        Get list of path completions for the current input.

        Args:
            current_path: The current path string to complete

        Returns:
            List of matching file/directory paths
        """
        if not current_path:
            return []

        try:
            # Expand user home directory
            path = Path(current_path).expanduser()

            # If path ends with separator, list directory contents
            if current_path.endswith('/') or current_path.endswith('\\'):
                if path.is_dir():
                    items = sorted(path.iterdir())
                    return [str(item) for item in items]
                return []

            # Otherwise, get parent directory and filter by prefix
            parent = path.parent
            prefix = path.name

            if not parent.exists() or not parent.is_dir():
                return []

            # Get all items in parent directory
            items = sorted(parent.iterdir())

            # Filter by prefix (case-insensitive)
            matches = [
                str(item)
                for item in items
                if item.name.lower().startswith(prefix.lower())
            ]

            return matches

        except (OSError, PermissionError):
            return []

    def _apply_completion(self) -> bool:
        """
        Apply the first available completion to the input.

        Returns:
            True if completion was applied, False otherwise
        """
        current_value = self.value
        completions = self._get_path_completions(current_value)

        if not completions:
            return False

        # Use the first match
        completed_path = completions[0]

        # If it's a directory, add trailing separator
        path_obj = Path(completed_path).expanduser()
        if path_obj.is_dir():
            completed_path = str(path_obj) + '/'

        self.value = completed_path
        # Move cursor to end
        self.cursor_position = len(self.value)

        return True

    def on_key(self, event: Key) -> None:
        """
        Handle key events for autocomplete.

        Args:
            event: The key event
        """
        # Handle Tab key for completion
        if event.key == "tab":
            # Try to apply completion
            if self._apply_completion():
                # Stop the event from propagating (prevents focus change)
                event.prevent_default()
                event.stop()
        # For all other cases, let the event propagate normally
