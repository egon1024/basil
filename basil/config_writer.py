import yaml
from cryptography.fernet import Fernet
from pathlib import Path
from typing import Dict, Any


def save_encrypted_config(config: Dict[str, Any], password: str, file_path: Path) -> None:
    """
    Save configuration to an encrypted file.
    
    Args:
        config: Configuration dictionary
        password: Encryption password (Fernet key)
        file_path: Path to save the encrypted config
    """
    # Create parent directories if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert config to YAML
    yaml_data = yaml.dump(config).encode('utf-8')
    
    # Encrypt with Fernet
    fernet = Fernet(password.encode() if isinstance(password, str) else password)
    encrypted_data = fernet.encrypt(yaml_data)
    
    # Write to file
    with open(file_path, 'wb') as f:
        f.write(encrypted_data)
