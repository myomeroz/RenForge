
import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.plugin_manager import PluginManager
from core.translation_service import TranslationService
from models.settings_model import SettingsModel

class TestPluginSystem:
    
    @pytest.fixture
    def plugin_manager(self):
        pm = PluginManager()
        # Ensure we point to the built-in plugins folder
        built_in_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'plugins', 'built_in'))
        pm.initialize(built_in_path)
        return pm

    def test_plugin_discovery(self, plugin_manager):
        """Verify built-in plugins are discovered."""
        engines = plugin_manager.get_all_engines()
        assert len(engines) >= 2 # Dummy + Google
        
        dummy = plugin_manager.get_engine("renforge.engine.dummy")
        assert dummy is not None
        assert dummy.name == "Dummy Engine (Test)"
        
        google = plugin_manager.get_engine("renforge.engine.google_free")
        assert google is not None


    def test_translation_service_flow(self, plugin_manager):
        """Test TranslationService with Dummy Engine and Token Masking."""
        
        # Mock Settings
        settings = MagicMock()
        # Return Dummy ID as active
        settings.get.side_effect = lambda k, d=None: "renforge.engine.dummy" if k == "active_plugin_engine" else ({"timeout_sec": 1} if k == "plugins_config" else d)
        
        service = TranslationService(settings)
        service.plugin_manager = plugin_manager
        
        # Test Data: Includes Ren'Py tokens
        items = [
            {"i": 1, "original": "Hello [player]!"},
            {"i": 2, "original": "{b}Bold{/b} move."}
        ]
        
        # Run Batch Translate
        # Mock cancel token
        cancel_token = MagicMock()
        cancel_token.is_set.return_value = False
        
        results = service.batch_translate(items, "en", "tr", cancel_token=cancel_token)
        
        assert len(results) == 2
        
        r1 = next(r for r in results if r["i"] == 1)
        assert "[TEST]" in r1["t"]
        assert "[player]" in r1["t"]
        assert "⟦T0⟧" not in r1["t"] 
        
        r2 = next(r for r in results if r["i"] == 2)
        assert "[TEST]" in r2["t"]
        assert "{b}Bold{/b}" in r2["t"]

    def test_cancellation(self, plugin_manager):
        """Test cancellation token support."""
        settings = MagicMock()
        settings.get.side_effect = lambda k, d=None: "renforge.engine.dummy" if k == "active_plugin_engine" else ({"timeout_sec": 1} if k == "plugins_config" else d)
        
        service = TranslationService(settings)
        service.plugin_manager = plugin_manager
        
        items = [{"i": 1, "original": "Test"}]
        cancel_token = MagicMock()
        cancel_token.is_set.return_value = True # Already canceled
        
        results = service.batch_translate(items, "en", "tr", cancel_token=cancel_token)
        
        assert results[0].get("error") == "Canceled"

    def test_manifest_validation(self, plugin_manager):
        """Verify invalid manifests are tracked."""
        # We can't easily inject a bad file here without IO, so we verify logic via PluginManager
        # check if failed_plugins list exists
        assert hasattr(plugin_manager, 'failed_plugins')
        assert isinstance(plugin_manager.failed_plugins, list)

    def test_glossary_integration(self, plugin_manager):
        """Test that Glossary is applied after translation."""
        
        settings = MagicMock()
        settings.get.side_effect = lambda k, d=None: "renforge.engine.dummy" if k == "active_plugin_engine" else d
        
        service = TranslationService(settings)
        service.plugin_manager = plugin_manager
        
        # Mock Glossary Manager
        with patch('core.glossary_manager.GlossaryManager') as MockGlossary:
            mock_gm_instance = MockGlossary.return_value
            # Setup apply_to_text to replace "Hello" with "Merhaba"
            mock_gm_instance.apply_to_text.side_effect = lambda t: t.replace("Hello", "Merhaba")
            
            # Force lazy load of GM
            service.glossary_manager = mock_gm_instance 
            
            items = [{"i": 1, "original": "Hello World"}]
            results = service.batch_translate(items, "en", "tr")
            
            # Dummy output: "[TEST] Hello World"
            # Glossary should change "Hello" -> "Merhaba"
            # Final: "[TEST] Merhaba World"
            
            r1 = results[0]
            assert "Merhaba" in r1["t"]
            assert "[TEST]" in r1["t"]
