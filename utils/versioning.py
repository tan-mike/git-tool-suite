"""
Versioning utilities for comparing semantic version strings.
"""
import sys

def is_newer_version(version1, version2):
    """
    Compares two semantic version strings (e.g., "v3.2.10" vs "3.2.8-alpha").
    Returns True if version1 is strictly newer than version2.

    Handles:
    - Optional leading 'v'
    - Pre-release tags (e.g., -alpha, +build)
    - Whitespace
    - Differing numbers of version components (e.g., 1.0 vs 1.0.0)
    """
    if not version1 or not version2:
        return False

    try:
        # --- Pre-processing ---
        v1_clean = version1.strip().lstrip('v').split('-')[0].split('+')[0]
        v2_clean = version2.strip().lstrip('v').split('-')[0].split('+')[0]

        v1_parts = list(map(int, v1_clean.split('.')))
        v2_parts = list(map(int, v2_clean.split('.')))

    except (ValueError, AttributeError) as e:
        # Handle cases where version strings are not in the expected format
        print(f"Warning: Could not parse version string. Error: {e}. v1='{version1}', v2='{version2}'", file=sys.stderr)
        return False

    # Pad the shorter version list with zeros for comparison
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (max_len - len(v1_parts)))
    v2_parts.extend([0] * (max_len - len(v2_parts)))

    return v1_parts > v2_parts
