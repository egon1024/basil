from basil.ui.widgets.base_resource_detail import BaseResourceDetailWidget
from basil.client import SensuResource
from typing import List, Dict, Any


class EntityDetailWidget(BaseResourceDetailWidget):
    """Widget for displaying detailed information about a Sensu entity."""

    def __init__(self, *args, **kwargs):
        """Initialize the entity detail widget."""
        super().__init__(*args, **kwargs)
        self.all_events: List[SensuResource] = []  # Cache of all events for check grouping

    def set_events(self, events: List[SensuResource]) -> None:
        """
        Set the events cache for entity detail display.

        Args:
            events: List of all events
        """
        self.all_events = events

    def format_resource(self, resource: SensuResource) -> str:
        """
        Format an Entity resource for display.

        Args:
            resource: The entity resource to format

        Returns:
            Rich-formatted string with entity details
        """
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
            lines.append(f"  Last Seen: {self.format_timestamp(data.last_seen)}")

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

        system = self.safe_get(data, 'system')
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
        deregister = self.safe_get(data, 'deregister')
        if deregister:
            lines.append(f"  Deregister: [yellow]Enabled[/yellow]")

        # Check for deregistration handler
        deregistration = self.safe_get(data, 'deregistration')
        if deregistration:
            if isinstance(deregistration, dict):
                handler = deregistration.get('handler', 'N/A')
                lines.append(f"  Deregistration Handler: {handler}")
            else:
                lines.append(f"  Deregistration: {deregistration}")

        # Check for user field
        user = self.safe_get(data, 'user')
        if user:
            lines.append(f"  User: {user}")

        # Check for redact list
        redact = self.safe_get(data, 'redact')
        if redact:
            lines.append(f"  Redacted Fields:")
            for field in redact:
                lines.append(f"    • {field}")

        # Additional system details
        system = self.safe_get(data, 'system')
        if system:
            # OS info - try multiple possible field names
            os_info = self.safe_get(system, 'os')
            # Try various possible field names for OS version
            os_version = (self.safe_get(system, 'os_version') or
                         self.safe_get(system, 'osversion'))

            if os_info:
                if os_version:
                    lines.append(f"  OS: {os_info} {os_version}")
                else:
                    lines.append(f"  OS: {os_info}")
            elif os_version:
                lines.append(f"  OS Version: {os_version}")

            # Platform and Architecture (moved from main section)
            platform = self.safe_get(system, 'platform')
            platform_version = self.safe_get(system, 'platform_version')
            if platform:
                if platform_version:
                    lines.append(f"  Platform: {platform} {platform_version}")
                else:
                    lines.append(f"  Platform: {platform}")

            arch = self.safe_get(system, 'arch')
            if arch:
                lines.append(f"  Architecture: {arch}")

            # VM info - only show if it's actually set to a meaningful value
            # "kvm" alone usually means bare metal or undetected
            vm_system = self.safe_get(system, 'vm_system')
            vm_role = self.safe_get(system, 'vm_role')

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
            cloud_provider = self.safe_get(system, 'cloud_provider')
            if cloud_provider:
                lines.append(f"  Cloud Provider: {cloud_provider}")

            # Libc type
            libc_type = self.safe_get(system, 'libc_type')
            if libc_type:
                lines.append(f"  Libc Type: {libc_type}")

            # Float info
            float_type = self.safe_get(system, 'float_type')
            if float_type:
                lines.append(f"  Float Type: {float_type}")

            # Processes
            processes = self.safe_get(system, 'processes')
            if processes:
                if isinstance(processes, list):
                    lines.append(f"  Processes: {len(processes)}")

            # Uptime
            uptime = self.safe_get(system, 'uptime')
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
            cpus = self.safe_get(system, 'cpus')
            if cpus:
                if isinstance(cpus, list) and len(cpus) > 0:
                    lines.append(f"  CPUs: {len(cpus)}")
                    # Show CPU model if available
                    first_cpu = cpus[0]
                    model_name = self.safe_get(first_cpu, 'model_name')
                    if model_name:
                        lines.append(f"    Model: {model_name}")
                elif isinstance(cpus, int):
                    lines.append(f"  CPUs: {cpus}")

            # Memory
            memory = self.safe_get(system, 'memory')
            if memory:
                total = self.safe_get(memory, 'total')
                if total and total > 0:
                    # Convert to GB
                    total_gb = total / (1024 ** 3)
                    lines.append(f"  Memory: {total_gb:.2f} GB")

            # Network information
            network = self.safe_get(system, 'network')
            if network:
                interfaces = self.safe_get(network, 'interfaces')
                if interfaces:
                    lines.append(f"  Network Interfaces: {len(interfaces)}")
                    # Show interface details
                    for interface in interfaces:
                        iface_name = self.safe_get(interface, 'name', 'unknown')
                        addresses = self.safe_get(interface, 'addresses', [])
                        if addresses:
                            lines.append(f"    • {iface_name}:")
                            for addr in addresses[:3]:  # Limit to first 3 addresses
                                lines.append(f"      - {addr}")

        # Metadata labels and annotations
        metadata = self.safe_get(data, 'metadata')
        if metadata:
            labels = self.safe_get(metadata, 'labels')
            if labels and isinstance(labels, dict):
                lines.append(f"  Labels:")
                for key, value in labels.items():
                    lines.append(f"    • {key}: {value}")

            annotations = self.safe_get(metadata, 'annotations')
            if annotations and isinstance(annotations, dict):
                lines.append(f"  Annotations:")
                for key, value in annotations.items():
                    # Truncate long annotation values
                    value_str = str(value)[:80]
                    if len(str(value)) > 80:
                        value_str += "..."
                    lines.append(f"    • {key}: {value_str}")

        return lines
