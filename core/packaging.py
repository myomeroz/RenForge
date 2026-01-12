
import os
import sys
import json
import shutil
import zipfile
import time
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Generator

from renforge_logger import get_logger
import renforge_config as config

logger = get_logger("core.packaging")

# Check for cryptography availability for secure secrets
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    logger.warning("Cryptography library not found. Secure export of secrets will be disabled.")


class PackConstants:
    EXTENSION = ".rfpack"
    META_FILE = "meta.json"
    SETTINGS_FILE = "settings.json"
    GLOSSARY_FILE = "glossary.json"
    QA_FILE = "qa_rules.json"  # If we split it later
    PLUGINS_DIR = "plugins"
    PLUGINS_CONFIG_FILE = "config.json"
    SECRETS_FILE = "secrets.enc"
    MANIFESTS_DIR = "manifests"
    TM_DIR = "tm"
    TM_DB_FILE = "tm.db"
    HISTORY_DIR = "history"
    CHANGELOG_FILE = "changelog.jsonl"
    
    VERSION = 1


class PackManager:
    """
    Manages Export and Import of RenForge Project Packs (.rfpack).
    """
    
    def __init__(self):
        self.temp_dir = config.APP_DIR / "temp" / "pack_staging"
        
    def export_pack(self, 
                    output_path: str,
                    include_options: Dict[str, bool],
                    password: str = None) -> bool:
        """
        Export current workspace to a .rfpack file.
        
        Args:
            output_path: Destination path (.rfpack or .zip)
            include_options: {
                "settings": bool,
                "glossary": bool,
                "tm": bool,
                "history": bool,
                "plugins": bool,
                "secrets": bool
            }
            password: Password for encrypting secrets (required if secrets=True)
            
        Returns:
            True if successful.
        """
        try:
            timestamp = datetime.datetime.now().isoformat()
            meta = {
                "format_version": PackConstants.VERSION,
                "created_at": timestamp,
                "app_version": "0.3.10", # Todo: Get from config
                "contents": []
            }
            
            # Prepare staging
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            
            plugins_dir = self.temp_dir / PackConstants.PLUGINS_DIR
            plugins_dir.mkdir(exist_ok=True)
            
            # 1. Settings
            if include_options.get("settings", True):
                self._export_settings(self.temp_dir / PackConstants.SETTINGS_FILE, include_options.get("secrets", False))
                meta["contents"].append("settings")
                
            # 2. Glossary
            if include_options.get("glossary", True):
                # Assume glossary is a single JSON for now or handled via manager
                # For now, just dumping the expected file if it exists
                # TODO: Integrate with GlossaryManager export
                glossary_path = config.APP_DIR / "glossary.json" # Or wherever it lives
                if glossary_path.exists():
                     shutil.copy2(glossary_path, self.temp_dir / PackConstants.GLOSSARY_FILE)
                     meta["contents"].append("glossary")
            
            # 3. TM (Optional - heavy)
            if include_options.get("tm", False):
                tm_dir = self.temp_dir / PackConstants.TM_DIR
                tm_dir.mkdir(exist_ok=True)
                src_tm = config.DB_DIR / "tm.db"
                if src_tm.exists():
                    # Must close DB connection logic? SQLite usually safe to copy if WAL 
                    # But ideally we should checkpoint. For now simple copy.
                    shutil.copy2(src_tm, tm_dir / PackConstants.TM_DB_FILE)
                    meta["contents"].append("tm")
            
            # 4. Plugins
            if include_options.get("plugins", True):
                self._export_plugins(plugins_dir, include_options.get("secrets", False), password)
                meta["contents"].append("plugins")

            # 5. History
            if include_options.get("history", False):
                hist_dir = self.temp_dir / PackConstants.HISTORY_DIR
                hist_dir.mkdir(exist_ok=True)
                # TODO: Copy ChangeLog
                meta["contents"].append("history")

            # Write Meta
            with open(self.temp_dir / PackConstants.META_FILE, 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=4)
                
            # Zip it up
            self._create_zip(self.temp_dir, output_path)
            logger.info(f"Pack exported successfully to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise
        finally:
            if self.temp_dir.exists():
                 pass # Cleanup? Or keep for debug?
                 shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_zip(self, source_dir: Path, output_path: str):
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)

    def _export_settings(self, dest_path: Path, include_secrets: bool):
        # Load current settings from disk
        import renforge_settings
        settings = renforge_settings.load_settings()
        
        if not include_secrets:
            # Strip secrets
            settings.pop("api_key", None)
            # Add more secret keys here if any
            
        with open(dest_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)

    def _export_plugins(self, dest_dir: Path, include_secrets: bool, password: str):
        # Gather plugin configs
        # Assuming plugin configs are in settings["plugins"] for now or separate files
        # We will iterate known plugins from PluginManager to find saved configs?
        # Actually simplest is to export the "plugins" section of settings.json separate if needed,
        # or just rely on settings.json export.
        # BUT the requirement says "/plugins/config.json".
        
        # Let's check if there is a plugins folder in settings? 
        # Or usually plugins store data in `SETTINGS_DIR`/plugins?
        # If not, let's assume we extract "plugins" key from settings.json and save it here.
        
        import renforge_settings
        settings = renforge_settings.load_settings()
        plugin_configs = settings.get("plugins", {})
        
        # Split secrets if needed
        clean_configs = {}
        secrets = {}
        
        for p_id, p_conf in plugin_configs.items():
            clean_configs[p_id] = p_conf.copy()
            # Known secret keys - TODO: Plugin should define what is secret
            # For now, hardcode "api_key"
            if "api_key" in clean_configs[p_id]:
                val = clean_configs[p_id].pop("api_key")
                secrets[f"{p_id}.api_key"] = val
                
        # Write clean config
        with open(dest_dir / PackConstants.PLUGINS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(clean_configs, f, indent=4)
            
        # Encrypt secrets if requested
        if include_secrets and password and HAS_CRYPTO and secrets:
            try:
                self._encrypt_secrets(secrets, password, dest_dir / PackConstants.SECRETS_FILE)
            except Exception as e:
                logger.error(f"Encryption failed: {e}")
                
    def _encrypt_secrets(self, secrets_dict: Dict, password: str, output_path: Path):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
        import os
        import base64
        
        # Derive key
        salt = os.urandom(16)
        kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
        key = kdf.derive(password.encode())
        
        # Encrypt
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        data = json.dumps(secrets_dict).encode()
        ct = aesgcm.encrypt(nonce, data, None)
        
        # Save format: version|salt|nonce|ciphertext (all base64 encoded)
        # Version 1
        blob = {
            "v": 1,
            "s": base64.b64encode(salt).decode('ascii'),
            "n": base64.b64encode(nonce).decode('ascii'),
            "c": base64.b64encode(ct).decode('ascii')
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(blob, f)

    def _decrypt_secrets(self, file_path: Path, password: str) -> Dict:
        if not HAS_CRYPTO:
            logger.error("Cannot decrypt secrets: cryptography library missing.")
            return {}
            
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
        import base64
        
        with open(file_path, 'r', encoding='utf-8') as f:
            blob = json.load(f)
            
        if blob.get("v") != 1:
            raise ValueError("Unknown secret format version")
            
        salt = base64.b64decode(blob["s"])
        nonce = base64.b64decode(blob["n"])
        ct = base64.b64decode(blob["c"])
        
        kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
        key = kdf.derive(password.encode())
        
        aesgcm = AESGCM(key)
        pt = aesgcm.decrypt(nonce, ct, None)
        return json.loads(pt.decode('utf-8'))

    # --- IMPORT LOGIC ---
    
    def inspect_pack(self, pack_path: str) -> Dict[str, Any]:
        """
        Read meta.json from a pack without extracting everything.
        """
        if not zipfile.is_zipfile(pack_path):
            raise ValueError("Not a valid zip file")
            
        with zipfile.ZipFile(pack_path, 'r') as zipf:
            try:
                with zipf.open(PackConstants.META_FILE) as f:
                    meta = json.load(f)
                    return meta
            except KeyError:
                raise ValueError("Valid .rfpack must contain meta.json")

    def import_pack(self, 
                   pack_path: str, 
                   strategies: Dict[str, str],
                   password: str = None) -> List[str]:
        """
        Import a pack using defined strategies.
        Returns a report of actions taken.
        """
        report = []
        
        # Prepare staging
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
            
        try:
            with zipfile.ZipFile(pack_path, 'r') as zipf:
                 zipf.extractall(self.temp_dir)
                 
            # 1. Recover Secrets (if any)
            secrets_path = self.temp_dir / PackConstants.PLUGINS_DIR / PackConstants.SECRETS_FILE
            decrypted_secrets = {}
            if secrets_path.exists():
                if password:
                    try:
                        decrypted_secrets = self._decrypt_secrets(secrets_path, password)
                        report.append("Secrets decrypted successfully.")
                    except Exception as e:
                        report.append(f"ERROR: Failed to decrypt secrets: {e}")
                else:
                    report.append("Secrets found but no password provided - skipped.")

            # 2. Merge Settings
            settings_strategy = strategies.get("settings", "SKIP") # SKIP, OVERWRITE
            if settings_strategy == "OVERWRITE":
                src = self.temp_dir / PackConstants.SETTINGS_FILE
                if src.exists():
                    import renforge_settings
                    with open(src, 'r', encoding='utf-8') as f:
                        imported_settings = json.load(f)
                    
                    # Merge restored secrets back into settings structure if needed
                    # Assumes secrets key "plugin_id.api_key" maps to structure
                    # Logic to re-inject secrets not fully implemented yet for complex structures
                    # But for simple top-level api_key:
                    if "main.api_key" in decrypted_secrets: # Example key
                         imported_settings["api_key"] = decrypted_secrets["main.api_key"]

                    renforge_settings.save_settings(imported_settings)
                    report.append("Settings overwritten from pack.")

            # 3. Merge Glossary
            glossary_strategy = strategies.get("glossary", "SKIP")
            if glossary_strategy != "SKIP":
                src = self.temp_dir / PackConstants.GLOSSARY_FILE
                if src.exists():
                    # Call glossary manager merge
                    try:
                        from core.glossary_manager import GlossaryManager
                        
                        with open(src, 'r', encoding='utf-8') as gf:
                            imported_data = json.load(gf)
                            # Handle structure variations if any (list or dict with 'terms')
                            terms = imported_data if isinstance(imported_data, list) else imported_data.get("terms", [])
                            
                            gm = GlossaryManager()
                            gm.merge_glossary(terms, strategy=glossary_strategy)
                            report.append(f"Glossary merged (Strategy: {glossary_strategy})")
                    except Exception as ge:
                        report.append(f"ERROR: Glossary merge failed: {ge}")

            # 4. Merge TM
            tm_strategy = strategies.get("tm", "SKIP")
            if tm_strategy != "SKIP":
                 src_tm = self.temp_dir / PackConstants.TM_DIR / PackConstants.TM_DB_FILE
                 if src_tm.exists():
                     if tm_strategy == "REPLACE":
                         dest = config.DB_DIR / "tm.db"
                         shutil.copy2(src_tm, dest)
                         report.append("TM Database replaced.")
                     elif tm_strategy == "MERGE":
                         # Call TM merge
                         from core.tm_store import get_tm_manager
                         tm = get_tm_manager() # Use global instance
                         count = tm.import_from_db(str(src_tm))
                         report.append(f"Merged {count} entries into TM.")

            return report
            
        finally:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)


