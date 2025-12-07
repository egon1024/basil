#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


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


def main():
    parser = argparse.ArgumentParser(description="Decrypt config file to stdout")
    parser.add_argument("file", help="Path to encrypted config file")
    parser.add_argument("--password", "-p", required=True, help="Encryption password")
    
    args = parser.parse_args()
    
    path = Path(args.file)
    if not path.exists():
        print(f"Error: File {path} not found", file=sys.stderr)
        sys.exit(1)
        
    try:
        with open(path, "rb") as f:
            # First 16 bytes are the salt
            salt = f.read(16)
            encrypted_data = f.read()
        
        # Derive key from password
        key = _derive_key(args.password, salt)
        
        # Decrypt
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_data)
        
        print(decrypted.decode('utf-8'))
        
    except Exception as e:
        print(f"Error decrypting config: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
