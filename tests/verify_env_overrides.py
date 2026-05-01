import unittest
from pathlib import Path
import tempfile
import shutil

# Assuming apply_env_overrides is defined at the top level of apps.worktree
from apps.worktree import apply_env_overrides

class TestEnvOverrides(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.env_file = self.test_dir / ".env"
        self.env_file.write_text("APP_PORT=8000\nDB_DATABASE=old_db\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_apply_env_overrides(self):
        overrides = [
            "APP_PORT=8001",
            "DB_DATABASE=app_${branch}",
            "NEW_KEY=test"
        ]
        
        apply_env_overrides(self.env_file, "feature-123", overrides)
        
        content = self.env_file.read_text()
        self.assertIn("APP_PORT=8001", content)
        self.assertIn("DB_DATABASE=app_feature-123", content)
        self.assertIn("NEW_KEY=test", content)
        self.assertNotIn("APP_PORT=8000", content)
        self.assertNotIn("DB_DATABASE=old_db", content)

if __name__ == "__main__":
    unittest.main()
