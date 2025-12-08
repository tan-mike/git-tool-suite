
import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the function to be tested
# We need to import check_for_dependency from main, but since it's not exported, we might need a different approach
# However, we added cleanup_old_versions to main.py, let's try to import it
from main import cleanup_old_versions

class TestCleanup(unittest.TestCase):
    def setUp(self):
        # Create a dummy .exe.old file
        self.test_file = Path("test_cleanup_logic.exe.old")
        self.test_file.touch()

    def tearDown(self):
        # Ensure cleanup if test fails
        if self.test_file.exists():
            self.test_file.unlink()

    def test_cleanup_function(self):
        # Ensure file exists before test
        self.assertTrue(self.test_file.exists())
        
        # Run cleanup
        # We need to mock sys.executable or __file__ depending on how the function determines path
        # The function uses __file__ if not frozen. Since we are running valid python, __file__ works.
        # But verify_cleanup_logic.py is in tests/, checking parent of main.py
        # Wait, the function checks the parent of ITSELF (main.py)
        # So it will look in the directory where main.py resides.
        # We need to place our test file in the SAME directory as main.py for the test to work without mocking too much.
        
        # Move test file to app root
        app_dir = Path(__file__).parent.parent 
        target_file = app_dir / "test_cleanup_logic.exe.old"
        if self.test_file.exists():
             # Move current test file to target location
             self.test_file.rename(target_file)
        
        self.assertTrue(target_file.exists(), f"File {target_file} should exist")
        
        # Run cleanup
        cleanup_old_versions()
        
        # Verify file is gone
        self.assertFalse(target_file.exists(), f"File {target_file} should have been deleted")

if __name__ == '__main__':
    unittest.main()
