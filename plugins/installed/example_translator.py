# -*- coding: utf-8 -*-
"""
Example Translator Plugin

Demonstrates how to create a custom translator plugin for RenForge.
This example shows integration with a hypothetical translation API.
"""

from typing import Optional, List, Dict, Any

from plugins.base import TranslatorPlugin, PluginInfo, PluginType


class ExampleTranslatorPlugin(TranslatorPlugin):
    """
    Example translator plugin.
    
    This plugin demonstrates the structure of a translator plugin.
    Replace the translate() method with actual API calls.
    """
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="example_translator",
            name="Example Translator",
            version="1.0.0",
            description="Example translator plugin demonstrating the plugin API",
            author="RenForge Team",
            plugin_type=PluginType.TRANSLATOR,
            config_schema={
                "api_key": {"type": "string", "required": True},
                "endpoint": {"type": "string", "default": "https://api.example.com"},
            }
        )
    
    def activate(self):
        """Initialize the translator."""
        super().activate()
        # Validate configuration
        if not self._config.get("api_key"):
            print("Warning: No API key configured for ExampleTranslator")
    
    def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> Optional[str]:
        """
        Translate text using the example API.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translated text, or None on failure
        """
        # This is a placeholder implementation
        # Replace with actual API calls
        
        api_key = self._config.get("api_key")
        endpoint = self._config.get("endpoint", "https://api.example.com")
        
        if not api_key:
            return None
        
        # Simulated translation (replace with actual API call)
        # import requests
        # response = requests.post(
        #     f"{endpoint}/translate",
        #     json={"text": text, "source": source_lang, "target": target_lang},
        #     headers={"Authorization": f"Bearer {api_key}"}
        # )
        # return response.json().get("translation")
        
        # For demo purposes, just return the original text with a marker
        return f"[EXAMPLE:{target_lang}] {text}"
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        return [
            "en", "tr", "de", "fr", "es", "it", "pt", "ru", 
            "zh", "ja", "ko", "ar", "nl", "pl", "sv"
        ]


# This allows the plugin to be discovered by PluginLoader
__plugin__ = ExampleTranslatorPlugin
