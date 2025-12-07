import yaml
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pathlib import Path
from typing import Dict, Any
import base64
import os


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


def save_encrypted_config(config: Dict[str, Any], password: str, file_path: Path) -> None:
    """
    Save configuration to an encrypted file.
    
    Args:
        config: Configuration dictionary
        password: Encryption password
        file_path: Path to save the encrypted config
    """
    # Create parent directories if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate a random salt
    salt = os.urandom(16)
    
    # Derive key from password
    key = _derive_key(password, salt)
    
    # Convert config to YAML
    yaml_data = yaml.dump(config).encode('utf-8')
    
    # Encrypt with Fernet
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(yaml_data)
    
    # Write salt + encrypted data to file
    with open(file_path, 'wb') as f:
        f.write(salt)  # First 16 bytes are the salt
        f.write(encrypted_data)
