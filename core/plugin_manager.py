
import os
import sys
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Type
from renforge_logger import get_logger
from interfaces.i_plugin import IPlugin, ITranslationEngine, PluginType

logger = get_logger("core.plugin_manager")

class PluginManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PluginManager, cls).__new__(cls)
            cls._instance.plugins = {} # id -> instance
            cls._instance.engines = {} # id -> instance
            cls._instance.failed_plugins = [] # List[Dict]
            cls._instance._initialized = False
        return cls._instance

    def initialize(self, built_in_path: str = None):
        if self._initialized:
            return

        self.plugins.clear()
        self.engines.clear()
        self.failed_plugins.clear()
        
        # Paths to scan
        paths = []
        if built_in_path:
             paths.append(built_in_path)
             
        # Add default built-in path "plugins/built_in" relative to app root
        # Assuming run from root
        default_builtin = Path("plugins") / "built_in"
        if default_builtin.exists():
            paths.append(str(default_builtin))

        for p in paths:
            self._scan_directory(p)

        self._initialized = True
        logger.info(f"PluginManager initialized. Loaded {len(self.plugins)} plugins.")
    def _scan_directory(self, path: str):
        path_obj = Path(path)
        if not path_obj.exists():
            return

        logger.debug(f"Scanning for plugins in: {path_obj}")
        
        # Add to sys.path to allow imports if needed
        if path not in sys.path:
            sys.path.append(path)

        for item in path_obj.iterdir():
            if item.is_dir():
                manifest_path = item / "manifest.json"
                if manifest_path.exists():
                    self._load_from_manifest(manifest_path, item)

    def _load_from_manifest(self, manifest_path: Path, plugin_dir: Path):
        try:
            import json
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
                
            # Validation
            if "id" not in manifest or "entrypoint" not in manifest:
                err = f"Invalid manifest in {plugin_dir.name}: Missing 'id' or 'entrypoint'."
                logger.error(err)
                self.failed_plugins.append({"name": plugin_dir.name, "error": err, "path": str(plugin_dir)})
                return

            api_ver = manifest.get("api_version", 0)
            from interfaces.i_plugin import RENFORGE_PLUGIN_API_VERSION
            if api_ver > RENFORGE_PLUGIN_API_VERSION:
                err = f"Plugin {manifest['id']} requires newer API version ({api_ver}). Current: {RENFORGE_PLUGIN_API_VERSION}"
                logger.error(err)
                self.failed_plugins.append({"name": plugin_dir.name, "error": err, "path": str(plugin_dir)})
                return # Block incompatible

            # Load Module
            entry_str = manifest["entrypoint"] # "module.py:ClassName" or "module:ClassName"
            if ":" not in entry_str:
                err = f"Invalid entrypoint format in {manifest['id']}: {entry_str}"
                logger.error(err)
                self.failed_plugins.append({"name": plugin_dir.name, "error": err, "path": str(plugin_dir)})
                return
                
            mod_name, class_name = entry_str.split(":")
            if mod_name.endswith(".py"): mod_name = mod_name[:-3]
            
            # Add plugin dir to sys.path temporarily to load module
            # Ideally we use importlib machinery to avoid polluting sys.path too much
            # But simple approach:
            
            spec = importlib.util.spec_from_file_location(f"{manifest['id']}_mod", plugin_dir / f"{mod_name}.py")
            if not spec or not spec.loader:
                logger.error(f"Could not load module {mod_name} for plugin {manifest['id']}")
                return
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if not hasattr(module, class_name):
                 logger.error(f"Class {class_name} not found in module {mod_name} for plugin {manifest['id']}")
                 return
                 
            cls = getattr(module, class_name)
            
            # Instantiate
            plugin = cls()
            plugin.manifest = manifest # Inject manifest data
            self._register_plugin(plugin)
            
        except Exception as e:
            err = f"Failed to load plugin from {plugin_dir.name}: {e}"
            logger.error(err)
            self.failed_plugins.append({"name": plugin_dir.name, "error": str(e), "path": str(plugin_dir)})

    def _register_plugin(self, plugin: IPlugin):
        if plugin.id in self.plugins:
            logger.warning(f"Plugin ID collision: {plugin.id}. Ignoring duplicate.")
            return

        logger.info(f"Registering plugin: {plugin.name} ({plugin.version})")
        plugin.on_load(context=None) # TODO: Pass real context
        
        self.plugins[plugin.id] = plugin
        if isinstance(plugin, ITranslationEngine):
            self.engines[plugin.id] = plugin

    def get_engine(self, engine_id: str) -> Optional[ITranslationEngine]:
        return self.engines.get(engine_id)

    def get_all_engines(self) -> List[ITranslationEngine]:
        return list(self.engines.values())

    def get_plugin(self, plugin_id: str) -> Optional[IPlugin]:
        return self.plugins.get(plugin_id)
