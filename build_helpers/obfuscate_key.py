#!/usr/bin/env python3
"""
API Key Obfuscation Script for Git Tool Suite.
Run this before building the executable to inject the obfuscated API key.

Usage:
    1. Add GEMINI_API_KEY to .env file OR set environment variable
    2. Run: python build_helpers/obfuscate_key.py
    3. Build: pyinstaller --onefile --windowed main.py
"""

import base64
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


def obfuscate_key(api_key):
    """
    Multi-layer obfuscation of API key.
    Returns three fragments for storage.
    """
    # Compute salt (must match config.py)
    salt_source = "GitToolSuite_v3.0"
    salt = sum(ord(c) for c in salt_source) & 0xFF
    
    # XOR with salt
    xored = bytes([ord(c) ^ salt for c in api_key])
    
    # Base64 encode
    encoded = base64.b64encode(xored).decode('utf-8')
    
    # Split into 3 parts
    third = len(encoded) // 3
    part1 = encoded[:third]
    part2 = encoded[third:2*third]
    part3 = encoded[2*third:]
    
    return part1, part2, part3


def inject_into_config(part1, part2, part3):
    """Updates config.py with obfuscated key fragments."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.py')
    
    # Read current config
    with open(config_path, 'r') as f:
        lines = f.readlines()
    
    # Find and replace the placeholder lines
    new_lines = []
    for line in lines:
        if '_KEY_PART1 = "PLACEHOLDER_PART1"' in line:
            new_lines.append(f'    _KEY_PART1 = "{part1}"\n')
        elif '_KEY_PART2 = "PLACEHOLDER_PART2"' in line:
            new_lines.append(f'    _KEY_PART2 = "{part2}"\n')
        elif '_KEY_PART3 = "PLACEHOLDER_PART3"' in line:
            new_lines.append(f'    _KEY_PART3 = "{part3}"\n')
        else:
            new_lines.append(line)
    
    # Write back
    with open(config_path, 'w') as f:
        f.writelines(new_lines)


def main():
    # Try to read from .env file first, then environment variable
    # Check both GEMINI_API_KEY (production) and GEMINI_API_KEY_OVERRIDE (dev)
    api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY_OVERRIDE')
    
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found")
        print("\nPlease provide your API key using one of these methods:")
        print("  1. Add to .env file: GEMINI_API_KEY=your_key_here")
        print("  2. Set environment variable: export GEMINI_API_KEY='your_key_here'")
        print("\nThen run:")
        print("  python build_helpers/obfuscate_key.py")
        print("\nAfter obfuscation, build the executable:")
        print("  pyinstaller --onefile --windowed --name GitToolSuite main.py")
        sys.exit(1)
    
    print("✓ API key found")
    print("Obfuscating API key...")
    parts = obfuscate_key(api_key)
    
    print("Injecting into config.py...")
    inject_into_config(*parts)
    
    print("✓ API key successfully obfuscated and injected!")
    print("\nNext steps:")
    print("  1. Build executable: pyinstaller --onefile --windowed --name GitToolSuite main.py")
    print("  2. Distribute the executable - users won't need to configure API key!")


if __name__ == "__main__":
    main()
