"""
Configuration management for Git Tool Suite.
Handles API key storage (bundled) and user preferences.
"""

import base64
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
    APP_VERSION = "3.2.2"
    IS_LIMITED_BUILD = True # Set to True for builds without API key setup
    UPDATE_CHECK_URL = "https://gist.githubusercontent.com/tan-mike/37c92fd3e04d4663fc70948567ec932d/raw/version.json"

    @staticmethod
    def get_api_key():
        """
        Returns the API key with the following priority:
        1. .env file (GEMINI_API_KEY) - for development
        2. User Preferences (if allowed)
        3. Bundled obfuscated key - for production builds
        """
        # Priority 1: Read from .env file (development)
        env_key = os.getenv('GEMINI_API_KEY')
        if env_key:
            return env_key
            
        # Priority 2: User Preferences (if not limited build)
        if not Config.IS_LIMITED_BUILD:
            prefs = Config.load_preferences()
            user_key = prefs.get('api_key')
            if user_key:
                return user_key
        
        # Priority 3: Use bundled obfuscated key (production)
        # Check if placeholder (not yet obfuscated)
        if "PLACEHOLDER" in Config._KEY_PART1:
            return None
        
        # Decode bundled key
        return Config._decode_bundled_key()
    
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
