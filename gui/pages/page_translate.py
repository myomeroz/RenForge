# -*- coding: utf-8 -*-
"""
RenForge Translate Page

Main translation page with command bar for translation actions.
"""

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from qfluentwidgets import (
    SubtitleLabel, PushButton, PrimaryDropDownPushButton, 
    DropDownPushButton, RoundMenu, Action, BodyLabel,
    FluentIcon as FIF, CommandBar, CommandButton
)

from gui.widgets.shared_table_view import TranslationTableWidget
from gui.widgets.mini_batch_bar import MiniBatchBar
from renforge_logger import get_logger

logger = get_logger("gui.pages.translate")


class TranslatePage(QWidget):
    """
    Translation page with command bar.
    
    Command bar actions:
    - Engine dropdown (Google/Gemini/TM)
    - Seçiliyi Çevir
    - Toplu Çevir
    - İptal
    """
    
    # Signals
    translate_selected_requested = Signal()
    batch_translate_requested = Signal()
    cancel_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TranslatePage")
        
        self._is_batch_running = False
        self._engine = "google"  # Default engine
        self._setup_ui()
        logger.debug("TranslatePage initialized")
    
    def _setup_ui(self):
        """Setup the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)  # Kompakt margins
        layout.setSpacing(12)  # Tutarlı spacing

        # File TabBar (for multi-file support)
        self._setup_file_tab_bar()
        layout.addWidget(self.file_tab_bar)
        
        # Settings bar (User Request restoration)
        self._setup_settings_bar()
        layout.addWidget(self.settings_card)
        
        # Command bar
        self._setup_command_bar()
        layout.addLayout(self.command_bar_layout)
        
        # Mini Batch Bar (compact progress bar for batch operations)
        self.mini_batch_bar = MiniBatchBar(self)
        self.mini_batch_bar.cancel_clicked.connect(self._on_mini_bar_cancel)
        self.mini_batch_bar.show_failed_clicked.connect(self._on_mini_bar_show_failed)
        self.mini_batch_bar.retry_clicked.connect(self._on_mini_bar_retry)
        
        # Report signals (Stage 7)
        self.mini_batch_bar.report_copy_markdown.connect(self._on_report_copy_markdown)
        self.mini_batch_bar.report_save_markdown.connect(self._on_report_save_markdown)
        self.mini_batch_bar.report_save_json.connect(self._on_report_save_json)
        
        layout.addWidget(self.mini_batch_bar)
        
        # Translation table
        self.table_widget = TranslationTableWidget(self)
        self.table_widget.selection_changed.connect(self._on_selection_changed)
        layout.addWidget(self.table_widget)
        
        # Update dropdown text based on default
        self._update_engine_ui()

    def _setup_file_tab_bar(self):
        """Setup the file tabs bar for multi-file support."""
        from PySide6.QtWidgets import QTabBar
        from PySide6.QtCore import Qt
        
        self.file_tab_bar = QTabBar()
        self.file_tab_bar.setTabsClosable(True)
        self.file_tab_bar.setMovable(True)
        self.file_tab_bar.setExpanding(False)
        self.file_tab_bar.setDocumentMode(True)
        
        # Style for dark theme
        self.file_tab_bar.setStyleSheet("""
            QTabBar::tab {
                background: #3d3d3d;
                color: #cccccc;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #0078d4;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background: #4d4d4d;
            }
            QTabBar::close-button {
                image: url(close.png);
                subcontrol-position: right;
            }
            QTabBar::close-button:hover {
                background: #ff4444;
                border-radius: 2px;
            }
        """)
        
        # Connect signals
        self.file_tab_bar.currentChanged.connect(self._on_file_tab_changed)
        self.file_tab_bar.tabCloseRequested.connect(self._on_file_tab_close_requested)
        
        # Initially hidden when no files are open
        self.file_tab_bar.setVisible(False)
        
        logger.debug("File TabBar initialized")

    def _setup_settings_bar(self):
        """Setup the general settings bar (Mode, Languages, Model)."""
        from qfluentwidgets import CardWidget, BodyLabel, ComboBox, FluentIcon, CheckBox, CheckBox
        
        self.settings_card = CardWidget()
        self.settings_card.setFixedHeight(56)  # Daha kompakt
        
        layout = QHBoxLayout(self.settings_card)
        layout.setContentsMargins(16, 8, 16, 8)  # Daha az padding
        layout.setSpacing(16)  # Tutar spacing
        
        # Title "Genel Ayarlar" implicit in grouping or we can add a label
        # Based on screenshot, seems to be a single row.
        
        # Mode
        mode_layout = QHBoxLayout()
        mode_label = BodyLabel("Mod:")
        mode_label.setStyleSheet("font-weight: bold; color: gray;")
        mode_val = BodyLabel("Translate")
        mode_val.setStyleSheet("font-weight: bold;")
        mode_layout.addWidget(mode_label)
        mode_layout.addSpacing(5)
        mode_layout.addWidget(mode_val)
        layout.addLayout(mode_layout)
        
        # Target Language
        target_layout = QHBoxLayout()
        target_layout.addWidget(BodyLabel("Hedef:"))
        self.target_lang_combo = ComboBox()
        self.target_lang_combo.setMinimumWidth(120)
        
        languages = [
            ("English", "en"),
            ("Turkish", "tr"),
            ("German", "de"),
            ("French", "fr"),
            ("Spanish", "es"),
            ("Italian", "it"),
            ("Portuguese", "pt"),
            ("Russian", "ru"),
            ("Japanese", "ja"),
            ("Chinese (Simplified)", "zh-CN")
        ]
        
        for name, code in languages:
            self.target_lang_combo.addItem(name, code)
        self.target_lang_combo.setCurrentIndex(1) # Default Turkish
        
        target_layout.addWidget(self.target_lang_combo)
        layout.addLayout(target_layout)
        
        # Source Language
        source_layout = QHBoxLayout()
        source_layout.addWidget(BodyLabel("Kaynak:"))
        self.source_lang_combo = ComboBox()
        self.source_lang_combo.setMinimumWidth(120)
        
        for name, code in languages:
            self.source_lang_combo.addItem(name, code)
        self.source_lang_combo.setCurrentIndex(0) # Default English
        
        source_layout.addWidget(self.source_lang_combo)
        layout.addLayout(source_layout)
        
        # Model
        model_layout = QHBoxLayout()
        model_layout.addWidget(BodyLabel("Gemini Model:"))
        self.model_combo = ComboBox()
        self.model_combo.setMinimumWidth(200)
        self.model_combo.addItem("models/gemini-2.0-flash")
        self.model_combo.addItem("models/gemini-1.5-pro")
        self.model_combo.addItem("models/gemini-1.5-flash")
        self.model_combo.setCurrentText("models/gemini-2.0-flash")
        
        model_layout.addWidget(self.model_combo)
        layout.addLayout(model_layout)
        
        layout.addStretch()
        
        # Connect signals
        self.target_lang_combo.currentIndexChanged.connect(self._on_target_lang_changed)
        self.source_lang_combo.currentIndexChanged.connect(self._on_source_lang_changed)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        
        # Errors Only Toggle (Stage 5.5)
        self.errors_only_chk = CheckBox("Sadece Hatalılar")
        self.errors_only_chk.stateChanged.connect(self._on_errors_only_toggled)
        layout.addWidget(self.errors_only_chk)
        
        # QC Only Toggle (Stage 6)
        self.problems_only_chk = CheckBox("Sadece Sorunlular")
        self.problems_only_chk.stateChanged.connect(self._on_problems_only_toggled)
        layout.addWidget(self.problems_only_chk)
        
        layout.addStretch()
        
        # Emit initial signals to sync state
        QTimer.singleShot(0, lambda: self._on_target_lang_changed())
        QTimer.singleShot(0, lambda: self._on_source_lang_changed())
        QTimer.singleShot(0, lambda: self._on_model_changed(self.model_combo.currentText()))

    def _on_target_lang_changed(self):
        """Handle target language change."""
        code = self.target_lang_combo.currentData()
        if code:
            self.window().target_language_changed.emit(code)
            logger.debug(f"Emitted target_language_changed: {code}")

    def _on_source_lang_changed(self):
        """Handle source language change."""
        code = self.source_lang_combo.currentData()
        if code:
            self.window().source_language_changed.emit(code)
            logger.debug(f"Emitted source_language_changed: {code}")

    def _on_model_changed(self, text):
        """Handle model change."""
        if text:
            self.window().model_changed.emit(text)
            logger.debug(f"Emitted model_changed: {text}")

    def _on_errors_only_toggled(self, state):
        """Handle errors only toggle."""
        # CheckBox state: 0=Unchecked, 2=Checked.
        is_checked = (state == 2)
        target_filter = "error" if is_checked else "all"
        
        # We need to set this on the SharedTableView's filter logic
        if hasattr(self, 'table_widget') and hasattr(self.table_widget, 'filter_segment'):
            # This updates the segmented widget (Top Bar) -> triggers its signal -> updates proxy
            self.table_widget.filter_segment.setCurrentItem(target_filter)

    def _on_problems_only_toggled(self, state):
        """Handle QC problems only toggle."""
        # CheckBox state: 0=Unchecked, 2=Checked
        is_checked = (state == 2)
        
        # Access proxy via the table widget
        # TableWidget -> generic_table -> model() which should be the proxy
        if hasattr(self, 'table_widget'):
            # Try to get proxy from table widget API if exists, or drill down
            proxy = None
            if hasattr(self.table_widget, 'get_proxy_model'):
                proxy = self.table_widget.get_proxy_model()
            elif hasattr(self.table_widget, 'view'):
                 proxy = self.table_widget.view.model()
            elif hasattr(self.table_widget, 'table_view'): # Fallback naming
                 proxy = self.table_widget.table_view.model()
            
            if proxy and hasattr(proxy, 'set_qc_filter'):
                proxy.set_qc_filter(is_checked)
            else:
                from renforge_logger import get_logger
                logger = get_logger("gui.pages.translate")
                logger.warning("Could not set QC filter - proxy not found or incompatible")

    def _update_engine_ui(self):
        """Update dropdown text and icon based on selected engine."""
        if self._engine == "google":
            self.engine_dropdown.setText("Google Translate")
            self.engine_dropdown.setIcon(FIF.GLOBE)
        elif self._engine == "gemini":
            self.engine_dropdown.setText("Gemini AI")
            self.engine_dropdown.setIcon(FIF.ROBOT)
        elif self._engine == "tm":
            self.engine_dropdown.setText("Translation Memory")
            self.engine_dropdown.setIcon(FIF.HISTORY)
            
    def _setup_command_bar(self):
        """Setup the command bar with translation actions."""
        self.command_bar_layout = QHBoxLayout()
        self.command_bar_layout.setSpacing(8)
        
        # Engine dropdown (left side)
        self.engine_dropdown = DropDownPushButton("Google Translate")
        self.engine_dropdown.setIcon(FIF.GLOBE)
        
        engine_menu = RoundMenu(parent=self)
        self.google_action = Action(FIF.GLOBE, "Google Translate")
        self.google_action.triggered.connect(lambda: self._set_engine("google"))
        self.gemini_action = Action(FIF.ROBOT, "Gemini AI")
        self.gemini_action.triggered.connect(lambda: self._set_engine("gemini"))
        self.tm_action = Action(FIF.HISTORY, "Translation Memory")
        self.tm_action.triggered.connect(lambda: self._set_engine("tm"))
        
        engine_menu.addAction(self.google_action)
        engine_menu.addAction(self.gemini_action)
        engine_menu.addSeparator()
        engine_menu.addAction(self.tm_action)
        
        self.engine_dropdown.setMenu(engine_menu)
        self.command_bar_layout.addWidget(self.engine_dropdown)
        
        # Separator
        self.command_bar_layout.addSpacing(16)
        
        # === PRIMARY ACTIONS ===
        
        # Seçiliyi Çevir (primary action - visible)
        self.translate_selected_btn = PushButton("Seçiliyi Çevir")
        self.translate_selected_btn.setIcon(FIF.EDIT)
        self.translate_selected_btn.clicked.connect(self._on_translate_selected)
        self.command_bar_layout.addWidget(self.translate_selected_btn)
        
        # Toplu Çevir (primary action - always visible)
        self.batch_translate_btn = PushButton("Toplu Çevir")
        self.batch_translate_btn.setIcon(FIF.SYNC)
        self.batch_translate_btn.clicked.connect(self._on_batch_translate)
        self.command_bar_layout.addWidget(self.batch_translate_btn)
        
        # İptal (visible only when batch running)
        self.cancel_btn = PushButton("İptal")
        self.cancel_btn.setIcon(FIF.CLOSE)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setVisible(False)  # Hidden by default
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.command_bar_layout.addWidget(self.cancel_btn)
        
        # Separator
        self.command_bar_layout.addSpacing(8)
        
        # Kaydet ▼ (menu button with save options)
        self.save_menu_btn = DropDownPushButton("Kaydet")
        self.save_menu_btn.setIcon(FIF.SAVE)
        
        save_menu = RoundMenu(parent=self)
        self.save_action = Action(FIF.SAVE, "Kaydet")
        self.save_action.triggered.connect(self._on_save)
        self.save_as_action = Action(FIF.SAVE_AS, "Farklı Kaydet...")
        self.save_as_action.triggered.connect(self._on_save_as)
        
        save_menu.addAction(self.save_action)
        save_menu.addAction(self.save_as_action)
        
        self.save_menu_btn.setMenu(save_menu)
        self.command_bar_layout.addWidget(self.save_menu_btn)
        
        # More menu (…) for secondary actions
        self.more_menu_btn = DropDownPushButton()
        self.more_menu_btn.setIcon(FIF.MORE)
        self.more_menu_btn.setToolTip("Diğer Eylemler")
        self.more_menu_btn.setFixedWidth(40)
        
        more_menu = RoundMenu(parent=self)
        
        # Inspector shortcuts
        self.open_log_action = Action(FIF.DOCUMENT, "Log'u Aç")
        self.open_log_action.triggered.connect(self._on_open_log)
        more_menu.addAction(self.open_log_action)
        
        self.open_batch_detail_action = Action(FIF.VIEW, "Toplu İşlem Detayı")
        self.open_batch_detail_action.triggered.connect(self._on_open_batch_detail)
        more_menu.addAction(self.open_batch_detail_action)
        
        self.more_menu_btn.setMenu(more_menu)
        self.command_bar_layout.addWidget(self.more_menu_btn)
        
        self.command_bar_layout.addStretch()
        
        # Selection info (right side)
        self.selection_label = BodyLabel("0 satır seçili")
        self.command_bar_layout.addWidget(self.selection_label)
    
    def _on_open_log(self):
        """Open Log tab in Inspector."""
        main_window = self.window()
        if hasattr(main_window, 'inspector'):
            main_window.inspector.setVisible(True)
            main_window.inspector.tabs.setCurrentIndex(2)  # Log tab
    
    def _on_open_batch_detail(self):
        """Open Batch tab in Inspector."""
        main_window = self.window()
        if hasattr(main_window, 'inspector'):
            main_window.inspector.setVisible(True)
            main_window.inspector.tabs.setCurrentIndex(1)  # Batch tab
    
    # =========================================================================
    # ACTION HANDLERS
    # =========================================================================
    
    def _set_engine(self, engine: str):
        """Set the active translation engine."""
        self._engine = engine
        self._update_engine_ui()
        logger.debug(f"Engine selected: {engine}")
    
    def _on_translate_selected(self):
        """Handle translate selected action - dispatched based on engine."""
        main_window = self.window()
        
        if self._engine == "google":
            if hasattr(main_window, 'translate_google_requested'):
                main_window.translate_google_requested.emit()
                logger.debug("Emitted translate_google_requested")
        elif self._engine == "gemini":
            if hasattr(main_window, 'translate_ai_requested'):
                main_window.translate_ai_requested.emit()
                logger.debug("Emitted translate_ai_requested")
        elif self._engine == "tm":
            from qfluentwidgets import InfoBar
            InfoBar.info(
                title="TM Modu",
                content="Translation Memory çevirisi henüz aktif değil.",
                parent=self,
                duration=3000
            )
    
    def _on_batch_translate(self):
        """Handle batch translate action - dispatched based on engine.
        
        NOT: Butonlar burada disable EDİLMİYOR!
        Onay dialogu gösterildikten ve kullanıcı "Evet" dedikten sonra
        handler'lar (batch_controller vb.) set_batch_running(True) çağırıyor.
        Bu sayede "Hayır" dendiğinde butonlar disabled kalmıyor.
        """
        import os
        trace = os.environ.get('RENFORGE_UI_STATE_TRACE') == '1'
        
        main_window = self.window()
        
        # Check if any rows are selected
        selected = self.get_selected_rows()
        if not selected:
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.warning(
                title="Satır Seçilmedi",
                content="Lütfen çevirmek için en az bir satır seçin.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return
        
        if trace:
            logger.info(f"[UI_STATE_TRACE] _on_batch_translate: engine={self._engine}, selected={len(selected)}")
        
        # ÖNEMLİ: BURADA set_batch_running(True) ÇAĞIRMA!
        # Handler'lar onay dialogu sonrası bunu yapacak.
        
        if self._engine == "google":
            if hasattr(main_window, 'batch_google_requested'):
                main_window.batch_google_requested.emit()
                logger.debug("Emitted batch_google_requested")
        elif self._engine == "gemini":
            if hasattr(main_window, 'batch_ai_requested'):
                main_window.batch_ai_requested.emit()
                logger.debug("Emitted batch_ai_requested")
        elif self._engine == "tm":
            from qfluentwidgets import InfoBar
            InfoBar.info(
                title="TM Modu",
                content="Toplu TM çevirisi henüz aktif değil.",
                parent=self,
                duration=3000
            )
            
    def _on_save(self):
        """Handle save action."""
        main_window = self.window()
        if hasattr(main_window, 'save_requested'):
            main_window.save_requested.emit()
            logger.info("Save requested via TranslatePage")

    def _on_save_as(self):
        """Handle save as action."""
        main_window = self.window()
        if hasattr(main_window, 'save_as_requested'):
            main_window.save_as_requested.emit()
            logger.info("Save As requested via TranslatePage")

    def _on_cancel(self):
        """Handle cancel action - cancels current batch operation."""
        self.cancel_requested.emit()
        main_window = self.window()
        
        # Try to cancel via batch controller if available
        if hasattr(main_window, 'batch_controller') and main_window.batch_controller:
            # Check if controller has cancel method
            if hasattr(main_window.batch_controller, 'cancel'):
                main_window.batch_controller.cancel()
            logger.info("Cancel requested via TranslatePage")
            
        # Also emit via inspector if available
        if hasattr(main_window, 'inspector') and main_window.inspector:
            main_window.inspector.cancel_batch_requested.emit()
        
        # IMPORTANT: Batch durumunu sıfırla ve butonları aktif et
        self.set_batch_running(False)
    
    def _on_mini_bar_cancel(self):
        """Handle cancel from MiniBatchBar - delegates to batch controller."""
        main_window = self.window()
        
        if hasattr(main_window, 'batch_controller') and main_window.batch_controller:
            if hasattr(main_window.batch_controller, 'cancel'):
                main_window.batch_controller.cancel()
                logger.info("Cancel requested via MiniBatchBar")
    
    def _on_mini_bar_show_failed(self):
        """Handle request to show failed items."""
        # 1. Switch filter to 'error' (Hatalı)
        if hasattr(self.table_widget, 'set_filter'):
            self.table_widget.set_filter("error")
        
        if hasattr(self.table_widget, 'scroll_to_top'):
            self.table_widget.scroll_to_top()
            
    def _on_mini_bar_retry(self):
        """Handle request to retry failed items."""
        main_window = self.window()
        if hasattr(main_window, 'batch_controller') and main_window.batch_controller:
            logger.info("Retry Failed requested via MiniBatchBar")
            main_window.batch_controller.retry_failed_last_run()
            
        logger.info("Switched to 'error' filter via MiniBatchBar")
    
    # =========================================================================
    # REPORT HANDLERS (Stage 7)
    # =========================================================================
    
    def _on_report_copy_markdown(self):
        """Copy batch report as Markdown to clipboard."""
        main_window = self.window()
        if hasattr(main_window, 'batch_controller') and main_window.batch_controller:
            bc = main_window.batch_controller
            if bc.has_last_run():
                if bc.copy_report_markdown():
                    from qfluentwidgets import InfoBar, InfoBarPosition
                    InfoBar.success(
                        title="Panoya Kopyalandı",
                        content="Rapor Markdown formatında panoya kopyalandı.",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                else:
                    from qfluentwidgets import InfoBar, InfoBarPosition
                    InfoBar.error(
                        title="Hata",
                        content="Rapor oluşturulamadı.",
                        parent=self
                    )
            else:
                from qfluentwidgets import InfoBar, InfoBarPosition
                InfoBar.info(
                    title="Bilgi",
                    content="Henüz rapor oluşturulacak bir işlem yok.",
                    parent=self
                )
    
    def _on_report_save_markdown(self):
        """Save batch report as Markdown file."""
        from PySide6.QtWidgets import QFileDialog
        
        main_window = self.window()
        if not hasattr(main_window, 'batch_controller') or not main_window.batch_controller:
            return
            
        bc = main_window.batch_controller
        if not bc.has_last_run():
            from qfluentwidgets import InfoBar
            InfoBar.info(
                title="Bilgi",
                content="Henüz rapor oluşturulacak bir işlem yok.",
                parent=self
            )
            return
        
        # Generate filename suggestion
        from datetime import datetime
        default_name = f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Raporu Kaydet (Markdown)",
            default_name,
            "Markdown Files (*.md);;All Files (*)"
        )
        
        if path:
            if bc.save_report_markdown(path):
                from qfluentwidgets import InfoBar, InfoBarPosition
                InfoBar.success(
                    title="Kaydedildi",
                    content=f"Rapor kaydedildi: {path}",
                    parent=self
                )
            else:
                from qfluentwidgets import InfoBar
                InfoBar.error(
                    title="Hata",
                    content="Rapor kaydedilemedi.",
                    parent=self
                )
    
    def _on_report_save_json(self):
        """Save batch report as JSON file."""
        from PySide6.QtWidgets import QFileDialog
        
        main_window = self.window()
        if not hasattr(main_window, 'batch_controller') or not main_window.batch_controller:
            return
            
        bc = main_window.batch_controller
        if not bc.has_last_run():
            from qfluentwidgets import InfoBar
            InfoBar.info(
                title="Bilgi",
                content="Henüz rapor oluşturulacak bir işlem yok.",
                parent=self
            )
            return
        
        # Generate filename suggestion
        from datetime import datetime
        default_name = f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Raporu Kaydet (JSON)",
            default_name,
            "JSON Files (*.json);;All Files (*)"
        )
        
        if path:
            if bc.save_report_json(path):
                from qfluentwidgets import InfoBar, InfoBarPosition
                InfoBar.success(
                    title="Kaydedildi",
                    content=f"Rapor kaydedildi: {path}",
                    parent=self
                )
            else:
                from qfluentwidgets import InfoBar
                InfoBar.error(
                    title="Hata",
                    content="Rapor kaydedilemedi.",
                    parent=self
                )
    
    def select_line(self, line_num):
        """Select a line in the table."""
        if hasattr(self, 'table_widget'):
             self.table_widget.select_line(line_num)
             
    def select_row_by_index(self, row_index: int):
        """
        Select row by internal 0-based row index.
        Wrapper for table_widget.select_row_by_index.
        """
        if hasattr(self, 'table_widget'):
            self.table_widget.select_row_by_index(row_index)
             
    def _on_selection_changed(self, row_data: dict):
        """Handle table selection changed."""
        # Merkezi state güncelleme
        self._update_action_states()
        
        # Update inspector
        main_window = self.window()
        if hasattr(main_window, 'inspector'):
            main_window.inspector.show_row(row_data)
    
    def showEvent(self, event):
        """Override to update action states when page shown."""
        super().showEvent(event)
        # State'i güncelle
        self._update_action_states()
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def set_batch_running(self, running: bool):
        """Set batch operation running state."""
        self._is_batch_running = running
        self._update_action_states()
    
    def _update_action_states(self):
        """
        Merkezi buton state güncelleme metodu.
        
        Tüm action butonlarını mevcut duruma göre günceller:
        - selection_count
        - batch_running
        - has_file
        - has_changes
        
        Debug: RENFORGE_UI_STATE_TRACE=1 ile detaylı log
        """
        import os
        trace = os.environ.get('RENFORGE_UI_STATE_TRACE') == '1'
        
        # Selection count
        selection_count = 0
        if hasattr(self, 'table_widget') and hasattr(self.table_widget, 'table_view'):
            selection = self.table_widget.table_view.selectionModel()
            if selection:
                selection_count = len(selection.selectedRows(0))
        
        # File state
        main_window = self.window()
        has_file = False
        row_count = 0
        
        if main_window and hasattr(main_window, 'current_file_path'):
            has_file = bool(main_window.current_file_path)
        
        # Row count - birden fazla yöntem dene
        if hasattr(self, 'table_widget'):
            # Yöntem 1: TranslationTableWidget.rowCount()
            try:
                row_count = self.table_widget.rowCount()
            except Exception:
                pass
            
            # Yöntem 2: Model'den al
            if row_count == 0:
                try:
                    model = self.table_widget.model()
                    if model:
                        row_count = model.rowCount()
                except Exception:
                    pass
            
            # Yöntem 3: table_view'dan al
            if row_count == 0:
                try:
                    if hasattr(self.table_widget, 'table_view'):
                        model = self.table_widget.table_view.model()
                        if model:
                            row_count = model.rowCount()
                except Exception:
                    pass
        
        # Batch running state - iç state kullan
        batch_running = self._is_batch_running
        
        if trace:
            logger.info(f"[UI_STATE_TRACE] _update_action_states: "
                       f"batch_running={batch_running}, selection={selection_count}, "
                       f"row_count={row_count}, has_file={has_file}")
        
        # === BUTON KURALLARI ===
        
        # Seçiliyi Çevir: selection > 0 VE batch çalışmıyor
        translate_enabled = selection_count > 0 and not batch_running
        if hasattr(self, 'translate_selected_btn'):
            self.translate_selected_btn.setEnabled(translate_enabled)
        
        # Toplu Çevir: dosya açık VE batch çalışmıyor
        batch_enabled = has_file and not batch_running
        self.batch_translate_btn.setEnabled(batch_enabled)
        
        # İptal: visible + enabled only when batch running
        self.cancel_btn.setVisible(batch_running)
        self.cancel_btn.setEnabled(batch_running)
        
        # Kaydet menu: enabled when file is open
        if hasattr(self, 'save_menu_btn'):
            self.save_menu_btn.setEnabled(has_file)
        
        # Selection label güncelle
        self.selection_label.setText(f"{selection_count} satır seçili")
        
        if trace:
            logger.info(f"[UI_STATE_TRACE] Final: translate_action={translate_enabled}, "
                       f"batch_btn={batch_enabled}, cancel_btn={batch_running}")
    
    def get_selected_rows(self) -> list:
        """Get selected row IDs."""
        return self.table_widget.get_selected_row_ids()
    
    def get_source_language_code(self) -> str:
        """Get selected source language code safely."""
        if hasattr(self, 'source_lang_combo'):
            idx = self.source_lang_combo.currentIndex()
            data = self.source_lang_combo.itemData(idx)
            if data:
                return data
        return "en"  # Default fallback
    
    def get_target_language_code(self) -> str:
        """Get selected target language code safely."""
        if hasattr(self, 'target_lang_combo'):
            idx = self.target_lang_combo.currentIndex()
            data = self.target_lang_combo.itemData(idx)
            if data:
                return data
        return "tr"  # Default fallback
    
    def get_source_language_name(self) -> str:
        """Get selected source language name."""
        if hasattr(self, 'source_lang_combo'):
            return self.source_lang_combo.currentText()
        return "English"
    
    def get_target_language_name(self) -> str:
        """Get selected target language name."""
        if hasattr(self, 'target_lang_combo'):
            return self.target_lang_combo.currentText()
        return "Turkish"
    
    # =========================================================================
    # FILE TAB MANAGEMENT
    # =========================================================================
    
    def _on_file_tab_changed(self, index: int):
        """Handle file tab selection changed."""
        if index < 0:
            return
        
        # Get file path from tab data
        file_path = self.file_tab_bar.tabData(index)
        if not file_path:
            return
        
        # Notify main window to switch file
        main_window = self.window()
        if hasattr(main_window, 'switch_to_file'):
            main_window.switch_to_file(file_path)
            logger.debug(f"Tab changed to: {file_path}")
    
    def _on_file_tab_close_requested(self, index: int):
        """Handle file tab close button clicked."""
        if index < 0:
            return
        
        # Get file path from tab data
        file_path = self.file_tab_bar.tabData(index)
        if not file_path:
            return
        
        # Notify main window to close file
        main_window = self.window()
        if hasattr(main_window, 'close_file_tab'):
            main_window.close_file_tab(file_path)
            logger.info(f"Tab close requested: {file_path}")
    
    def add_file_tab(self, file_path: str, display_name: str) -> int:
        """
        Add a new file tab.
        
        Args:
            file_path: Full path to the file (stored as tab data)
            display_name: Display name for the tab (usually basename)
            
        Returns:
            Tab index
        """
        # Check if tab already exists
        for i in range(self.file_tab_bar.count()):
            if self.file_tab_bar.tabData(i) == file_path:
                return i
        
        # Add new tab
        idx = self.file_tab_bar.addTab(display_name)
        self.file_tab_bar.setTabData(idx, file_path)
        self.file_tab_bar.setTabToolTip(idx, file_path)
        
        # Show tab bar when we have tabs
        self.file_tab_bar.setVisible(True)
        
        # Select the new tab
        self.file_tab_bar.setCurrentIndex(idx)
        
        logger.debug(f"Added file tab: {display_name} at index {idx}")
        return idx
    
    def remove_file_tab(self, file_path: str) -> bool:
        """
        Remove a file tab.
        
        Args:
            file_path: Path to the file to remove
            
        Returns:
            True if removed successfully
        """
        for i in range(self.file_tab_bar.count()):
            if self.file_tab_bar.tabData(i) == file_path:
                self.file_tab_bar.removeTab(i)
                
                # Hide tab bar if no tabs left
                if self.file_tab_bar.count() == 0:
                    self.file_tab_bar.setVisible(False)
                
                logger.debug(f"Removed file tab for: {file_path}")
                return True
        
        return False
    
    def focus_file_tab(self, file_path: str) -> bool:
        """
        Focus an existing file tab.
        
        Args:
            file_path: Path to the file to focus
            
        Returns:
            True if found and focused
        """
        for i in range(self.file_tab_bar.count()):
            if self.file_tab_bar.tabData(i) == file_path:
                self.file_tab_bar.blockSignals(True)
                self.file_tab_bar.setCurrentIndex(i)
                self.file_tab_bar.blockSignals(False)
                return True
        
        return False
