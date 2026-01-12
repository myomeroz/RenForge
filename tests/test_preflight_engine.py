
import os
import sys
import unittest
from pathlib import Path
import shutil

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import renforge_config as config
from core.preflight_engine import PreflightEngine, PreflightIssue

class TestPreflightEngine(unittest.TestCase):

    def setUp(self):
        # Setup temp test directory
        self.test_dir = Path("tests/temp_preflight_test")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True)
        
        # Mock Config APP_DIR
        self.orig_app_dir = config.APP_DIR
        config.APP_DIR = self.test_dir
        
        self.engine = PreflightEngine()

    def tearDown(self):
        config.APP_DIR = self.orig_app_dir
        if self.test_dir.exists():
            try:
                shutil.rmtree(self.test_dir)
            except:
                pass
                
    def create_rpy_file(self, name, content):
        with open(self.test_dir / name, 'w', encoding='utf-8') as f:
            f.write(content)

    def test_scan_no_issues(self):
        content = """
translate turkish start_123:
    # "Hello"
    "Merhaba"
"""
        self.create_rpy_file("clean.rpy", content)
        
        issues = self.engine.run_scan()
        if len(issues) > 0:
            with open("tests/preflight_error.log", "w") as f:
                f.write(str([i.message for i in issues]))
        self.assertEqual(len(issues), 0)

    def test_missing_token(self):
        content = """
translate turkish start_123:
    # "Hello [player]"
    "Merhaba"
"""
        self.create_rpy_file("missing_token.rpy", content)
        
        issues = self.engine.run_scan()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].rule, "missing_token")
        self.assertIn("[player]", issues[0].message)

    def test_markup_mismatch(self):
        # Case 1: Unclosed tag
        content = """
translate turkish start_123:
    # "Bold text"
    "{b}Kalin"
"""
        self.create_rpy_file("markup.rpy", content)
        
        issues = self.engine.run_scan()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].rule, "markup_mismatch")
        
    def test_empty_translation(self):
        # NOTE: RPYParser might parse empty string as "" or skip? 
        # Standard parser usually handles translate blocks.
        content = """
translate turkish start_123:
    # "Hello"
    ""
"""
        self.create_rpy_file("empty.rpy", content)
        
        issues = self.engine.run_scan()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].rule, "empty_translation")

    def test_identical_check(self):
        content = """
translate turkish start_123:
    # "This is a long sentence."
    "This is a long sentence."
"""
        self.create_rpy_file("identical.rpy", content)
        
        issues = self.engine.run_scan()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "warning")
        self.assertEqual(issues[0].rule, "identical")

if __name__ == '__main__':
    unittest.main()
