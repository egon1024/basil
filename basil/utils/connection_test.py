"""
Utility for testing Sensu server connections.
"""
from typing import Dict, Any, Tuple
from basil.client import SensuConnection


def test_sensu_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test a Sensu server connection.

    Args:
        config: Server configuration dict with keys:
            - name: Server name
            - url: Server URL
            - api_key: Optional API key (not yet supported)
            - username: Optional username
            - password: Optional password
            - namespace: Optional namespace (default: "default")

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Create a temporary connection
        _ = SensuConnection(
            name=config.get("name", "test"),
            url=config["url"],
            api_key=config.get("api_key"),
            username=config.get("username"),
            password=config.get("password"),
            namespace=config.get("namespace", "default")
        )

        # If we got here without exception, authentication succeeded
        return True, "Connection successful"

    except NotImplementedError as e:
        return False, str(e)
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Connection failed: {str(e)}"
