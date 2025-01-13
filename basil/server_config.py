"""
A class to read/save server configuration.
"""

# Built in imports
import yaml

# 3rd party imports
from pydantic import BaseModel
from fawlty.sensu_server import SensuServer

# Our imports


class ServerEntry(BaseModel):
    """
    A class to hold a server entry.
    """

    name: str
    server: SensuServer
    username: str = None
    password: str = None
    save_username: bool = False
    save_password: bool = False
    namespaces: list = None


class ServerConfig:

    def __init__(self, config_file: str = None, servers: list = None):
        """
        Initialize with EITHER a config file OR a list of servers, not both.
        """

        self.config_file = config_file
        self.servers = servers

        # If we got a config file but no servers, read the config file
        if config_file and not servers:
            self.read_config_file(config_file)

    def read_config_file(self, config_file=None):
        """
        Read the config file and return a list of servers.
        """

        if config_file is not None:
            self.config_file = config_file

        if not self.config_file:
            raise ValueError('No config file specified.')

        servers = []

        # Read int the yaml file
        with open(config_file, 'r') as f:
            server_config = yaml.load(f, Loader=yaml.SafeLoader)

        # Turn the entries into SensuServer objects
        for item in server_config:
            server = SensuServer(**item)
            entry = ServerEntry(**item, server=server)
            if entry.username is not None:
                entry.save_username = True
            if entry.password is not None:
                entry.save_password = True

            namespaces = item.get('namespaces', [])
            
            servers.append(entry)

        self.servers = servers
        print(self.servers)

    def write_config_file(self, config_file=None):
        """
        Write the server configuration to a file.
        """
        if config_file is not None:
            self.config_file = config_file

        if not self.config_file:
            raise ValueError('No config file specified.')

        if not self.servers:
            raise ValueError('No servers to write to the config file.')

        # Form the data structure
        data = []
        for entry in self.servers:
            item = entry.to_dict()
            item['name'] = entry.name
            if not entry.save_username:
                item.pop('username')
            if not entry.save_password:
                item.pop('password')
            item['namespaces'] = entry.namespaces

            data.append(item)

        # Write the yaml file
        with open(self.config_file, 'w') as f:
            yaml.dump(data, f)