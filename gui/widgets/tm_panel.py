
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem, 
                             QLabel, QPushButton, QHBoxLayout, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from renforge_logger import get_logger
from core.tm_store import get_tm_manager, TMEntry
from core.change_log import get_change_log, ChangeRecord, ChangeSource
from core import text_utils
from locales import tr
import time

logger = get_logger("gui.widgets.tm_panel")

class TMEntryWidget(QWidget):
    apply_clicked = pyqtSignal()
    
    def __init__(self, entry: TMEntry, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        
        # Score Badge
        score_lbl = QLabel(f"{int(entry.score)}%")
        score_font = QFont()
        score_font.setBold(True)
        score_lbl.setFont(score_font)
        if entry.score >= 90:
            score_lbl.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 4px; padding: 2px;")
        elif entry.score >= 70:
            score_lbl.setStyleSheet("background-color: #FFC107; color: black; border-radius: 4px; padding: 2px;")
        else:
            score_lbl.setStyleSheet("background-color: #9E9E9E; color: white; border-radius: 4px; padding: 2px;")
        layout.addWidget(score_lbl)
        
        # Text
        text_layout = QVBoxLayout()
        tgt_lbl = QLabel(entry.target_text)
        tgt_lbl.setWordWrap(True)
        text_layout.addWidget(tgt_lbl)
        
        src_lbl = QLabel(f"{tr('tm_source_prefix')}{entry.provenance}")
        src_lbl.setStyleSheet("color: gray; font-size: 10px;")
        text_layout.addWidget(src_lbl)
        
        layout.addLayout(text_layout, 1)
        
        # Apply Btn
        apply_btn = QPushButton(tr("tm_btn_apply"))
        apply_btn.clicked.connect(self.apply_clicked.emit)
        apply_btn.setFixedWidth(50)
        layout.addWidget(apply_btn)

class TMPanel(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.tm_manager = get_tm_manager()
        self.current_item = None
        self.current_raw_index = -1
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        # Options
        opt_layout = QHBoxLayout()
        self.safe_mode_chk = QCheckBox(tr("tm_safe_mode"))
        self.safe_mode_chk.setChecked(True)
        opt_layout.addWidget(self.safe_mode_chk)
        layout.addLayout(opt_layout)
        
        # List
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        # Status
        self.status_lbl = QLabel(tr("tm_no_suggestions"))
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("color: gray;")
        layout.addWidget(self.status_lbl)
        
    def on_selection_changed(self):
        items = self.main_window._get_current_translatable_items()
        idx = self.main_window._get_current_item_index()
        
        if not items or idx < 0 or idx >= len(items):
            self.list_widget.clear()
            self.status_lbl.show()
            self.current_item = None
            return

        item = items[idx]
        self.current_item = item
        self.current_raw_index = idx
        
        # Query TM
        source_text = item.original_text or ""
        suggestions = self.tm_manager.lookup(source_text)
        
        self.list_widget.clear()
        
        if not suggestions:
            self.status_lbl.show()
        else:
            self.status_lbl.hide()
            for entry in suggestions:
                item_widget = QListWidgetItem(self.list_widget)
                widget = TMEntryWidget(entry)
                widget.apply_clicked.connect(lambda e=entry: self.apply_suggestion(e))
                
                item_widget.setSizeHint(widget.sizeHint())
                self.list_widget.addItem(item_widget)
                self.list_widget.setItemWidget(item_widget, widget)
                
    def apply_suggestion(self, entry: TMEntry):
        if not self.current_item: return
        
        # Token Check
        if self.safe_mode_chk.isChecked():
            orig_tokens = set(re.findall(r'\[.*?\]', self.current_item.original_text or ""))
            new_tokens = set(re.findall(r'\[.*?\]', entry.target_text))
            
            if orig_tokens != new_tokens:
                QMessageBox.warning(self, tr("tm_safe_mode"), tr("tm_token_mismatch_warning"))
                return
                
        # Apply Logic
        current_data = self.main_window._get_current_file_data()
        items = self.main_window._get_current_translatable_items()
        
        # Capture Undo
        self.main_window.batch_controller.capture_undo_snapshot(
             current_data.file_path, [self.current_raw_index], items, batch_type="tm_apply"
        )
        
        before_text = self.current_item.current_text or ""
        
        # Update Data
        self.current_item.current_text = entry.target_text
        self.current_item.is_modified_session = True
        
        # Update UI
        from gui import gui_table_manager as tm
        table = self.main_window._get_current_table()
        if table:
             tm.update_table_item_text(self.main_window, table, self.current_raw_index, 4, entry.target_text)
             tm.update_table_row_style(table, self.current_raw_index, self.current_item)
             
        self.main_window._set_current_tab_modified(True)
        
        # Log Change
        rec = ChangeRecord(
            timestamp=time.time(),
            file_path=current_data.file_path,
            item_index=self.current_raw_index,
            display_row=(self.current_item.line_index or 0) + 1,
            before_text=before_text,
            after_text=entry.target_text,
            source=ChangeSource.OTHER # Should add TM enum? Using OTHER for now or reuse existing
        )
        get_change_log().add_record(rec)
