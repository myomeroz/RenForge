
import sys
import os
import unittest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parser.translate_parser import TranslateParser
from parser.core import format_line_from_components
from models.parsed_file import ParsedItem
from renforge_enums import ItemType

class TestP0Fix(unittest.TestCase):
    def test_parser_extracts_character_tag(self):
        """Verify TranslateParser extracts 'mc 12' correctly (Fix P3-6)."""
        lines = [
            'translate Italian start_a1b2c3:',
            '#   mc 12 "Original text"',
            '    mc 12 "Translation text"' # Ren'Py generated format often repeats char in translation line
        ]
        
        # Or specifically the format user showed:
        # #   mc 12 "{i}(Damn...)"
        #     mc 12 "{i}(Accidenti...)"
        
        parser = TranslateParser()
        items, lang = parser.parse(lines)
        
        # Should find 1 item
        self.assertEqual(len(items), 1)
        item = items[0]
        
        print(f"Parsed Item: {item.parsed_data}")
        
        # Check if character tag is captured in parsed_data
        character_data = item.parsed_data.get('character')
        self.assertIsNotNone(character_data, "Character tag missing in parsed_data")
        self.assertTrue('mc 12' in character_data, f"Expected 'mc 12' in character data, got '{character_data}'")

    def test_reconstruction_preserves_prefix(self):
        """Verify formatting preserves the prefix using memory Item (Fix P3-5 logic)."""
        
        # Simulate an item stored in memory
        item = ParsedItem(
            line_index=2,
            original_text="Original",
            current_text="Old Trans",
            initial_text="Old Trans",
            type=ItemType.DIALOGUE,
            parsed_data={
                'indent': '    ',
                'character': 'mc 12', # The critical data (No trailing space)
                'suffix': '\n',
                'prefix': '' # Translate parser typically uses character as prefix equivalent for dialogue
            }
        )
        
        new_text = "New Translation"
        
        # Reconstruct
        new_line = format_line_from_components(item, new_text)
        
        print(f"Reconstructed Line: '{new_line}'")
        
        expected_line = '    mc 12 "New Translation"\n'
        self.assertEqual(new_line, expected_line)
        
        # Verify it DOES NOT look like '    "New Translation"\n'
        self.assertNotEqual(new_line.strip(), '"New Translation"')

    def test_parser_handles_empty_prefix_correctly(self):
        """Verify format 1 (old/new) still works."""
        item = ParsedItem(
            line_index=1,
            original_text="Old",
            current_text="New",
            initial_text="New",
            type=ItemType.DIALOGUE,
            parsed_data={
                'indent': '    ',
                'prefix': 'new ',
                'suffix': '\n'
            }
        )
        new_line = format_line_from_components(item, "Updated")
        self.assertEqual(new_line, '    new "Updated"\n')

if __name__ == '__main__':
    unittest.main()
