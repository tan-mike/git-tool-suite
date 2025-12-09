
import os
import sys
import json
from pathlib import Path

# Mock Config class to test logic without importing the actual app which might trigger UI
class MockConfig:
    _KEY_PART1 = "PLACEHOLDER" # Simulate bundled key missing/placeholder
    IS_LIMITED_BUILD = False
    APP_VERSION = "3.1"
    
    @staticmethod
    def get_api_key(env_key=None, user_key=None):
        # Priority 1: Env
        if env_key:
            return env_key
            
        # Priority 2: User Prefs
        if not MockConfig.IS_LIMITED_BUILD and user_key:
            return user_key
            
        # Priority 3: Bundled
        return None

def verify_settings_logic():
    print("Verifying API Key Priority Logic...")
    
    # Case 1: Env Var present
    key = MockConfig.get_api_key(env_key="ENV_KEY", user_key="USER_KEY")
    if key == "ENV_KEY":
        print("SUCCESS: Env key takes priority.")
    else:
        print(f"FAILURE: Expected ENV_KEY, got {key}")
        sys.exit(1)
        
    # Case 2: User Key present (Env missing)
    key = MockConfig.get_api_key(env_key=None, user_key="USER_KEY")
    if key == "USER_KEY":
        print("SUCCESS: User key used when Env missing.")
    else:
        print(f"FAILURE: Expected USER_KEY, got {key}")
        sys.exit(1)
        
    # Case 3: Limited Build (User Key ignored)
    MockConfig.IS_LIMITED_BUILD = True
    key = MockConfig.get_api_key(env_key=None, user_key="USER_KEY")
    if key is None:
        print("SUCCESS: User key ignored in Limited Build.")
    else:
        print(f"FAILURE: Expected None in Limited Build, got {key}")
        sys.exit(1)
        
    print("\nVerifying Version Check Logic...")
    # Add parent dir to path to import utils
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.versioning import is_newer_version

    versions_to_test = [
        # Basic comparisons
        ("3.2.10", "3.2.8", True),
        ("3.2.8", "3.2.10", False),
        ("3.1.0", "3.0.1", True),
        ("3.0.1", "3.1.0", False),
        ("4.0.0", "3.9.9", True),
        ("3.9.9", "4.0.0", False),
        ("3.2.8", "3.2.8", False),

        # Whitespace handling
        (" 1.2.3 ", "1.2.3", False),
        ("1.2.4", " 1.2.3 ", True),

        # Leading 'v' handling
        ("v1.2.3", "1.2.3", False),
        ("v1.2.4", "1.2.3", True),
        ("1.2.4", "v1.2.3", True),

        # Pre-release / build metadata handling
        ("1.2.3-alpha", "1.2.3", False),
        ("1.2.3", "1.2.3-alpha", False),
        ("1.2.4", "1.2.3-alpha", True),
        ("1.2.3+build.1", "1.2.3", False),
        ("1.2.3", "1.2.3+build.1", False),
        ("1.2.4-rc1", "1.2.4-rc0", False), # Note: pre-release ignored

        # Padding / component length
        ("1.0.0", "1.0", False),
        ("1.0", "1.0.0", False),
        ("2.0", "1.9.9", True),
    ]

    for v1, v2, expected in versions_to_test:
        result = is_newer_version(v1, v2)
        if result == expected:
            print(f"SUCCESS: is_newer_version('{v1}', '{v2}') returned {result} as expected.")
        else:
            print(f"FAILURE: is_newer_version('{v1}', '{v2}') returned {result}, but expected {expected}.")
            sys.exit(1)

    # Test invalid inputs
    invalid_inputs = [("3.2.a", "3.2.8"), (None, "3.2.8"), ("3.2.8", "")]
    for v1, v2 in invalid_inputs:
        result = is_newer_version(v1, v2)
        if result is False:
            print(f"SUCCESS: is_newer_version('{v1}', '{v2}') correctly returned False for invalid input.")
        else:
            print(f"FAILURE: is_newer_version('{v1}', '{v2}') returned {result}, but expected False for invalid input.")
            sys.exit(1)

if __name__ == "__main__":
    try:
        verify_settings_logic()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
