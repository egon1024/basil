# built-in imports
import base64
from typing import Dict, Any
from pathlib import Path

# third party imports
import yaml
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def _derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive a Fernet key from a password using PBKDF2.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

class ConfigLoader:
    """
    Loads and decrypts configuration files.
    """
    def __init__(self, config_path: Path):
        self.config_path = config_path

    def load(self, password: str) -> Dict[str, Any]:
        """
        Decrypts and parses all the configuration data.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "rb") as f:
            # First 16 bytes are the salt
            salt = f.read(16)
            encrypted_data = f.read()

        # Derive key from password
        key = _derive_key(password, salt)

        # Decrypt
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data)

        return yaml.safe_load(decrypted_data)
