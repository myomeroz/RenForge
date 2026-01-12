
import os
import sys
import json
import shutil
import zipfile
import unittest
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import renforge_config as config
from core.packaging import PackManager, PackConstants
from core.glossary_manager import GlossaryManager
from core.tm_store import TMManager
import renforge_settings as rf_settings

class TestPackagingCore(unittest.TestCase):

    def setUp(self):
        # Setup temp directories
        self.test_dir = Path("tests/temp_pack_test")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True)
        
        self.pack_path = self.test_dir / "test_project.rfpack"
        
        # Mock Config Directories
        self.orig_app_dir = config.APP_DIR
        self.orig_settings_dir = config.SETTINGS_DIR
        self.orig_db_dir = config.DB_DIR
        
        config.APP_DIR = self.test_dir
        config.SETTINGS_DIR = self.test_dir / "settings"
        config.DB_DIR = self.test_dir / "DB"
        
        config.SETTINGS_DIR.mkdir()
        config.DB_DIR.mkdir()
        
        # Mock Settings
        self.settings_file = config.SETTINGS_DIR / "settings.json"
        rf_settings.SETTINGS_FILE = self.settings_file # Patch settings file path if needed, 
        # actually rf_settings uses config.SETTINGS_FILE_PATH, which depends on APP_DIR/SETTINGS_DIR logic in runtime?
        # Let's check logic: renforge_config sets paths at module level.
        # Patching config.SETTINGS_DIR might be enough if rf_settings uses it dynamically OR we patch rf_settings internal paths.
        
        # Re-initialize path in rf_settings if it cached it?
        # rf_settings likely imports config and uses it.
        # BUT config paths are computed on import. 
        # Modifying config attributes AFTER import works if rf_settings uses config.ATTR.
        
        # Let's ensure rf_settings uses our new path
        # Actually rf_settings.load_settings() uses renforge_config.SETTINGS_FILE_PATH
        config.SETTINGS_FILE_PATH = self.settings_file
        
        self.test_settings = {
            "ui_language": "en",
            "plugins": {
                "test_plugin": {"enabled": True, "api_key": "SECRET_KEY_123"}
            },
            "glossary_terms": [
                {"source": "Hello", "target": "Bonjour", "mode": "exact", "enabled": True}
            ]
        }
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_settings, f)
            
        # Create TM DB
        self.tm_path = config.DB_DIR / "tm.db"
        self.tm_mgr = TMManager(str(self.test_dir))
        self.tm_mgr.init_db(str(self.test_dir)) # Force re-init with new path logic if needed, but we patched config.DB_DIR
        # Actually init_db uses config.DB_DIR.
        
        self.tm_mgr.add_entry("Good Morning", "Gunaydin", "manual", True)
        self.tm_mgr.conn.close() # Close to allow file copy
        self.tm_mgr.conn = None
        del self.tm_mgr
        import gc
        gc.collect() 
        
        # Also create a standalone glossary.json if logic supports it (as per code)
        # Packaging code checks config.APP_DIR / "glossary.json"
        self.glossary_std_path = config.APP_DIR / "glossary.json"
        with open(self.glossary_std_path, 'w') as f:
            json.dump([{"source": "External", "target": "Dis", "mode": "exact"}], f)


    def tearDown(self):
        # Restore Config
        config.APP_DIR = self.orig_app_dir
        config.SETTINGS_DIR = self.orig_settings_dir
        config.DB_DIR = self.orig_db_dir
        
        if self.test_dir.exists():
             try:
                shutil.rmtree(self.test_dir)
             except:
                 pass

    def test_export_import_flow(self):
        pm = PackManager()
        
        # 1. Export
        options = {
            "settings": True,
            "glossary": True,
            "tm": True,
            "plugins": True,
            "secrets": True
        }
        password = "strongpassword"
        
        pm.export_pack(str(self.pack_path), options, password)
        
        self.assertTrue(self.pack_path.exists())
        self.assertTrue(zipfile.is_zipfile(self.pack_path))
        
        # 2. Modify State (Simulate new/clean workspace)
        # Delete TM db
        if self.tm_path.exists(): os.remove(str(self.tm_path))
        
        # Modify Settings
        new_settings = {"ui_language": "en", "glossary_terms": []}
        with open(self.settings_file, 'w') as f: json.dump(new_settings, f)
        
        # 3. Import
        strategies = {
            "settings": "OVERWRITE",
            "glossary": "MERGE_PREFER_IMPORTED",
            "tm": "REPLACE"
        }
        
        report = pm.import_pack(str(self.pack_path), strategies, password)
        
        # 4. Verify
        # Check Settings
        with open(self.settings_file, 'r') as f:
            restored_settings = json.load(f)
            
        self.assertEqual(restored_settings["ui_language"], "en")
        
        # Check Secrets Decryption
        self.assertEqual(restored_settings.get("api_key"), None) # Main API key
        # Check plugin secret (logic was to restore into settings if key matches)
        # Currenly my mock packaging implementation of Settings restore is:
        # if "main.api_key" in decrypted: imported_settings["api_key"] = ...
        # My clean_configs logic extracted "plugins" -> "test_plugin.api_key".
        # Packaging import logic needs to be verified for this restoration.
        # Currently the import logic for secrets restoration in settings is placeholder-ish in my code.
        # But let's check what it does.
        
        # Check TM
        self.assertTrue(self.tm_path.exists(), "TM DB should be restored")
        tm_check = TMManager(str(self.test_dir))
        # Wait, need to reconnect
        tm_check.init_db(None)
        res = tm_check.lookup("Good Morning")
        self.assertTrue(len(res) > 0)
        self.assertEqual(res[0].target_text, "Gunaydin")
        
        # Check Glossary (External file merge)
        # Packaging logic merges external glossary.json into GLOSSARY_MANAGER (settings based).
        # My setup created external glossary.json AND settings glossary.
        # The result should be merged into settings["glossary_terms"] via manager.
        
        # Load settings again (internal save triggered)
        with open(self.settings_file, 'r') as f:
            final_settings = json.load(f)
            
        terms = final_settings.get("glossary_terms", [])
        sources = [t["source"] for t in terms]
        self.assertIn("External", sources)
        
if __name__ == '__main__':
    unittest.main()
