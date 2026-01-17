# -*- coding: utf-8 -*-
"""
RenForge Settings Page

Application settings with theme toggle and other options.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, CardWidget, SwitchButton,
    FluentIcon as FIF, ComboBox, SettingCard, ExpandLayout,
    setTheme, Theme, isDarkTheme
)

from renforge_logger import get_logger

logger = get_logger("gui.pages.settings")


class SettingsPage(QWidget):
    """
    Settings page with theme toggle and application options.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsPage")
        
        self._setup_ui()
        logger.debug("SettingsPage initialized")
    
    def _setup_ui(self):
        """Setup the settings UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Title
        title = SubtitleLabel("Ayarlar")
        layout.addWidget(title)
        
        # Theme section
        theme_card = CardWidget()
        theme_layout = QVBoxLayout(theme_card)
        theme_layout.setContentsMargins(16, 16, 16, 16)
        theme_layout.setSpacing(12)
        
        theme_header = QHBoxLayout()
        theme_label = BodyLabel("Tema")
        theme_label.setStyleSheet("font-weight: bold;")
        theme_header.addWidget(theme_label)
        theme_header.addStretch()
        theme_layout.addLayout(theme_header)
        
        # Dark mode toggle
        dark_mode_layout = QHBoxLayout()
        dark_mode_label = BodyLabel("Koyu Tema")
        dark_mode_layout.addWidget(dark_mode_label)
        dark_mode_layout.addStretch()
        
        self.dark_mode_switch = SwitchButton()
        self.dark_mode_switch.setChecked(isDarkTheme())
        self.dark_mode_switch.checkedChanged.connect(self._on_theme_changed)
        dark_mode_layout.addWidget(self.dark_mode_switch)
        theme_layout.addLayout(dark_mode_layout)
        
        layout.addWidget(theme_card)
        
        # Language section - Only UI language (Uygulama dili)
        lang_card = CardWidget()
        lang_layout = QVBoxLayout(lang_card)
        lang_layout.setContentsMargins(16, 16, 16, 16)
        lang_layout.setSpacing(12)
        
        lang_header = QHBoxLayout()
        lang_label = BodyLabel("Dil Ayarları")
        lang_label.setStyleSheet("font-weight: bold;")
        lang_header.addWidget(lang_label)
        lang_header.addStretch()
        lang_layout.addLayout(lang_header)
        
        # UI Language (Uygulama Dili) 
        ui_lang_layout = QHBoxLayout()
        ui_lang_layout.addWidget(BodyLabel("Uygulama Dili"))
        ui_lang_layout.addStretch()
        self.ui_lang_combo = ComboBox()
        self.ui_lang_combo.addItem("Türkçe", "tr")
        self.ui_lang_combo.addItem("English", "en")
        self.ui_lang_combo.setCurrentIndex(0)  # Default Turkish
        ui_lang_layout.addWidget(self.ui_lang_combo)
        lang_layout.addLayout(ui_lang_layout)
        
        # NOTE: "Varsayılan Kaynak/Hedef Dil" combos removed.
        # Translation source/target languages are now controlled exclusively 
        # from TranslatePage settings bar (Hedef/Kaynak dropdowns).
        
        layout.addWidget(lang_card)
        
        # AI Settings section
        ai_card = CardWidget()
        ai_layout = QVBoxLayout(ai_card)
        ai_layout.setContentsMargins(16, 16, 16, 16)
        ai_layout.setSpacing(12)
        
        ai_header = QHBoxLayout()
        ai_label = BodyLabel("AI Ayarları")
        ai_label.setStyleSheet("font-weight: bold;")
        ai_header.addWidget(ai_label)
        ai_header.addStretch()
        ai_layout.addLayout(ai_header)
        
        # API Key
        from qfluentwidgets import LineEdit, PushButton
        api_layout = QHBoxLayout()
        api_layout.addWidget(BodyLabel("Gemini API Anahtarı"))
        api_layout.addStretch()
        self.api_key_edit = LineEdit()
        self.api_key_edit.setPlaceholderText("API anahtarınızı girin...")
        self.api_key_edit.setMinimumWidth(200)
        self.api_key_edit.setEchoMode(LineEdit.EchoMode.Password)
        api_layout.addWidget(self.api_key_edit)
        
        self.api_key_btn = PushButton("Kaydet")
        self.api_key_btn.clicked.connect(self._save_api_key)
        api_layout.addWidget(self.api_key_btn)
        ai_layout.addLayout(api_layout)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(BodyLabel("Gemini Model"))
        model_layout.addStretch()
        self.model_combo = ComboBox()
        self.model_combo.addItems([
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b"
        ])
        self.model_combo.setCurrentText("gemini-2.5-flash-lite")
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        model_layout.addWidget(self.model_combo)
        ai_layout.addLayout(model_layout)
        
        # Load saved API key if exists
        self._load_api_key()
        
        layout.addWidget(ai_card)
        
        # Performance section
        perf_card = CardWidget()
        perf_layout = QVBoxLayout(perf_card)
        perf_layout.setContentsMargins(16, 16, 16, 16)
        perf_layout.setSpacing(12)
        
        perf_header = QHBoxLayout()
        perf_label = BodyLabel("Performans")
        perf_label.setStyleSheet("font-weight: bold;")
        perf_header.addWidget(perf_label)
        perf_header.addStretch()
        perf_layout.addLayout(perf_header)
        
        # Batch size
        batch_layout = QHBoxLayout()
        batch_layout.addWidget(BodyLabel("Toplu çeviri chunk boyutu"))
        batch_layout.addStretch()
        self.batch_size_combo = ComboBox()
        self.batch_size_combo.addItems(["10", "25", "50", "100"])
        self.batch_size_combo.setCurrentText("25")
        batch_layout.addWidget(self.batch_size_combo)
        perf_layout.addLayout(batch_layout)
        
        layout.addWidget(perf_card)
        
        
        # Shortcuts section
        self._setup_shortcuts_ui(layout)
        
        layout.addStretch()
    
    def _setup_shortcuts_ui(self, parent_layout):
        """Setup the keyboard shortcuts configuration section."""
        from gui.shortcuts.shortcut_manager import ShortcutManager
        from qfluentwidgets import PushButton, InfoBar, InfoBarPosition, SwitchButton
        # KeySequenceEdit is not available in qfluentwidgets, use PySide6
        from PySide6.QtWidgets import QKeySequenceEdit
        from PySide6.QtGui import QKeySequence
        
        shortcuts_card = CardWidget()
        shortcuts_layout = QVBoxLayout(shortcuts_card)
        shortcuts_layout.setContentsMargins(16, 16, 16, 16)
        shortcuts_layout.setSpacing(12)
        
        # Header
        header = QHBoxLayout()
        title_label = BodyLabel("Klavye Kısayolları")
        title_label.setStyleSheet("font-weight: bold;")
        header.addWidget(title_label)
        header.addStretch()
        
        # Enable Switch
        self.shortcuts_switch = SwitchButton()
        self.shortcuts_switch.setOnText("Açık")
        self.shortcuts_switch.setOffText("Kapalı")
        
        # Connect to settings
        from models.settings_model import SettingsModel
        settings = SettingsModel.instance()
        
        self.shortcuts_switch.setChecked(settings.keyboard_shortcuts_enabled)
        self.shortcuts_switch.checkedChanged.connect(self._on_shortcuts_toggle)
        header.addWidget(self.shortcuts_switch)
        
        shortcuts_layout.addLayout(header)
        shortcuts_layout.addSpacing(10)
        
        # List Container
        self.shortcuts_list_layout = QVBoxLayout()
        self.shortcuts_list_layout.setSpacing(8)
        shortcuts_layout.addLayout(self.shortcuts_list_layout)
        
        # Populate List
        self._populate_shortcuts_list()
        
        # Reset All Button
        reset_layout = QHBoxLayout()
        reset_layout.addStretch()
        reset_btn = PushButton("Tümünü Sıfırla")
        reset_btn.clicked.connect(self._on_reset_all_shortcuts)
        reset_layout.addWidget(reset_btn)
        shortcuts_layout.addLayout(reset_layout)
        
        parent_layout.addWidget(shortcuts_card)
    
    def _populate_shortcuts_list(self):
        """Populate the shortcuts list widgets."""
        # Clear existing
        while self.shortcuts_list_layout.count():
            child = self.shortcuts_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        from gui.shortcuts.shortcut_manager import ShortcutManager
        # Use TransparentToolButton for icon buttons if available, else QToolButton
        from qfluentwidgets import TransparentToolButton
        from PySide6.QtWidgets import QKeySequenceEdit
        from PySide6.QtGui import QKeySequence
        
        mgr = ShortcutManager.instance()
        actions = mgr.get_action_map()
        
        # Sort by localized name
        sorted_actions = sorted(actions.items(), key=lambda x: x[1]['name'])
        
        for action_id, info in sorted_actions:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            
            # Label
            name_label = BodyLabel(info['name'])
            name_label.setToolTip(info['desc'])
            name_label.setMinimumWidth(200)
            row_layout.addWidget(name_label)
            
            row_layout.addStretch()
            
            # Editor
            editor = QKeySequenceEdit()
            current_seq = info['sequence']
            if current_seq:
                editor.setKeySequence(QKeySequence(current_seq))
            else:
                editor.setKeySequence(QKeySequence())
            
            editor.setMinimumWidth(150)
            
            # Helper to capture action_id for constraints
            # We connect signal but need to handle conflict logic carefully
            editor.keySequenceChanged.connect(
                lambda seq, aid=action_id, ed=editor: self._on_key_changed(aid, seq, ed)
            )
            
            row_layout.addWidget(editor)
            
            # Reset Button (Icon)
            reset_btn = TransparentToolButton(FIF.ROTATE)
            reset_btn.setToolTip("Varsayılana Döndür")
            reset_btn.clicked.connect(lambda _, aid=action_id: self._on_reset_shortcut(aid))
            row_layout.addWidget(reset_btn)
            
            self.shortcuts_list_layout.addWidget(row_widget)

    def _on_key_changed(self, action_id, key_sequence, editor):
        """Handle key sequence change."""
        from gui.shortcuts.shortcut_manager import ShortcutManager
        from qfluentwidgets import InfoBar, InfoBarPosition
        from PySide6.QtGui import QKeySequence
        
        mgr = ShortcutManager.instance()
        new_seq_str = key_sequence.toString(QKeySequence.PortableText)
        
        # If empty
        if key_sequence.isEmpty():
            mgr.set_sequence(action_id, "")
            return

        try:
            mgr.set_sequence(action_id, new_seq_str)
        except ValueError as e:
            # Conflict detected
            InfoBar.error(
                title="Çakışma Algılandı",
                content=str(e),
                parent=self.window(),
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000
            )
            # Revert UI to old value
            old_seq = mgr.get_sequence(action_id)
            editor.blockSignals(True)
            editor.setKeySequence(QKeySequence(old_seq))
            editor.blockSignals(False)

    def _on_shortcuts_toggle(self, checked):
        """Handle global shortcuts toggle."""
        from models.settings_model import SettingsModel
        SettingsModel.instance().keyboard_shortcuts_enabled = checked
        
        # Refresh UI state (maybe disable editors)
        # For now just update model which updates manager
        
    def _on_reset_shortcut(self, action_id):
        """Reset single shortcut."""
        from gui.shortcuts.shortcut_manager import ShortcutManager
        ShortcutManager.instance().reset_default(action_id)
        self._populate_shortcuts_list() # Re-render to show update
        
    def _on_reset_all_shortcuts(self):
        """Reset all shortcuts."""
        from gui.shortcuts.shortcut_manager import ShortcutManager
        ShortcutManager.instance().reset_all()
        self._populate_shortcuts_list()

    def _on_theme_changed(self, checked: bool):
        """Handle theme toggle."""
        if checked:
            setTheme(Theme.DARK)
            logger.info("Theme switched to DARK")
        else:
            setTheme(Theme.LIGHT)
            logger.info("Theme switched to LIGHT")
    
    def _load_api_key(self):
        """Load saved API key from settings."""
        try:
            from models.settings_model import SettingsModel
            settings = SettingsModel.instance()
            api_key = settings.get("gemini_api_key", "")
            if api_key:
                self.api_key_edit.setText(api_key)
            
            # Also load saved model
            model = settings.get("gemini_model", "gemini-2.5-flash-lite")
            if model:
                index = self.model_combo.findText(model)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)
        except Exception as e:
            logger.error(f"Failed to load API key: {e}")
    
    def _save_api_key(self):
        """Save API key to settings."""
        try:
            from models.settings_model import SettingsModel
            from qfluentwidgets import InfoBar, InfoBarPosition
            
            settings = SettingsModel.instance()
            api_key = self.api_key_edit.text().strip()
            
            if api_key:
                settings.set("gemini_api_key", api_key)
                settings.set("api_key", api_key)  # Legacy support
                settings.save()
                
                # Update environment variable for immediate use
                import os
                os.environ["GEMINI_API_KEY"] = api_key
                
                InfoBar.success(
                    title="Başarılı",
                    content="API anahtarı kaydedildi.",
                    parent=self,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=3000
                )
                logger.info("API key saved successfully")
            else:
                InfoBar.warning(
                    title="Uyarı",
                    content="API anahtarı boş olamaz.",
                    parent=self,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=3000
                )
        except Exception as e:
            logger.error(f"Failed to save API key: {e}")
    
    def _on_model_changed(self, model_name: str):
        """Handle model selection change."""
        try:
            from models.settings_model import SettingsModel
            settings = SettingsModel.instance()
            settings.set("gemini_model", model_name)
            settings.save()
            
            # Update main window reference if available
            main_window = self.window()
            if hasattr(main_window, 'selected_model'):
                main_window.selected_model = model_name
            
            logger.info(f"Model changed to: {model_name}")
        except Exception as e:
            logger.error(f"Failed to save model selection: {e}")

