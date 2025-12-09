"""
Configuration management for Git Tool Suite.
Handles API key storage (bundled) and user preferences.
"""

import base64
import hashlib
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration handler for API keys and user preferences."""
    
    # These will be replaced by build script with obfuscated fragments
    _KEY_PART1 = "c3tIU2FLcwBDdgV8A"
    _KEY_PART2 = "ApmBndjBx94VXgBV1"
    _KEY_PART3 = "VYUGgfeFxTBX55ZwYC"
    
    _CONFIG_DIR = Path.home() / '.git-tool-suite'
    _PREFS_FILE = _CONFIG_DIR / 'preferences.json'
    
    # App Metadata
    APP_VERSION = "3.3.0"
    IS_LIMITED_BUILD = True # Set to True for builds without API key setup
    UPDATE_CHECK_URL = "https://gist.githubusercontent.com/tan-mike/37c92fd3e04d4663fc70948567ec932d/raw/version.json"

    # Product Key Hash (will be replaced by build script)
    # This is the SHA-256 hash of the actual product key from .env
    _PRODUCT_KEY_HASH = "PLACEHOLDER_PRODUCT_KEY_HASH"

    @staticmethod
    def get_api_key():
        """
        Returns the API key with the following priority:
        1. .env file (GEMINI_API_KEY) - for development
        2. User Preferences (if allowed)
        3. Bundled obfuscated key - for production builds
           (If Limited Edition is active OR not a limited build)
        """
        # Priority 1: Read from .env file (development)
        env_key = os.getenv('GEMINI_API_KEY')
        if env_key:
            return env_key
            
        # Check if Limited Edition is active
        is_limited = Config.is_limited_edition()
            
        # Priority 2: User Preferences 
        # (Always check prefs if NOT limited edition, or if user wants to override)
        prefs = Config.load_preferences()
        user_key = prefs.get('api_key')
        
        # If user has a key and we are NOT limited edition, use it.
        # If we ARE limited edition, we prefer the bundled key, unless the bundled key fails?
        # Actually, let's keep it simple: If Limited Edition is Active => Use Bundled Key.
        # If Not Limited Edition => User must provide key.
        
        if not is_limited:
            if user_key:
                return user_key
            # Fallthrough will return None (or bundled if not limited build? Logic in line 51)
        
        # Priority 3: Bundled Key
        # Only returned if:
        # a) Not a limited build (legacy/dev behavior)
        # b) Limited Edition is ACTIVE (Product Key is valid)
        if not Config.IS_LIMITED_BUILD or is_limited:
            if "PLACEHOLDER" not in Config._KEY_PART1:
                return Config._decode_bundled_key()
                
        # If we are here and still haven't returned, try user_key one last time for safety
        if user_key:
            return user_key
            
        return None

    @staticmethod
    def validate_product_key(user_key):
        """
        Validate a product key by comparing its SHA-256 hash.
        Returns True if the key is valid, False otherwise.
        """
        if not user_key or not user_key.strip():
            return False
        
        # Check if hash has been injected (not placeholder)
        if "PLACEHOLDER" in Config._PRODUCT_KEY_HASH:
            return False
        
        # Compute SHA-256 hash of user input
        user_hash = hashlib.sha256(user_key.strip().encode('utf-8')).hexdigest()
        
        # Compare with embedded hash
        return user_hash == Config._PRODUCT_KEY_HASH
    
    @staticmethod
    def is_limited_edition():
        """Check if the user has activated the Limited Edition with a valid product key."""
        prefs = Config.load_preferences()
        key = prefs.get('product_key', '')
        return Config.validate_product_key(key)
    
    @staticmethod
    def _decode_bundled_key():
        """Multi-layer de-obfuscation of bundled API key."""
        try:
            # Combine fragments
            combined = Config._KEY_PART1 + Config._KEY_PART2 + Config._KEY_PART3
            
            # Compute salt from app metadata (must match obfuscation script)
            salt_source = "GitToolSuite_v3.0"
            salt = sum(ord(c) for c in salt_source) & 0xFF
            
            #Base64 decode
            decoded = base64.b64decode(combined)
            
            # XOR with salt
            unxored = bytes([b ^ salt for b in decoded])
            
            return unxored.decode('utf-8')
        except Exception as e:
            print(f"ERROR decoding API key: {e}")
            return None
    
    @staticmethod
    def load_preferences():
        """Load user preferences from config file."""
        Config._CONFIG_DIR.mkdir(exist_ok=True)
        
        if Config._PREFS_FILE.exists():
            try:
                with open(Config._PREFS_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading preferences: {e}")
        
        # Return default preferences
        return {
            "last_repo_path": "",
            "product_key": "",
            "propagator": {
                "max_commits": 50,
                "auto_push": False
            },
            "cleanup": {
                "default_prefix": "feature/",
                "default_days": 30,
                "delete_scope": "both"
            },
            "pr_creator": {
                "default_target": "main"
            }
        }
    
    @staticmethod
    def save_preferences(prefs):
        """Save user preferences to config file."""
        Config._CONFIG_DIR.mkdir(exist_ok=True)
        
        try:
            with open(Config._PREFS_FILE, 'w') as f:
                json.dump(prefs, f, indent=2)
        except Exception as e:
            print(f"Error saving preferences: {e}")
