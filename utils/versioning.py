"""
Versioning utilities for comparing semantic version strings.
"""

def is_newer_version(version1, version2):
    """
    Compares two semantic version strings (e.g., "3.2.10" vs "3.2.8").
    Returns True if version1 is strictly newer than version2.
    """
    if not version1 or not version2:
        return False

    try:
        v1_parts = list(map(int, version1.split('.')))
        v2_parts = list(map(int, version2.split('.')))
    except (ValueError, AttributeError):
        # Handle cases where version strings are not in the expected format
        return False

    # Pad the shorter version list with zeros for comparison
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (max_len - len(v1_parts)))
    v2_parts.extend([0] * (max_len - len(v2_parts)))

    return v1_parts > v2_parts
