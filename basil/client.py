"""
Sensu client wrapper and connection management.
"""

# built-in imports
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

# 3rd party imports
from fawlty.sensu_client import SensuClient
from fawlty.sensu_server import SensuServer
from fawlty.resources.entity import Entity
from fawlty.resources.event import Event
from fawlty.resources.check import Check
from fawlty.resources.silence import Silence


class SensuResource:
    """
    Wrapper for a Sensu resource that includes connection metadata.
    """
    def __init__(self, data: Dict[str, Any], connection: 'SensuConnection'):
        """
        Initialize the wrapper.
        """
        self.data = data
        self.connection = connection
        self.connection_name = connection.name

    def __getitem__(self, key: str) -> Any:
        """
        Allow dict-like access to the underlying data.
        """
        return self.data[key]

    def __repr__(self) -> str:
        """
        Return string representation.
        """
        return f"SensuResource(connection={self.connection_name}, data={self.data})"


class SensuConnection:
    """
    Manages a single connection to a Sensu server using fawlty.
    Exposes the fawlty client directly for callers to use.
    """
    def __init__(self, name: str, url: str, api_key: Optional[str] = None,
                 username: Optional[str] = None, password: Optional[str] = None,
                 namespace: str = "default"):
        """
        Initialize a new Sensu connection.
        """

        self.name = name
        self.namespace = namespace

        # Parse URL to extract host, port, and scheme
        parsed = urlparse(url)
        host = parsed.hostname or url
        port = parsed.port or (443 if parsed.scheme == 'https' else 8080)
        use_ssl = parsed.scheme == 'https'

        # Create SensuServer object
        server = SensuServer(
            host=host,
            port=port,
            use_ssl=use_ssl,
            ignore_cert=False  # TODO: Make this configurable
        )

        # Create SensuClient with the server
        self.client = SensuClient(server=server)

        # Authenticate
        if api_key:
            # TODO: fawlty doesn't support API key auth yet
            # For now, we'll raise an error
            raise NotImplementedError("API key authentication is not yet supported by fawlty")

        if username and password:
            self.client.login(username, password)
        else:
            raise ValueError("Either api_key or username/password must be provided")


class ConnectionManager:
    """
    Singleton-like manager for all Sensu connections.
    """
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the connection manager with a configuration dictionary.
        """
        self._connections: Dict[str, SensuConnection] = {}
        self._load_connections(config)

    def _load_connections(self, config: Dict[str, Any]):
        """
        Parses configuration and creates SensuConnection objects.
        Expected config format:
        connections:
          - name: prod
            url: https://sensu.prod.example.com
            api_key: sensitive_key
            namespace: prod_ops
          - name: dev
            url: https://sensu.dev.example.com
            username: user
            password: password
        """
        connections_config = config.get("connections", [])
        for conn_cfg in connections_config:
            name = conn_cfg.get("name")
            if not name:
                continue # Skip unnamed connections

            self._connections[name] = SensuConnection(
                name=name,
                url=conn_cfg.get("url"),
                api_key=conn_cfg.get("api_key"),
                username=conn_cfg.get("username"),
                password=conn_cfg.get("password"),
                namespace=conn_cfg.get("namespace", "default")
            )

    def get_connection(self, name: str) -> Optional[SensuConnection]:
        """
        Retrieve a specific connection by name.
        """
        return self._connections.get(name)

    def get_all_connections(self) -> List[SensuConnection]:
        """
        Retrieve all active connections.
        """
        return list(self._connections.values())

    def get_all(self, resource_type: str) -> Optional[List[SensuResource]]:
        """
        Fetch all items of a given resource type from all connections.

        Args:
            resource_type: The resource type (e.g., 'entities', 'events', 'silenced', 'checks')

        Returns:
            List of SensuResource instances, each wrapping the original data
            with connection metadata accessible via .connection and .connection_name.
            Returns None if all connections failed (to distinguish from empty but successful
            result).
        """
        # Map resource types to fawlty resource classes

        resource_map = {
            'entities': Entity,
            'events': Event,
            'checks': Check,
            'silenced': Silence,
        }

        resource_class = resource_map.get(resource_type)
        if not resource_class:
            # Unknown resource type
            return []

        all_items = []
        success_count = 0
        error_count = 0
        errors = []

        for conn in self._connections.values():
            try:
                # Call Resource.get(client=..., namespace=...)
                items = resource_class.get(client=conn.client, namespace=conn.namespace)

                # Wrap each item with connection metadata
                for item in items:
                    all_items.append(SensuResource(data=item, connection=conn))

                success_count += 1

            except Exception as e:
                # Track error but continue with other connections
                error_count += 1
                errors.append(f"{conn.name}: {e}")
                continue

        # If all connections failed, return None to indicate total failure
        if success_count == 0 and error_count > 0:
            # Log errors for debugging
            for error in errors:
                print(f"Error fetching {resource_type}: {error}")
            return None

        return all_items
