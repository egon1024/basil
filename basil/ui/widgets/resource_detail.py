from textual.app import ComposeResult
from textual.widgets import Static, Rule
from textual.containers import Vertical, ScrollableContainer
from basil.client import SensuResource
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict


class ResourceDetailWidget(ScrollableContainer):
    """
    Widget for displaying detailed information about a selected resource.
    """
    
    DEFAULT_CSS = """
    ResourceDetailWidget {
        border: solid $primary;
        padding: 1;
    }

    .detail-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .detail-section {
        margin-bottom: 1;
    }

    .section-header {
        text-style: bold;
        color: $secondary;
        margin-top: 1;
        margin-bottom: 1;
    }

    .field-label {
        color: $text-muted;
    }

    .status-ok {
        color: $success;
        text-style: bold;
    }

    .status-warning {
        color: $warning;
        text-style: bold;
    }

    .status-critical {
        color: $error;
        text-style: bold;
    }
    """
    
    def on_key(self, event) -> None:
        """Override to not consume e, n, s, c, r keys - let them bubble to Screen."""
        if event.key in ('e', 'n', 'c', 'r'):
            # Don't handle these keys, let them bubble up
            return
        # For 's' and other keys, use default ScrollableContainer behavior
        super().on_key(event)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_resource: SensuResource | None = None
    
    def compose(self) -> ComposeResult:
        """
        Create the detail view components.
        """
        yield Static("Select an item to view details", id="detail-content")
    
    def _format_timestamp(self, timestamp: int) -> str:
        """Format a Unix timestamp into a readable string."""
        if not timestamp:
            return "N/A"
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return str(timestamp)

    def _format_duration(self, duration: float) -> str:
        """Format duration in seconds to a readable string."""
        if duration is None:
            return "N/A"
        if duration < 1:
            return f"{duration*1000:.0f}ms"
        elif duration < 60:
            return f"{duration:.2f}s"
        else:
            mins = int(duration // 60)
            secs = duration % 60
            return f"{mins}m {secs:.0f}s"

    def _get_status_markup(self, status: int, state: str) -> str:
        """Get colored markup for status."""
        status_map = {
            0: ("OK", "status-ok"),
            1: ("WARNING", "status-warning"),
            2: ("CRITICAL", "status-critical"),
        }
        status_text, css_class = status_map.get(status, (f"UNKNOWN ({status})", "status-warning"))
        return f"[{css_class}]{status_text}[/{css_class}] ({state})"

    def _format_event(self, resource: SensuResource) -> str:
        """Format an Event resource for display."""
        data = resource.data
        lines = []

        # Header
        entity_name = getattr(data.entity, 'metadata', {}).name if hasattr(data, 'entity') and data.entity else "Unknown"
        check_name = getattr(data.check, 'metadata', {}).name if hasattr(data, 'check') and data.check else "Unknown"

        lines.append(f"[bold cyan]{entity_name} / {check_name}[/bold cyan]")
        lines.append(f"[dim]Connection: {resource.connection_name} | Namespace: {resource.connection.namespace}[/dim]")
        lines.append("")

        # Status Section
        if hasattr(data, 'check') and data.check:
            check = data.check
            lines.append("[bold]Status[/bold]")
            lines.append(f"  {self._get_status_markup(check.status, check.state)}")
            lines.append(f"  Occurrences: {check.occurrences} / Watermark: {check.occurrences_watermark}")
            if check.is_silenced:
                lines.append("  [yellow]SILENCED[/yellow]")
            lines.append("")

            # Timing Information
            lines.append("[bold]Timing[/bold]")
            lines.append(f"  Executed: {self._format_timestamp(check.executed)}")
            lines.append(f"  Last OK: {self._format_timestamp(check.last_ok)}")
            lines.append(f"  Duration: {self._format_duration(check.duration)}")
            if check.interval:
                lines.append(f"  Interval: {check.interval}s")
            if check.timeout:
                lines.append(f"  Timeout: {check.timeout}s")
            lines.append("")

            # Check Details
            lines.append("[bold]Check Configuration[/bold]")
            if check.command:
                lines.append(f"  Command: [cyan]{check.command}[/cyan]")
            if check.subscriptions:
                lines.append(f"  Subscriptions: {', '.join(check.subscriptions)}")
            if check.handlers:
                lines.append(f"  Handlers: {', '.join(check.handlers)}")
            if check.runtime_assets:
                lines.append(f"  Assets: {', '.join(check.runtime_assets)}")

            # Check Hooks Configuration
            if check.check_hooks:
                lines.append("  Check Hooks:")
                for hook_dict in check.check_hooks:
                    for hook_type, hook_list in hook_dict.items():
                        if hook_list:
                            lines.append(f"    {hook_type}: {', '.join(hook_list)}")

            lines.append("")

            # Hook Execution Results (if available in raw data)
            # Try multiple possible locations for hook results
            hooks_data = None

            # Check for hooks attribute on check object
            if hasattr(check, 'hooks') and check.hooks:
                hooks_data = check.hooks
            # Check in raw data dict (fawlty might store it differently)
            elif hasattr(data, 'hooks') and data.hooks:
                hooks_data = data.hooks
            # Try to access from check's model_extra or raw dict
            elif hasattr(check, '__dict__') and 'hooks' in check.__dict__:
                hooks_data = check.__dict__['hooks']

            if hooks_data:
                lines.append("[bold]Hook Execution Results[/bold]")

                # Handle both list and dict formats
                if isinstance(hooks_data, list):
                    for hook in hooks_data:
                        # Try different ways to access hook data
                        if hasattr(hook, 'metadata'):
                            hook_name = hook.metadata.name if hasattr(hook.metadata, 'name') else 'Unknown'
                        elif hasattr(hook, 'name'):
                            hook_name = hook.name
                        elif isinstance(hook, dict):
                            hook_name = hook.get('name', hook.get('metadata', {}).get('name', 'Unknown'))
                        else:
                            hook_name = 'Unknown'

                        hook_status = getattr(hook, 'status', hook.get('status', 'N/A') if isinstance(hook, dict) else 'N/A')
                        hook_output = getattr(hook, 'output', hook.get('output', '') if isinstance(hook, dict) else '')
                        hook_duration = getattr(hook, 'duration', hook.get('duration', None) if isinstance(hook, dict) else None)
                        hook_executed = getattr(hook, 'executed', hook.get('executed', None) if isinstance(hook, dict) else None)

                        status_color = "green" if hook_status == 0 else "red"
                        lines.append(f"  [{status_color}]{hook_name}[/{status_color}] (exit: {hook_status})")

                        if hook_executed:
                            lines.append(f"    Executed: {self._format_timestamp(hook_executed)}")
                        if hook_duration is not None:
                            lines.append(f"    Duration: {self._format_duration(hook_duration)}")

                        if hook_output:
                            output_lines = hook_output.strip().split('\n')
                            if len(output_lines) > 5:
                                lines.append(f"    [dim](Showing first 5 lines of {len(output_lines)})[/dim]")
                                for line in output_lines[:5]:
                                    lines.append(f"    {line}")
                                lines.append("    [dim]...[/dim]")
                            else:
                                for line in output_lines:
                                    lines.append(f"    {line}")
                        lines.append("")
                elif isinstance(hooks_data, dict):
                    # Handle dict format if hooks are keyed by name
                    for hook_name, hook_data in hooks_data.items():
                        hook_status = hook_data.get('status', 'N/A') if isinstance(hook_data, dict) else 'N/A'
                        hook_output = hook_data.get('output', '') if isinstance(hook_data, dict) else ''

                        status_color = "green" if hook_status == 0 else "red"
                        lines.append(f"  [{status_color}]{hook_name}[/{status_color}] (exit: {hook_status})")

                        if hook_output:
                            output_lines = hook_output.strip().split('\n')
                            if len(output_lines) > 5:
                                lines.append(f"    [dim](Showing first 5 lines of {len(output_lines)})[/dim]")
                                for line in output_lines[:5]:
                                    lines.append(f"    {line}")
                                lines.append("    [dim]...[/dim]")
                            else:
                                for line in output_lines:
                                    lines.append(f"    {line}")
                        lines.append("")

            # Output
            if check.output:
                lines.append("[bold]Output[/bold]")
                # Truncate long output and add scrolling hint
                output_lines = check.output.strip().split('\n')
                if len(output_lines) > 10:
                    lines.append(f"  [dim](Showing first 10 lines of {len(output_lines)})[/dim]")
                    for line in output_lines[:10]:
                        lines.append(f"  {line}")
                    lines.append("  [dim]...[/dim]")
                else:
                    for line in output_lines:
                        lines.append(f"  {line}")
                lines.append("")

            # History (last 5 states)
            if check.history and len(check.history) > 0:
                lines.append("[bold]Recent History[/bold]")
                history_display = []
                for h in check.history[-10:]:
                    status_char = "✓" if h.status == 0 else "✗"
                    color = "green" if h.status == 0 else ("yellow" if h.status == 1 else "red")
                    history_display.append(f"[{color}]{status_char}[/{color}]")
                lines.append(f"  {''.join(history_display)} (oldest → newest)")
                lines.append(f"  Total State Change: {check.total_state_change}%")
                lines.append("")

        # Entity Information
        if hasattr(data, 'entity') and data.entity:
            entity = data.entity
            lines.append("[bold]Entity[/bold]")
            lines.append(f"  Name: {entity.metadata.name}")
            if hasattr(entity, 'entity_class'):
                lines.append(f"  Class: {entity.entity_class}")
            if hasattr(entity, 'subscriptions') and entity.subscriptions:
                lines.append(f"  Subscriptions: {', '.join(entity.subscriptions)}")
            if hasattr(entity, 'system') and entity.system:
                system = entity.system
                if hasattr(system, 'platform'):
                    lines.append(f"  Platform: {system.platform} {getattr(system, 'platform_version', '')}")
                if hasattr(system, 'arch'):
                    lines.append(f"  Architecture: {system.arch}")

        return "\n".join(lines)

    def _format_generic(self, resource: SensuResource) -> str:
        """Format a generic resource as JSON."""
        lines = []
        lines.append(f"[bold]Connection:[/bold] {resource.connection_name}")
        lines.append(f"[bold]Namespace:[/bold] {resource.connection.namespace}")
        lines.append("")
        lines.append("[bold]Resource Data:[/bold]")

        try:
            if is_dataclass(resource.data):
                data_dict = asdict(resource.data)
            else:
                data_dict = resource.data
            formatted_data = json.dumps(data_dict, indent=2, default=str)
        except Exception:
            formatted_data = str(resource.data)

        lines.append(formatted_data)
        return "\n".join(lines)

    def show_resource(self, resource: SensuResource) -> None:
        """
        Display details for the given resource.
        """
        self.current_resource = resource
        content = self.query_one("#detail-content", Static)

        # Determine resource type and format accordingly
        data = resource.data
        if hasattr(data, 'check') and hasattr(data, 'entity'):
            # This is an Event
            formatted = self._format_event(resource)
        else:
            # Generic formatting
            formatted = self._format_generic(resource)

        content.update(formatted)
    
    def clear(self) -> None:
        """
        Clear the detail view.
        """
        self.current_resource = None
        content = self.query_one("#detail-content", Static)
        content.update("Select an item to view details")
