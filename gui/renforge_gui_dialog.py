import os
import re

from renforge_logger import get_logger
logger = get_logger("gui.dialog")

try:
    from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
                              QLineEdit, QMessageBox, QDialogButtonBox, QGroupBox,
                              QRadioButton, QGridLayout, QApplication, QSizePolicy, QSplitter,
                              QComboBox, QCheckBox) 
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QFont
except ImportError:
     logger.critical("PyQt6 is required for GUI dialogs but not found.")
     raise 

try:
    import renforge_config as config
    import renforge_core as core
    import parser.core as parser
    from locales import tr
    from models.parsed_file import ParsedItem
    from renforge_enums import ContextType, ItemType

    from renforge_ai import (refine_text_with_gemini, GoogleTranslator,
                            load_api_key, save_api_key, _lazy_import_translator, 
                            get_google_languages, no_ai, gemini_model,
                            _available_models_cache)

    from renforge_settings import load_settings, save_settings
except ImportError as e:
     logger.critical(f"Failed to import renforge modules in dialogs: {e}")
     raise

class AIEditDialog(QDialog):

    def __init__(self, parent, item_index, edit_mode):
        super().__init__(parent)
        self.parent = parent 
        self.item_index = item_index
        self.edit_mode = edit_mode

        current_items = parent._get_current_translatable_items() 
        if not current_items or not (0 <= item_index < len(current_items)):

             QMessageBox.critical(parent, tr("error_data"), tr("error_data_item", index=item_index))

             QTimer.singleShot(0, self.reject)
             return

        self.item: ParsedItem = current_items[item_index]
        self.char_tag = self.item.character_tag or self.item.character_trans
        self.current_file_data = parent._get_current_file_data() 

        if not self.current_file_data:
            QMessageBox.critical(parent, tr("error_data"), tr("error_data_file", index=item_index))
            QTimer.singleShot(0, self.reject)
            return

        self.setWindowTitle(tr("dialog_ai_edit"))
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        item_info = QLabel(tr("ai_item_info", current=item_index + 1, total=len(current_items), mode=edit_mode))
        layout.addWidget(item_info)

        text_splitter = QSplitter(Qt.Orientation.Vertical)

        if edit_mode == "translate":
            original_group = QGroupBox("Original Text")
            original_layout = QVBoxLayout(original_group)
            self.original_text = QTextEdit()
            self.original_text.setReadOnly(True)
            self.original_text.setPlainText(self.item.original_text)
            self.original_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            original_layout.addWidget(self.original_text)
            text_splitter.addWidget(original_group) 

        current_group_title = "Current Text" if edit_mode == "direct" else "Current Translation"
        current_group = QGroupBox(current_group_title)
        current_layout = QVBoxLayout(current_group)
        self.current_text = QTextEdit()
        self.current_text.setReadOnly(True) 
        # text_key logic removed, use unified current_text
        self.current_text.setPlainText(self.item.current_text)
        self.current_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        current_layout.addWidget(self.current_text)
        text_splitter.addWidget(current_group) 

        layout.addWidget(text_splitter, 1) 

        instruction_group = QGroupBox("Instruction for Gemini")
        instruction_layout = QVBoxLayout(instruction_group)
        instruction_label = QLabel(tr("ai_instruction_label"))
        self.instruction_edit = QTextEdit()
        self.instruction_edit.setPlaceholderText(tr("ai_instruction_placeholder"))
        self.instruction_edit.setMaximumHeight(100) 
        instruction_layout.addWidget(instruction_label)
        instruction_layout.addWidget(self.instruction_edit)
        layout.addWidget(instruction_group)

        self.send_btn = QPushButton(tr("btn_send_request"))
        self.send_btn.clicked.connect(self._send_request)

        self.send_btn.setEnabled(not no_ai)
        if no_ai:
            self.send_btn.setToolTip("Gemini is unavailable. Check API key and settings.")
        layout.addWidget(self.send_btn)

        result_group = QGroupBox("Gemini Suggestion")
        result_layout = QVBoxLayout(result_group)
        self.result_text = QTextEdit()

        self.result_text.setPlaceholderText(tr("ai_result_placeholder"))
        result_layout.addWidget(self.result_text)
        layout.addWidget(result_group)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply |

            QDialogButtonBox.StandardButton.Cancel
        )
        self.apply_btn = self.buttons.button(QDialogButtonBox.StandardButton.Apply)
        self.apply_btn.setText(tr("btn_apply_result"))
        self.apply_btn.setEnabled(False) 
        self.apply_btn.clicked.connect(self._apply_suggestion)
        self.buttons.rejected.connect(self.reject)

        layout.addWidget(self.buttons)

    def _send_request(self):

        global no_ai
        instruction = self.instruction_edit.toPlainText().strip()
        if not instruction:
            instruction = "Improve the text for clarity, grammar, and naturalness, preserving the original meaning and style."
            logger.debug(f"GUI Dialog: Using default instruction: '{instruction}'")

        self.send_btn.setEnabled(False)
        self.send_btn.setText(tr("btn_sending"))
        self.apply_btn.setEnabled(False)
        self.result_text.setPlainText("Waiting for response from Gemini...")
        QApplication.processEvents() 

        try:

            current_text_for_ai = self.item.current_text
            original_text_for_ai = self.item.original_text if self.edit_mode == "translate" else current_text_for_ai

            context = core.get_context_for_item( 
                self.item_index,
                self.current_file_data.items,
                self.current_file_data.lines,
                self.edit_mode
            )

            source_lang = self.current_file_data.source_language or config.DEFAULT_SOURCE_LANG
            target_lang = self.current_file_data.target_language or config.DEFAULT_TARGET_LANG

            logger.debug(f"[AIEditDialog._send_request] Calling refine_text_with_gemini...") 
            refined_text, error_msg = refine_text_with_gemini(
                original_text_for_ai, current_text_for_ai, instruction, context,
                source_lang, target_lang, self.edit_mode, self.char_tag
            )
            logger.debug(f"[AIEditDialog._send_request] refine_text_with_gemini returned. Refined: {refined_text is not None}, Error: '{error_msg}'") 

            if refined_text is not None:
                self.result_text.setPlainText(refined_text)
                self.apply_btn.setEnabled(True) 
            else:
                error_display = "Gemini could not suggest an improvement."
                if error_msg:
                    error_display += f"\n\nReason: {error_msg}"
                else:
                    error_display += "\n\nReason unknown (possibly an internal error)."
                logger.warning(f"[AIEditDialog._send_request] Displaying error: {error_display}") 
                self.result_text.setPlainText(error_display)
                self.apply_btn.setEnabled(False)
                QMessageBox.warning(self, tr("error_gemini"), error_display)

        except Exception as e:
            error_display = f"An UNEXPECTED error occurred while processing the request to Gemini:\n{type(e).__name__}: {e}"
            logger.critical(f"[AIEditDialog._send_request] CRITICAL ERROR: {error_display}") 
            import traceback
            traceback.print_exc()
            self.result_text.setPlainText(error_display)
            self.apply_btn.setEnabled(False)
            QMessageBox.critical(self, tr("error_gemini_critical"), error_display)
            no_ai = True 
        finally:
             self.send_btn.setEnabled(True)
             self.send_btn.setText(tr("btn_send_request"))
             if self.parent:
                 self.parent._update_ui_state() 

    def _apply_suggestion(self):

        refined_text = self.result_text.toPlainText() 

        if not refined_text or refined_text.startswith("Gemini could not"): 
             QMessageBox.warning(self, tr("ai_no_result"), tr("ai_no_result"))
             return

        # text_key logic removed, using unified current_text

        text_before_refinement = self.item.current_text

        text_for_var_comparison = self.item.original_text if self.edit_mode == "translate" else text_before_refinement

        original_vars = set(re.findall(r'(\[.*?\])', text_for_var_comparison))
        refined_vars = set(re.findall(r'(\[.*?\])', refined_text))

        if original_vars != refined_vars:
            result = QMessageBox.warning(
                self, tr("variable_warning_title"),
                f"A change in '[...]' variables was detected!\n"
                f"Original: {original_vars or '{}'}\n"
                f"New: {refined_vars or '{}'}\n\n"
                "Continue applying?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if result != QMessageBox.StandardButton.Yes:
                return 

        self.item.current_text = refined_text
        self.item.is_modified_session = True

        if self.item.initial_text is None:
             self.item.initial_text = text_before_refinement 

        if self.edit_mode == "translate":
            line_idx = self.item.line_index
            parsed_data = self.item.parsed_data
            current_file_lines = self.current_file_data.lines

            if line_idx is not None and parsed_data is not None and current_file_lines and 0 <= line_idx < len(current_file_lines):
                new_line = parser.format_line_from_components(self.item, refined_text)
                if new_line is not None:
                    current_file_lines[line_idx] = new_line

                    self.accept()
                else:

                    QMessageBox.critical(self, tr("error_formatting"),
                                         tr("error_formatting_message"))
                    self.item.current_text = text_before_refinement 
                    self.item.is_modified_session = (self.item.current_text != self.item.initial_text) 

            else:

                 QMessageBox.critical(self, tr("error_line_data"),
                                   tr("error_line_data_message", line=line_idx))
                 self.item.current_text = text_before_refinement
                 self.item.is_modified_session = (self.item.current_text != self.item.initial_text)

        else: 
            self.accept()

class GoogleTranslateDialog(QDialog):

    def __init__(self, parent, item_index, edit_mode):
        super().__init__(parent)
        self.parent = parent
        self.item_index = item_index
        self.edit_mode = edit_mode

        current_items = parent._get_current_translatable_items()
        if not current_items or not (0 <= item_index < len(current_items)):
             QMessageBox.critical(parent, tr("error_data"), tr("error_data_item", index=item_index))
             QTimer.singleShot(0, self.reject)
             return
        self.item = current_items[item_index]
        self.current_file_data = parent._get_current_file_data()
        if not self.current_file_data:
            QMessageBox.critical(parent, tr("error_data"), tr("error_data_file", index=item_index))
            QTimer.singleShot(0, self.reject)
            return

        self.setWindowTitle(tr("dialog_google_translate"))
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)

        item_info = QLabel(tr("ai_item_info", current=item_index + 1, total=len(current_items), mode=edit_mode))
        layout.addWidget(item_info)

        settings_group = QGroupBox("Translation Settings (from main window)")
        settings_layout = QGridLayout(settings_group)

        self.source_code = self.current_file_data.source_language or config.DEFAULT_SOURCE_LANG
        self.target_code = self.current_file_data.target_language or config.DEFAULT_TARGET_LANG

        all_languages = parent.google_languages if hasattr(parent, 'google_languages') else {}
        source_lang_name = all_languages.get(self.source_code, self.source_code) 
        target_lang_name = all_languages.get(self.target_code, self.target_code) 

        if self.source_code == "auto":
             source_display = f"Source Language: Auto ({self.source_code})"
        else:
             source_display = f"Source Language: {source_lang_name} ({self.source_code})"
        target_display = f"Target Language: {target_lang_name} ({self.target_code})"

        source_lang_label = QLabel(source_display)
        settings_layout.addWidget(source_lang_label, 0, 0)
        target_lang_label = QLabel(target_display)
        settings_layout.addWidget(target_lang_label, 1, 0)
        layout.addWidget(settings_group)

        text_splitter = QSplitter(Qt.Orientation.Vertical)

        text_to_translate_val = ""
        if edit_mode == "translate" or edit_mode == "direct": 
             text_to_translate_val = self.item.original_text

        source_group = QGroupBox("Text to Translate (Original)")
        source_layout = QVBoxLayout(source_group)
        self.source_text = QTextEdit()
        self.source_text.setReadOnly(True)
        self.source_text.setPlainText(text_to_translate_val)
        self.source_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        source_layout.addWidget(self.source_text)
        text_splitter.addWidget(source_group)

        current_text_val = ""
        # text_key logic removed
        current_text_val = self.item.current_text
        current_group = QGroupBox("Current Text/Translation")
        current_layout = QVBoxLayout(current_group)
        self.current_text = QTextEdit()
        self.current_text.setReadOnly(True)
        self.current_text.setPlainText(current_text_val)
        self.current_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        current_layout.addWidget(self.current_text)
        text_splitter.addWidget(current_group)

        layout.addWidget(text_splitter, 1) 

        self.translate_btn = QPushButton("Translate")
        self.translate_btn.clicked.connect(self._translate)

        self.GoogleTranslator = _lazy_import_translator() 

        if self.GoogleTranslator is None:
             self.translate_btn.setEnabled(False)
             self.translate_btn.setToolTip("The deep-translator library is unavailable.")
        elif not self.target_code:
             self.translate_btn.setEnabled(False)
             self.translate_btn.setToolTip("Target language is not specified in settings.")

        layout.addWidget(self.translate_btn)

        result_group = QGroupBox("Google Translation Result")
        result_layout = QVBoxLayout(result_group)
        self.result_text = QTextEdit()

        self.result_text.setPlaceholderText(tr("translate_result_placeholder"))
        result_layout.addWidget(self.result_text)
        layout.addWidget(result_group)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.Cancel
        )
        self.apply_btn = self.buttons.button(QDialogButtonBox.StandardButton.Apply)
        self.apply_btn.setText(tr("btn_apply_translation"))
        self.apply_btn.setEnabled(False) 
        self.apply_btn.clicked.connect(self._apply_translation)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _translate(self):

        Translator = self.GoogleTranslator
        if Translator is None:
            QMessageBox.warning(self, tr("error"), tr("translate_lib_unavailable"))
            return
        if not self.target_code:
            QMessageBox.warning(self, tr("error"), tr("translate_no_target"))
            return

        text_to_translate = self.source_text.toPlainText()
        if not text_to_translate:
            self.result_text.setPlainText("No text to translate.")
            self.apply_btn.setEnabled(False)
            return

        self.translate_btn.setEnabled(False)
        self.translate_btn.setText(tr("btn_translating"))
        self.apply_btn.setEnabled(False)
        self.result_text.setPlainText("Requesting Google Translate...")
        QApplication.processEvents()

        try:

            translator = Translator(source=self.source_code, target=self.target_code)
            translated_text = translator.translate(text_to_translate)

            if translated_text:
                self.result_text.setPlainText(translated_text)
                self.apply_btn.setEnabled(True)
            else:
                self.result_text.setPlainText("Failed to get translation from Google.")
                self.apply_btn.setEnabled(False)

        except Exception as e:
            error_msg = f"Error during Google translation: {e}"
            self.result_text.setPlainText(error_msg)
            self.apply_btn.setEnabled(False)
            QMessageBox.warning(self, tr("error_google_translate"), error_msg)
        finally:

            self.translate_btn.setEnabled(True)
            self.translate_btn.setText(tr("btn_translate"))

    def _apply_translation(self):

        translated_text = self.result_text.toPlainText() 

        if not translated_text or translated_text.startswith("Failed to get"): 
             QMessageBox.warning(self, tr("translate_no_result"), tr("translate_no_result"))
             return

        # text_key logic removed

        text_before_translation = self.item.current_text

        text_for_var_comparison = self.item.original_text if self.edit_mode == "translate" else text_before_translation

        original_vars = set(re.findall(r'(\[.*?\])', text_for_var_comparison))
        translated_vars = set(re.findall(r'(\[.*?\])', translated_text))

        if original_vars != translated_vars:
            result = QMessageBox.warning(
                self, tr("variable_warning_title"),
                f"A change in '[...]' variables was detected!\n"
                f"Original: {original_vars or '{}'}\n"
                f"New: {translated_vars or '{}'}\n\n"
                "Continue applying?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if result != QMessageBox.StandardButton.Yes:
                return

        self.item.current_text = translated_text
        self.item.is_modified_session = True
        if self.item.initial_text is None:
             self.item.initial_text = text_before_translation

        if self.edit_mode == "translate":
            line_idx = self.item.line_index
            parsed_data = self.item.parsed_data
            current_file_lines = self.current_file_data.lines

            if line_idx is not None and parsed_data is not None and current_file_lines and 0 <= line_idx < len(current_file_lines):

                new_line = parser.format_line_from_components(self.item, translated_text)
                if new_line is not None:
                    current_file_lines[line_idx] = new_line
                    self.accept() 
                else:
                    QMessageBox.critical(self, tr("error_formatting"),
                                         tr("error_formatting_message"))
                    self.item.current_text = text_before_translation
                    self.item.is_modified_session = (self.item.current_text != self.item.initial_text)
            else:
                 QMessageBox.critical(self, tr("error_line_data"),
                                   tr("error_line_data_message", line=line_idx))
                 self.item.current_text = text_before_translation
                 self.item.is_modified_session = (self.item.current_text != self.item.initial_text)
        else: 
            self.accept() 

class ApiKeyDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.save_status = "unchanged" 
        self._save_status_internal = "pending"

        self.setWindowTitle(tr("dialog_api_key"))
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        info_label = QLabel(tr("api_key_info"))
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setOpenExternalLinks(True) 
        layout.addWidget(info_label)

        self.current_key_label = QLabel("")
        self._update_current_key_label()
        layout.addWidget(self.current_key_label)

        key_label = QLabel(tr("api_key_new"))
        layout.addWidget(key_label)
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("AI...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password) 
        layout.addWidget(self.key_input)

        self.show_key_button = QPushButton(tr("btn_show_key"))
        self.show_key_button.setCheckable(True)
        self.show_key_button.toggled.connect(self._toggle_key_visibility)
        layout.addWidget(self.show_key_button)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("btn_save_close"))
        buttons.accepted.connect(self._save_and_accept) 
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_current_key_label(self):

        current_key = load_api_key() 
        if current_key:
            masked_key = "..." + current_key[-4:] if len(current_key) > 4 else current_key
            self.current_key_label.setText(tr("api_key_current", api_key=masked_key))
            self.current_key_label.setStyleSheet("color: #90EE90;") 
        else:
            self.current_key_label.setText(tr("api_key_not_saved"))
            self.current_key_label.setStyleSheet("color: #FFA07A;") 

    def _toggle_key_visibility(self, checked):

        if checked:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_key_button.setText(tr("btn_hide_key"))
        else:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_key_button.setText(tr("btn_show_key"))

    def _save_and_accept(self):

        new_key = self.key_input.text().strip()
        key_to_save = new_key if new_key else None 
        needs_confirmation_for_delete = False

        self._save_status_internal = "pending"

        current_key_exists = load_api_key() is not None

        if not new_key and current_key_exists:
            needs_confirmation_for_delete = True

        if needs_confirmation_for_delete:
            reply = QMessageBox.question(self, tr("api_key_delete_confirm"),
                                         tr("api_key_delete_message"),
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:

                self.reject()
                return 

        save_status, updated_settings = save_api_key(key_to_save)
        self._save_status_internal = save_status 

        if save_status == "error":
             QMessageBox.warning(self, tr("error"), tr("api_key_save_error"))

             return
        else:

             if self.parent(): 

                 if save_status in ["saved", "removed"]:

                      self.parent().settings = updated_settings.copy() 
                      logger.debug(f"Parent window settings updated in memory (status: {save_status}).")
                 else: 
                      logger.debug(f"No changes made to API key (status: {save_status}). Parent settings not updated.")
             else:
                 logger.warning("ApiKeyDialog has no parent to update settings for.")

             self.accept()

    def get_save_status(self):

        return self._save_status_internal

class ModeSelectionDialog(QDialog):

    def __init__(self, parent=None, initial_mode="direct", filename=""):
        super().__init__(parent)
        self.setWindowTitle(tr("dialog_mode_select"))
        self.setMinimumWidth(400)

        self.selected_mode = initial_mode 

        layout = QVBoxLayout(self)

        file_label = QLabel(f"File: <b>{os.path.basename(filename)}</b>")
        layout.addWidget(file_label)
        full_path_label = QLabel(f"Path: {filename}")
        full_path_label.setStyleSheet("font-size: 8pt; color: #a0a0a0;") 
        layout.addWidget(full_path_label)

        group_box = QGroupBox(f"Select mode (suggested: {initial_mode}):") 
        mode_layout = QVBoxLayout(group_box)

        self.direct_radio = QRadioButton(tr("mode_direct") + " - " + tr("mode_direct_desc"))
        self.direct_radio.setToolTip("Edits dialogue, narration, menu lines.\nIgnores comments, labels, Ren'Py commands, Python code.")
        self.translate_radio = QRadioButton(tr("mode_translate") + " - " + tr("mode_translate_desc"))
        self.translate_radio.setToolTip("Edits lines within 'translate python:' or 'translate <language> strings:' blocks.\nUses # comments for original and 'new'/'old' lines.")

        if initial_mode == "translate":
            self.translate_radio.setChecked(True)
        else:
            self.direct_radio.setChecked(True)

        mode_layout.addWidget(self.direct_radio)
        mode_layout.addWidget(self.translate_radio)
        group_box.setLayout(mode_layout) 
        layout.addWidget(group_box)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):

        self.selected_mode = "translate" if self.translate_radio.isChecked() else "direct"
        super().accept()

    def get_selected_mode(self):

        return self.selected_mode

class InsertLineDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dialog_insert_line"))
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        label = QLabel(tr("insert_line_label"))
        layout.addWidget(label)

        examples_label = QLabel(
            "<i>Examples:</i><br>"
            "<code>e \"Hello, world!\"</code><br>"
            "<code>\"This is a narration line.\"</code><br>"
            "<code>menu:</code><br>"
            "<code>    \"Choice 1\":</code><br>"
            "<code>        jump choice_1</code>"
            )
        examples_label.setStyleSheet("font-size: 9pt; color: #c0c0c0; background-color: #3a3a3a; border: 1px solid #4f5254; padding: 5px; border-radius: 3px;")
        examples_label.setWordWrap(True)
        layout.addWidget(examples_label)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(tr("insert_line_placeholder"))
        layout.addWidget(self.line_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_line_text(self):

        return self.line_edit.text()

class SettingsDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dialog_main_settings"))
        self.setMinimumWidth(500) 

        self.settings = parent.settings if parent else load_settings()
        self.current_mode_method = self.settings.get("mode_selection_method", config.DEFAULT_MODE_SELECTION_METHOD)
        if self.current_mode_method not in ["auto", "manual"]:
            self.current_mode_method = config.DEFAULT_MODE_SELECTION_METHOD

        self.current_default_source_lang = self.settings.get("default_source_language", config.DEFAULT_SOURCE_LANG)
        self.current_default_target_lang = self.settings.get("default_target_language", config.DEFAULT_TARGET_LANG)
        self.current_default_model = self.settings.get("default_selected_model", config.DEFAULT_MODEL_NAME)
        self.current_use_detected_lang = self.settings.get("use_detected_target_lang", config.DEFAULT_USE_DETECTED_TARGET_LANG)
        self.current_auto_prepare_project = self.settings.get("auto_prepare_project", config.DEFAULT_AUTO_PREPARE_PROJECT)
        self.current_ui_language = self.settings.get("ui_language", config.DEFAULT_UI_LANGUAGE)

        self.languages = parent.SUPPORTED_LANGUAGES if hasattr(parent, 'SUPPORTED_LANGUAGES') else get_google_languages() or {}

        self.models = _available_models_cache if _available_models_cache is not None else []

        display_mode = self.current_mode_method if self.current_mode_method else "auto"

        layout = QVBoxLayout(self)

        mode_group = QGroupBox(tr("settings_mode_selection"))
        mode_layout = QVBoxLayout(mode_group)

        self.auto_mode_radio = QRadioButton(tr("settings_mode_auto"))
        self.auto_mode_radio.setToolTip("The program will try to determine if the file contains 'translate' blocks.")
        self.manual_mode_radio = QRadioButton(tr("settings_mode_manual"))
        self.manual_mode_radio.setToolTip("A mode selection dialog will be shown before opening each file.")

        if self.current_mode_method == "manual":
            self.manual_mode_radio.setChecked(True)
        else:
            self.auto_mode_radio.setChecked(True) 

        mode_layout.addWidget(self.auto_mode_radio)
        mode_layout.addWidget(self.manual_mode_radio)
        layout.addWidget(mode_group)

        lang_group = QGroupBox(tr("settings_language"))
        lang_layout = QVBoxLayout(lang_group)

        self.use_detected_lang_checkbox = QCheckBox(tr("settings_use_detected_lang"))
        self.use_detected_lang_checkbox.setToolTip("If enabled, the target language for 'translate' tabs will be\n"
                                                    "automatically set from 'translate <language> ...',\n"
                                                    "overriding the default language.")
        self.use_detected_lang_checkbox.setChecked(self.current_use_detected_lang)
        lang_layout.addWidget(self.use_detected_lang_checkbox)
        layout.addWidget(lang_group)

        prepare_group = QGroupBox(tr("settings_project"))
        prepare_layout = QVBoxLayout(prepare_group)
        self.auto_prepare_checkbox = QCheckBox(tr("settings_auto_prepare"))
        self.auto_prepare_checkbox.setToolTip("If enabled, when opening a project, the program will attempt to\n"
                                             "find the necessary *.rpy files by unpacking archives and\n"
                                             "decompiling *.rpyc files (requires unrpa and unrpyc).")
        self.auto_prepare_checkbox.setChecked(self.current_auto_prepare_project)
        prepare_layout.addWidget(self.auto_prepare_checkbox)
        layout.addWidget(prepare_group)

        defaults_group = QGroupBox(tr("settings_defaults"))
        defaults_layout = QGridLayout(defaults_group)

        defaults_layout.addWidget(QLabel(tr("settings_source_lang")), 0, 0)
        self.default_source_lang_combo = QComboBox()
        self.default_source_lang_combo.addItem("Auto-detect", "auto")
        sorted_langs = sorted(self.languages.items(), key=lambda item: item[1])
        for code, name in sorted_langs:
            self.default_source_lang_combo.addItem(name, code)

        idx = self.default_source_lang_combo.findData(self.current_default_source_lang)
        self.default_source_lang_combo.setCurrentIndex(idx if idx != -1 else 0)
        defaults_layout.addWidget(self.default_source_lang_combo, 0, 1)

        defaults_layout.addWidget(QLabel(tr("settings_target_lang")), 1, 0)
        self.default_target_lang_combo = QComboBox()
        for code, name in sorted_langs: 
            self.default_target_lang_combo.addItem(name, code)
        idx = self.default_target_lang_combo.findData(self.current_default_target_lang)
        self.default_target_lang_combo.setCurrentIndex(idx if idx != -1 else 0)
        defaults_layout.addWidget(self.default_target_lang_combo, 1, 1)

        defaults_layout.addWidget(QLabel(tr("settings_gemini_model")), 2, 0)
        self.default_model_combo = QComboBox()
        self.default_model_combo.addItem("None") 
        if self.models:
             self.default_model_combo.addItems(self.models)
             idx = self.default_model_combo.findText(self.current_default_model if self.current_default_model else "")
             self.default_model_combo.setCurrentIndex(idx if idx != -1 else 0) 
        else:
             self.default_model_combo.addItem("Models not loaded")
             self.default_model_combo.setEnabled(False)
        defaults_layout.addWidget(self.default_model_combo, 2, 1)

        layout.addWidget(defaults_group)

        # UI Language Group
        ui_lang_group = QGroupBox(tr("settings_ui_language"))
        ui_lang_layout = QHBoxLayout(ui_lang_group)
        ui_lang_layout.addWidget(QLabel(tr("settings_ui_lang_label")))
        self.ui_lang_combo = QComboBox()
        self.ui_lang_combo.addItem("Türkçe", "tr")
        self.ui_lang_combo.addItem("English", "en")
        idx = self.ui_lang_combo.findData(self.current_ui_language)
        self.ui_lang_combo.setCurrentIndex(idx if idx != -1 else 0)
        ui_lang_layout.addWidget(self.ui_lang_combo)
        ui_lang_layout.addStretch()
        layout.addWidget(ui_lang_group)
        
        # Restart notice
        restart_label = QLabel(tr("settings_ui_lang_restart"))
        restart_label.setStyleSheet("color: #FFA07A; font-style: italic;")
        layout.addWidget(restart_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):

        new_method = self.get_selected_mode_method()
        new_use_detected_lang = self.use_detected_lang_checkbox.isChecked()
        new_default_source = self.default_source_lang_combo.currentData()
        new_default_target = self.default_target_lang_combo.currentData()
        new_default_model_text = self.default_model_combo.currentText()
        new_auto_prepare = self.auto_prepare_checkbox.isChecked()
        if new_default_model_text == "None" or new_default_model_text == "Models not loaded":
             new_default_model_to_save = None 
        else:
             new_default_model_to_save = new_default_model_text 

        settings_to_update = self.settings 

        settings_to_update["mode_selection_method"] = new_method
        settings_to_update["use_detected_target_lang"] = new_use_detected_lang
        settings_to_update["default_source_language"] = new_default_source
        settings_to_update["default_target_language"] = new_default_target
        settings_to_update["default_selected_model"] = new_default_model_to_save 
        settings_to_update["auto_prepare_project"] = new_auto_prepare
        
        # UI Language
        new_ui_language = self.ui_lang_combo.currentData()
        settings_to_update["ui_language"] = new_ui_language
        if save_settings(settings_to_update): 

             if self.parent():
                  self.parent().settings = settings_to_update.copy() 

                  self.parent().target_language = new_default_target
                  self.parent().source_language = new_default_source
                  self.parent().selected_model = new_default_model_to_save

                  self.parent()._update_main_window_defaults_display()
                  self.parent()._update_language_model_display()

             super().accept()
        else:
             QMessageBox.warning(self, tr("error"), tr("settings_save_error"))

    def get_selected_mode_method(self):

        return "manual" if self.manual_mode_radio.isChecked() else "auto"

logger.debug("gui/renforge_gui_dialogs.py loaded")