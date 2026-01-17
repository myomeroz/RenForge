
import unittest
from core.error_explainer import ErrorExplainer
from gui.panels.inspector_panel import InspectorPanel
from PySide6.QtWidgets import QApplication
import sys

# Ensure QApplication
app = QApplication.instance() or QApplication(sys.argv)

class TestSmartErrorsPolish(unittest.TestCase):
    def test_empty_result_classification(self):
        """Test that 'Empty result' is classified as EMPTY_RESPONSE."""
        errors = ["Line 45: Empty result from Gemini"]
        summary = ErrorExplainer.analyze(errors)
        
        self.assertEqual(summary['category'], ErrorExplainer.CAT_EMPTY)
        self.assertIn("Boş Sonuç", summary['title'])
        self.assertIn("Empty result", summary['raw_sample'])
        
    def test_inspector_goto_line_parsing(self):
        """Test that InspectorPanel extracts line number from error summary."""
        panel = InspectorPanel()
        
        # Simulare a status with error summary containing a line number
        summary = {
            'category': 'EMPTY_RESPONSE',
            'title': 'Test Error',
            'message': 'Test Message',
            'suggestions': [],
            'raw_sample': 'Error at Line 123: unexpected token'
        }
        
        status = {
            'stage': 'completed',
            'failed': 1,
            'error_summary': summary
        }
        
        panel.show_batch_status(status)
        
        # Check if button is visible and text is correct
        # self.assertTrue(panel.goto_line_btn.isVisible(), "Go to Line button should be visible")
        self.assertIn("123", panel.goto_line_btn.text(), "Button text should contain line number 123")
        self.assertEqual(panel._target_line_for_nav, 123, "Target line should be parsed as 123")
        
    def test_inspector_no_line_parsing(self):
        """Test that InspectorPanel handles errors without line numbers."""
        panel = InspectorPanel()
        
        summary = {
            'category': 'NETWORK',
            'title': 'Valid Error',
            'message': 'Msg',
            'suggestions': [],
            'raw_sample': 'Connection timed out'
        }
        
        status = {
            'stage': 'completed',
            'failed': 1,
            'error_summary': summary
        }
        
        panel.show()
        panel.show_batch_status(status)
        
        self.assertFalse(panel.goto_line_btn.isVisible(), "Go to Line button should NOT be visible")
        self.assertIsNone(panel._target_line_for_nav)

if __name__ == '__main__':
    unittest.main()
