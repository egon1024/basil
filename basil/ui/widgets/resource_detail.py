from textual.app import ComposeResult
from textual.widgets import Static, Rule
from textual.containers import Vertical, ScrollableContainer
from basil.client import SensuResource
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict, List


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
        self.all_events: List[SensuResource] = []  # Cache of all events for entity detail
    
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

    def _safe_get(self, obj: Any, attr: str, default: Any = None) -> Any:
        """
        Safely get an attribute from an object, handling both dict and object access.

        Args:
            obj: Object or dict to get attribute from
            attr: Attribute name
            default: Default value if attribute not found

        Returns:
            Attribute value or default
        """
        if obj is None:
            return default

        # Try dict-like access first
        if isinstance(obj, dict):
            return obj.get(attr, default)

        # Try object attribute access
        if hasattr(obj, attr):
            value = getattr(obj, attr, default)
            # Return None as default, not empty values
            if value is None or value == '' or value == [] or value == {}:
                return default
            return value

        return default

    def _format_entity(self, resource: SensuResource) -> str:
        """Format an Entity resource for display."""
        data = resource.data
        lines = []

        # Header
        metadata = getattr(data, 'metadata', None)
        entity_name = getattr(metadata, 'name', 'Unknown') if metadata else 'Unknown'

        lines.append(f"[bold cyan]{entity_name}[/bold cyan]")
        lines.append(f"[dim]Connection: {resource.connection_name} | Namespace: {resource.connection.namespace}[/dim]")
        lines.append("")

        # Entity Information
        lines.append("[bold]Entity Details[/bold]")
        entity_class = getattr(data, 'entity_class', 'N/A')
        lines.append(f"  Class: {entity_class}")

        if hasattr(data, 'subscriptions') and data.subscriptions:
            lines.append(f"  Subscriptions: {', '.join(data.subscriptions)}")

        if hasattr(data, 'last_seen') and data.last_seen:
            lines.append(f"  Last Seen: {self._format_timestamp(data.last_seen)}")

        if hasattr(data, 'sensu_agent_version') and data.sensu_agent_version:
            lines.append(f"  Agent Version: {data.sensu_agent_version}")

        # System information
        if hasattr(data, 'system') and data.system:
            system = data.system
            if hasattr(system, 'hostname'):
                lines.append(f"  Hostname: {system.hostname}")

        lines.append("")

        # Group checks by status from events
        checks_by_status = self._group_entity_checks(entity_name, resource.connection_name)

        # Display checks in error state
        if checks_by_status['critical']:
            lines.append("[bold red]Checks in Critical State[/bold red]")
            for check_info in checks_by_status['critical']:
                lines.append(f"  [red]✗[/red] {check_info['name']}")
                if check_info['output']:
                    # Show first line of output
                    first_line = check_info['output'].split('\n')[0][:60]
                    lines.append(f"    [dim]{first_line}[/dim]")
            lines.append("")

        # Display checks in warning state
        if checks_by_status['warning']:
            lines.append("[bold yellow]Checks in Warning State[/bold yellow]")
            for check_info in checks_by_status['warning']:
                lines.append(f"  [yellow]⚠[/yellow] {check_info['name']}")
                if check_info['output']:
                    first_line = check_info['output'].split('\n')[0][:60]
                    lines.append(f"    [dim]{first_line}[/dim]")
            lines.append("")

        # Display checks passing
        if checks_by_status['ok']:
            lines.append("[bold green]Checks Passing[/bold green]")
            for check_info in checks_by_status['ok']:
                lines.append(f"  [green]✓[/green] {check_info['name']}")
            lines.append("")

        # If no checks found
        if not any([checks_by_status['ok'], checks_by_status['warning'], checks_by_status['critical']]):
            lines.append("[dim]No checks found for this entity[/dim]")
            lines.append("")

        # Miscellaneous details section
        misc_lines = self._format_entity_miscellaneous(data)
        if misc_lines:
            lines.append("[bold]Additional Details[/bold]")
            lines.extend(misc_lines)
            lines.append("")

        return "\n".join(lines)

    def _format_entity_miscellaneous(self, data: Any) -> List[str]:
        """
        Format miscellaneous entity details that aren't shown in main sections.

        Args:
            data: Entity data object

        Returns:
            List of formatted lines
        """
        lines = []

        # Attributes already displayed in main sections:
        # - metadata.name (in header)
        # - entity_class
        # - subscriptions
        # - last_seen
        # - sensu_agent_version
        # - system.platform, system.platform_version, system.arch, system.hostname

        # Debug: Show all available attributes and system attributes
        lines.append(f"  [dim]Entity attributes:[/dim]")
        if hasattr(data, '__dict__'):
            for key in sorted(data.__dict__.keys()):
                lines.append(f"    [dim]{key}[/dim]")
        elif hasattr(data, 'model_fields'):
            # Pydantic model
            for key in sorted(data.model_fields.keys()):
                lines.append(f"    [dim]{key}[/dim]")

        system = self._safe_get(data, 'system')
        if system:
            lines.append(f"  [dim]System attributes:[/dim]")
            if hasattr(system, '__dict__'):
                for key in sorted(system.__dict__.keys()):
                    value = getattr(system, key, None)
                    value_preview = str(value)[:50] if value is not None else 'None'
                    lines.append(f"    [dim]{key}: {type(value).__name__} = {value_preview}[/dim]")
            elif hasattr(system, 'model_fields'):
                # Pydantic model
                for key in sorted(system.model_fields.keys()):
                    value = getattr(system, key, None)
                    value_preview = str(value)[:50] if value is not None else 'None'
                    lines.append(f"    [dim]{key}: {type(value).__name__} = {value_preview}[/dim]")
            else:
                # Use dir() as fallback
                for key in sorted([k for k in dir(system) if not k.startswith('_')]):
                    try:
                        value = getattr(system, key, None)
                        if not callable(value):
                            value_preview = str(value)[:50] if value is not None else 'None'
                            lines.append(f"    [dim]{key}: {type(value).__name__} = {value_preview}[/dim]")
                    except:
                        pass

        # Check for deregister flag
        deregister = self._safe_get(data, 'deregister')
        if deregister:
            lines.append(f"  Deregister: [yellow]Enabled[/yellow]")

        # Check for deregistration handler
        deregistration = self._safe_get(data, 'deregistration')
        if deregistration:
            if isinstance(deregistration, dict):
                handler = deregistration.get('handler', 'N/A')
                lines.append(f"  Deregistration Handler: {handler}")
            else:
                lines.append(f"  Deregistration: {deregistration}")

        # Check for user field
        user = self._safe_get(data, 'user')
        if user:
            lines.append(f"  User: {user}")

        # Check for redact list
        redact = self._safe_get(data, 'redact')
        if redact:
            lines.append(f"  Redacted Fields:")
            for field in redact:
                lines.append(f"    • {field}")

        # Additional system details
        system = self._safe_get(data, 'system')
        if system:
            # OS info - try multiple possible field names
            os_info = self._safe_get(system, 'os')
            # Try various possible field names for OS version
            os_version = (self._safe_get(system, 'os_version') or
                         self._safe_get(system, 'osversion'))

            if os_info:
                if os_version:
                    lines.append(f"  OS: {os_info} {os_version}")
                else:
                    lines.append(f"  OS: {os_info}")
            elif os_version:
                lines.append(f"  OS Version: {os_version}")

            # Platform and Architecture (moved from main section)
            platform = self._safe_get(system, 'platform')
            platform_version = self._safe_get(system, 'platform_version')
            if platform:
                if platform_version:
                    lines.append(f"  Platform: {platform} {platform_version}")
                else:
                    lines.append(f"  Platform: {platform}")

            arch = self._safe_get(system, 'arch')
            if arch:
                lines.append(f"  Architecture: {arch}")

            # VM info - only show if it's actually set to a meaningful value
            # "kvm" alone usually means bare metal or undetected
            vm_system = self._safe_get(system, 'vm_system')
            vm_role = self._safe_get(system, 'vm_role')

            # Only display VM info if vm_role is "guest" or vm_system is something other than just "kvm"
            if vm_role and vm_role.lower() == 'guest':
                if vm_system:
                    lines.append(f"  VM System: {vm_system}")
                lines.append(f"  VM Role: {vm_role}")
            elif vm_system and vm_system.lower() not in ['kvm', 'none', '']:
                lines.append(f"  VM System: {vm_system}")
                if vm_role:
                    lines.append(f"  VM Role: {vm_role}")

            # Cloud provider
            cloud_provider = self._safe_get(system, 'cloud_provider')
            if cloud_provider:
                lines.append(f"  Cloud Provider: {cloud_provider}")

            # Libc type
            libc_type = self._safe_get(system, 'libc_type')
            if libc_type:
                lines.append(f"  Libc Type: {libc_type}")

            # Float info
            float_type = self._safe_get(system, 'float_type')
            if float_type:
                lines.append(f"  Float Type: {float_type}")

            # Processes
            processes = self._safe_get(system, 'processes')
            if processes:
                if isinstance(processes, list):
                    lines.append(f"  Processes: {len(processes)}")

            # Uptime
            uptime = self._safe_get(system, 'uptime')
            if uptime:
                uptime_seconds = int(uptime)
                days = uptime_seconds // 86400
                hours = (uptime_seconds % 86400) // 3600
                minutes = (uptime_seconds % 3600) // 60
                if days > 0:
                    lines.append(f"  Uptime: {days}d {hours}h {minutes}m")
                elif hours > 0:
                    lines.append(f"  Uptime: {hours}h {minutes}m")
                else:
                    lines.append(f"  Uptime: {minutes}m")

            # CPU info
            cpus = self._safe_get(system, 'cpus')
            if cpus:
                if isinstance(cpus, list) and len(cpus) > 0:
                    lines.append(f"  CPUs: {len(cpus)}")
                    # Show CPU model if available
                    first_cpu = cpus[0]
                    model_name = self._safe_get(first_cpu, 'model_name')
                    if model_name:
                        lines.append(f"    Model: {model_name}")
                elif isinstance(cpus, int):
                    lines.append(f"  CPUs: {cpus}")

            # Memory
            memory = self._safe_get(system, 'memory')
            if memory:
                total = self._safe_get(memory, 'total')
                if total and total > 0:
                    # Convert to GB
                    total_gb = total / (1024 ** 3)
                    lines.append(f"  Memory: {total_gb:.2f} GB")

            # Network information
            network = self._safe_get(system, 'network')
            if network:
                interfaces = self._safe_get(network, 'interfaces')
                if interfaces:
                    lines.append(f"  Network Interfaces: {len(interfaces)}")
                    # Show interface details
                    for interface in interfaces:
                        iface_name = self._safe_get(interface, 'name', 'unknown')
                        addresses = self._safe_get(interface, 'addresses', [])
                        if addresses:
                            lines.append(f"    • {iface_name}:")
                            for addr in addresses[:3]:  # Limit to first 3 addresses
                                lines.append(f"      - {addr}")

        # Metadata labels and annotations
        metadata = self._safe_get(data, 'metadata')
        if metadata:
            labels = self._safe_get(metadata, 'labels')
            if labels and isinstance(labels, dict):
                lines.append(f"  Labels:")
                for key, value in labels.items():
                    lines.append(f"    • {key}: {value}")

            annotations = self._safe_get(metadata, 'annotations')
            if annotations and isinstance(annotations, dict):
                lines.append(f"  Annotations:")
                for key, value in annotations.items():
                    # Truncate long annotation values
                    value_str = str(value)[:80]
                    if len(str(value)) > 80:
                        value_str += "..."
                    lines.append(f"    • {key}: {value_str}")

        return lines

    def _group_entity_checks(self, entity_name: str, connection_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group checks for a specific entity by their status.

        Args:
            entity_name: Name of the entity
            connection_name: Connection name

        Returns:
            Dictionary with 'ok', 'warning', 'critical' keys, each containing list of check info
        """
        result = {'ok': [], 'warning': [], 'critical': []}

        for event in self.all_events:
            # Match entity and connection
            event_entity = getattr(getattr(event.data, 'entity', None), 'metadata', None)
            event_entity_name = getattr(event_entity, 'name', None) if event_entity else None

            if event_entity_name != entity_name or event.connection_name != connection_name:
                continue

            # Extract check information
            check = getattr(event.data, 'check', None)
            if not check:
                continue

            check_metadata = getattr(check, 'metadata', None)
            check_name = getattr(check_metadata, 'name', 'Unknown') if check_metadata else 'Unknown'
            status = getattr(check, 'status', None)
            output = getattr(check, 'output', '')

            check_info = {
                'name': check_name,
                'status': status,
                'output': output
            }

            if status == 0:
                result['ok'].append(check_info)
            elif status == 1:
                result['warning'].append(check_info)
            elif status == 2:
                result['critical'].append(check_info)

        # Sort each list by check name
        for key in result:
            result[key].sort(key=lambda x: x['name'])

        return result

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
        elif hasattr(data, 'entity_class') and hasattr(data, 'subscriptions'):
            # This is an Entity
            formatted = self._format_entity(resource)
        else:
            # Generic formatting
            formatted = self._format_generic(resource)

        content.update(formatted)

    def set_events(self, events: List[SensuResource]) -> None:
        """
        Set the events cache for entity detail display.

        Args:
            events: List of all events
        """
        self.all_events = events
    
    def clear(self) -> None:
        """
        Clear the detail view.
        """
        self.current_resource = None
        content = self.query_one("#detail-content", Static)
        content.update("Select an item to view details")
