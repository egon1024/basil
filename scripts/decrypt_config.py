#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from cryptography.fernet import Fernet

def main():
    parser = argparse.ArgumentParser(description="Decrypt config file to stdout")
    parser.add_argument("file", help="Path to encrypted config file")
    # In a real app we might prompt for password to avoid history, but arg is requested "easily"
    parser.add_argument("--password", "-p", required=True, help="Encryption key/password")
    
    args = parser.parse_args()
    
    path = Path(args.file)
    if not path.exists():
        print(f"Error: File {path} not found", file=sys.stderr)
        sys.exit(1)
        
    try:
        with open(path, "rb") as f:
            data = f.read()
            
        fernet = Fernet(args.password)
        decrypted = fernet.decrypt(data)
        
        print(decrypted.decode('utf-8'))
        
    except Exception as e:
        print(f"Error decrypting config: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
