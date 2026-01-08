# -*- coding: utf-8 -*-
"""
Tests for AI Translation Utilities

Tests for batch translation token masking, validation, and first-character preservation.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTokenMasking:
    """Tests for Ren'Py token masking and unmasking."""
    
    def test_mask_basic_tags(self):
        """Test masking of basic formatting tags."""
        from renforge_ai import mask_renpy_tokens, unmask_renpy_tokens
        
        text = "This is {b}bold{/b} and {i}italic{/i} text."
        masked, token_map = mask_renpy_tokens(text)
        
        # Check that tokens are replaced with placeholders
        assert "{b}" not in masked
        assert "{/b}" not in masked
        assert "{i}" not in masked
        assert "{/i}" not in masked
        assert "⟦T" in masked
        
        # Check token map has all tokens
        assert len(token_map) == 4
        assert "{b}" in token_map.values()
        assert "{/b}" in token_map.values()
    
    def test_mask_variable_placeholders(self):
        """Test masking of variable placeholders like [name]."""
        from renforge_ai import mask_renpy_tokens, unmask_renpy_tokens
        
        text = "Hello [player], welcome to [location]!"
        masked, token_map = mask_renpy_tokens(text)
        
        assert "[player]" not in masked
        assert "[location]" not in masked
        assert len(token_map) == 2
    
    def test_mask_wait_pause_tags(self):
        """Test masking of {w}, {p}, {nw} tags."""
        from renforge_ai import mask_renpy_tokens
        
        text = "Wait here...{w} for a moment{p=1.0} and continue{nw}"
        masked, token_map = mask_renpy_tokens(text)
        
        assert "{w}" not in masked
        assert "{p=1.0}" not in masked
        assert "{nw}" not in masked
        assert len(token_map) == 3
    
    def test_mask_color_tags(self):
        """Test masking of color tags."""
        from renforge_ai import mask_renpy_tokens
        
        text = "This is {color=#ff0000}red{/color} text."
        masked, token_map = mask_renpy_tokens(text)
        
        assert "{color=#ff0000}" not in masked
        assert "{/color}" not in masked
        assert len(token_map) == 2
    
    def test_unmask_roundtrip(self):
        """Test that mask -> unmask returns original text."""
        from renforge_ai import mask_renpy_tokens, unmask_renpy_tokens
        
        original = "Hello [player]! {b}Welcome{/b} to {color=#00ff00}the game{/color}.{w}"
        
        masked, token_map = mask_renpy_tokens(original)
        restored = unmask_renpy_tokens(masked, token_map)
        
        assert restored == original
    
    def test_unmask_with_modified_text(self):
        """Test unmasking when surrounding text was modified (simulating translation)."""
        from renforge_ai import mask_renpy_tokens, unmask_renpy_tokens
        
        original = "Hello [player], welcome!"
        masked, token_map = mask_renpy_tokens(original)
        
        # Simulate translation changing the surrounding text
        translated_masked = masked.replace("Hello", "Merhaba").replace("welcome", "hoşgeldin")
        
        restored = unmask_renpy_tokens(translated_masked, token_map)
        
        # Original placeholder should be restored
        assert "[player]" in restored
        assert "Merhaba" in restored
        assert "hoşgeldin" in restored
    
    def test_mask_empty_text(self):
        """Test masking with empty text."""
        from renforge_ai import mask_renpy_tokens
        
        masked, token_map = mask_renpy_tokens("")
        assert masked == ""
        assert token_map == {}
        
        masked, token_map = mask_renpy_tokens(None)
        assert masked is None
        assert token_map == {}
    
    def test_mask_text_without_tokens(self):
        """Test masking text that has no tokens."""
        from renforge_ai import mask_renpy_tokens
        
        text = "This is plain text with no special tokens."
        masked, token_map = mask_renpy_tokens(text)
        
        assert masked == text
        assert token_map == {}
    
    def test_mask_python_format_strings(self):
        """Test masking of Python format strings like %s, %(name)s."""
        from renforge_ai import mask_renpy_tokens
        
        text = "Item count: %d, Name: %(name)s, Simple: %s"
        masked, token_map = mask_renpy_tokens(text)
        
        assert "%d" not in masked
        assert "%(name)s" not in masked
        assert "%s" not in masked


class TestValidation:
    """Tests for translation output validation."""
    
    def test_validate_empty_translation(self):
        """Test that empty translations are rejected."""
        from renforge_ai import validate_translation_output
        
        is_valid, error = validate_translation_output("Hello world", "")
        assert not is_valid
        assert "Empty" in error
        
        is_valid, error = validate_translation_output("Hello world", "   ")
        assert not is_valid
        assert "whitespace" in error.lower()
    
    def test_validate_truncated_translation(self):
        """Test that severely truncated translations are flagged."""
        from renforge_ai import validate_translation_output
        
        original = "This is a long sentence that should produce a reasonably sized translation output."
        truncated = "Bu"  # Way too short
        
        is_valid, error = validate_translation_output(original, truncated)
        assert not is_valid
        assert "short" in error.lower()
    
    def test_validate_reasonable_translation(self):
        """Test that reasonable translations pass validation."""
        from renforge_ai import validate_translation_output
        
        original = "Hello, how are you?"
        translation = "Merhaba, nasılsın?"
        
        is_valid, error = validate_translation_output(original, translation)
        assert is_valid
        assert error is None
    
    def test_validate_suspicious_punctuation(self):
        """Test that translations starting with unexpected punctuation are flagged."""
        from renforge_ai import validate_translation_output
        
        original = "Hello there"
        bad_translation = ", Merhaba"  # Starts with comma
        
        is_valid, error = validate_translation_output(original, bad_translation)
        assert not is_valid
        assert "punctuation" in error.lower()
    
    def test_validate_short_original(self):
        """Test validation with very short original text."""
        from renforge_ai import validate_translation_output
        
        original = "Hi"
        translation = "Selam"
        
        is_valid, error = validate_translation_output(original, translation)
        assert is_valid


class TestTokenPreservation:
    """Tests for checking if tokens are preserved during translation."""
    
    def test_all_tokens_preserved(self):
        """Test detecting when all tokens are preserved."""
        from renforge_ai import validate_tokens_preserved
        
        token_map = {"⟦T0⟧": "[player]", "⟦T1⟧": "{b}"}
        translated = "Merhaba ⟦T0⟧! ⟦T1⟧Hoşgeldin⟧"
        
        missing = validate_tokens_preserved("", translated, token_map)
        # T0 and T1 are present
        assert "⟦T0⟧" not in missing
        assert "⟦T1⟧" not in missing
    
    def test_missing_tokens_detected(self):
        """Test detecting when tokens are missing."""
        from renforge_ai import validate_tokens_preserved
        
        token_map = {"⟦T0⟧": "[player]", "⟦T1⟧": "{b}", "⟦T2⟧": "{/b}"}
        translated = "Merhaba ⟦T0⟧!"  # Missing T1 and T2
        
        missing = validate_tokens_preserved("", translated, token_map)
        assert "⟦T1⟧" in missing
        assert "⟦T2⟧" in missing
        assert "⟦T0⟧" not in missing


class TestFirstCharacterPreservation:
    """Tests specifically for first-character loss regression."""
    
    def test_first_char_not_lost_in_masking(self):
        """Ensure masking doesn't lose first character."""
        from renforge_ai import mask_renpy_tokens, unmask_renpy_tokens
        
        original = "Hey there, [player]!"
        masked, token_map = mask_renpy_tokens(original)
        restored = unmask_renpy_tokens(masked, token_map)
        
        assert restored[0] == 'H'
        assert restored.startswith("Hey")
    
    def test_first_char_tag_preserved(self):
        """Test when the text STARTS with a tag."""
        from renforge_ai import mask_renpy_tokens, unmask_renpy_tokens
        
        original = "{b}Bold start{/b}"
        masked, token_map = mask_renpy_tokens(original)
        restored = unmask_renpy_tokens(masked, token_map)
        
        assert restored == original
        assert restored.startswith("{b}")
    
    def test_validation_catches_first_char_loss(self):
        """Test that validation catches first character corruption."""
        from renforge_ai import validate_translation_output
        
        original = "Hello world"
        # Simulating first char loss -> starts with comma
        corrupted = ", ello world"
        
        is_valid, error = validate_translation_output(original, corrupted)
        assert not is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
