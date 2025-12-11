from basil.ui.widgets.base_resource_detail import BaseResourceDetailWidget
from basil.client import SensuResource
import json
from dataclasses import asdict, is_dataclass


class CheckDetailWidget(BaseResourceDetailWidget):
    """Widget for displaying detailed information about a Sensu check."""

    def format_resource(self, resource: SensuResource) -> str:
        """
        Format a Check resource for display.

        Args:
            resource: The check resource to format

        Returns:
            Rich-formatted string with check details
        """
        data = resource.data
        lines = []

        # Header
        metadata = getattr(data, 'metadata', None)
        name = getattr(metadata, 'name', 'Unknown') if metadata else 'Unknown'

        lines.append(f"[bold cyan]{name}[/bold cyan]")
        lines.append(f"[dim]Connection: {resource.connection_name} | Namespace: {resource.connection.namespace}[/dim]")
        lines.append("")

        # Check Configuration
        lines.append("[bold]Check Configuration[/bold]")

        command = getattr(data, 'command', None)
        if command:
            lines.append(f"  Command: [cyan]{command}[/cyan]")

        interval = getattr(data, 'interval', None)
        if interval:
            lines.append(f"  Interval: {interval}s")

        timeout = getattr(data, 'timeout', None)
        if timeout:
            lines.append(f"  Timeout: {timeout}s")

        subscriptions = getattr(data, 'subscriptions', None)
        if subscriptions:
            lines.append(f"  Subscriptions: {', '.join(subscriptions)}")

        handlers = getattr(data, 'handlers', None)
        if handlers:
            lines.append(f"  Handlers: {', '.join(handlers)}")

        runtime_assets = getattr(data, 'runtime_assets', None)
        if runtime_assets:
            lines.append(f"  Runtime Assets: {', '.join(runtime_assets)}")

        publish = getattr(data, 'publish', None)
        if publish is not None:
            lines.append(f"  Publish: {publish}")

        stdin = getattr(data, 'stdin', None)
        if stdin is not None:
            lines.append(f"  STDIN: {stdin}")

        lines.append("")

        # Check Hooks
        check_hooks = getattr(data, 'check_hooks', None)
        if check_hooks:
            lines.append("[bold]Check Hooks[/bold]")
            for hook_dict in check_hooks:
                for hook_type, hook_list in hook_dict.items():
                    if hook_list:
                        lines.append(f"  {hook_type}: {', '.join(hook_list)}")
            lines.append("")

        # Proxy Configuration
        proxy_entity_name = getattr(data, 'proxy_entity_name', None)
        if proxy_entity_name:
            lines.append("[bold]Proxy Configuration[/bold]")
            lines.append(f"  Proxy Entity Name: {proxy_entity_name}")

            proxy_requests = getattr(data, 'proxy_requests', None)
            if proxy_requests:
                lines.append(f"  Proxy Requests: {proxy_requests}")
            lines.append("")

        # High Availability
        round_robin = getattr(data, 'round_robin', None)
        if round_robin is not None:
            lines.append("[bold]High Availability[/bold]")
            lines.append(f"  Round Robin: {round_robin}")
            lines.append("")

        # Metadata
        if metadata:
            labels = getattr(metadata, 'labels', None)
            if labels and isinstance(labels, dict):
                lines.append("[bold]Labels[/bold]")
                for key, value in labels.items():
                    lines.append(f"  {key}: {value}")
                lines.append("")

            annotations = getattr(metadata, 'annotations', None)
            if annotations and isinstance(annotations, dict):
                lines.append("[bold]Annotations[/bold]")
                for key, value in annotations.items():
                    # Truncate long annotation values
                    value_str = str(value)[:80]
                    if len(str(value)) > 80:
                        value_str += "..."
                    lines.append(f"  {key}: {value_str}")
                lines.append("")

        # Output Metric Format
        output_metric_format = getattr(data, 'output_metric_format', None)
        output_metric_handlers = getattr(data, 'output_metric_handlers', None)
        if output_metric_format or output_metric_handlers:
            lines.append("[bold]Metrics[/bold]")
            if output_metric_format:
                lines.append(f"  Output Metric Format: {output_metric_format}")
            if output_metric_handlers:
                lines.append(f"  Output Metric Handlers: {', '.join(output_metric_handlers)}")
            lines.append("")

        # Raw data for debugging (collapsed)
        lines.append("[bold]Raw Data[/bold]")
        try:
            if is_dataclass(data):
                data_dict = asdict(data)
            else:
                data_dict = data if isinstance(data, dict) else {}
            formatted_data = json.dumps(data_dict, indent=2, default=str)
            # Show first 20 lines
            data_lines = formatted_data.split('\n')
            if len(data_lines) > 20:
                lines.append(f"  [dim](Showing first 20 lines of {len(data_lines)})[/dim]")
                for line in data_lines[:20]:
                    lines.append(f"  {line}")
                lines.append("  [dim]...[/dim]")
            else:
                for line in data_lines:
                    lines.append(f"  {line}")
        except Exception as e:
            lines.append(f"  [dim]Could not format raw data: {e}[/dim]")

        return "\n".join(lines)
