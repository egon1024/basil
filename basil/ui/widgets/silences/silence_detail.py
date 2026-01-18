"""
Widget for displaying Silence details.
"""
# Built-in imports
import json
from dataclasses import asdict, is_dataclass

# Basil imports
from basil.ui.widgets.base_resource_detail import BaseResourceDetailWidget
from basil.client import SensuResource


class SilenceDetailWidget(BaseResourceDetailWidget):
    """Widget for displaying detailed information about a Sensu silence."""

    def format_resource(self, resource: SensuResource) -> str:
        """
        Format a Silence resource for display.

        Args:
            resource: The silence resource to format

        Returns:
            Rich-formatted string with silence details
        """
        data = resource.data
        lines = []

        # Header
        metadata = getattr(data, 'metadata', None)
        name = getattr(metadata, 'name', 'Unknown') if metadata else 'Unknown'

        lines.append(f"[bold cyan]{name}[/bold cyan]")
        lines.append(
            f"[dim]Connection: {resource.connection_name} | "
            f"Namespace: {resource.connection.namespace}[/dim]"
        )
        lines.append("")

        # Silence Details
        lines.append("[bold]Silence Details[/bold]")

        reason = getattr(data, 'reason', 'N/A')
        if reason and reason != 'N/A':
            lines.append(f"  Reason: {reason}")

        expire = getattr(data, 'expire', None)
        if expire:
            if expire == -1:
                lines.append("  Expires: Never")
            elif isinstance(expire, int):
                lines.append(f"  Expires: {self.format_timestamp(expire)}")
            else:
                lines.append(f"  Expires: {expire}")

        expire_on_resolve = getattr(data, 'expire_on_resolve', None)
        if expire_on_resolve is not None:
            lines.append(f"  Expire on Resolve: {expire_on_resolve}")

        # Check filter
        check = getattr(data, 'check', None)
        if check:
            lines.append(f"  Check: {check}")

        # Subscription filter
        subscription = getattr(data, 'subscription', None)
        if subscription:
            lines.append(f"  Subscription: {subscription}")

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
