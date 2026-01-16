
import difflib
import html
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHeaderView, QLabel,
                             QComboBox, QAbstractItemView, QMessageBox, QMenu)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QIcon

from renforge_logger import get_logger
from core.change_log import get_change_log, ChangeRecord, ChangeSource
from locales import tr
import gui.gui_table_manager as tm

logger = get_logger("gui.widgets.review_panel")

def generate_diff_html(a, b):
    # Escape HTML first
    a = html.escape(a)
    b = html.escape(b)
    
    matcher = difflib.SequenceMatcher(None, a, b)
    res = []
    for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
        if opcode == 'equal':
            res.append(a[a0:a1])
        elif opcode == 'insert':
            res.append(f"<span style='background-color:#d4fcbc; color:#2a5e0b'>{b[b0:b1]}</span>")
        elif opcode == 'delete':
            res.append(f"<span style='background-color:#fcd4d4; color:#8a0e0e; text-decoration:line-through'>{a[a0:a1]}</span>")
        elif opcode == 'replace':
            res.append(f"<span style='background-color:#fcd4d4; color:#8a0e0e; text-decoration:line-through'>{a[a0:a1]}</span><span style='background-color:#d4fcbc; color:#2a5e0b'>{b[b0:b1]}</span>")
    return "".join(res)

class ReviewPanel(QWidget):
    request_navigation = Signal(int)
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.change_log = get_change_log()
        self.change_log.add_listener(self.refresh_list)
        
        self.current_records = []
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        # Source Filter
        self.filter_combo = QComboBox()
        self.filter_combo.addItem(tr("review_filter_source"), "all")
        self.filter_combo.addItem(tr("review_source_batch"), ChangeSource.BATCH)
        self.filter_combo.addItem(tr("review_source_replace"), ChangeSource.SEARCH_REPLACE)
        self.filter_combo.addItem(tr("review_source_qa"), ChangeSource.QA_FIX)
        self.filter_combo.addItem(tr("review_source_manual"), ChangeSource.MANUAL)
        self.filter_combo.currentIndexChanged.connect(self.refresh_list)
        toolbar.addWidget(self.filter_combo)
        
        # Actions
        self.revert_btn = QPushButton(tr("review_btn_revert"))
        self.revert_btn.clicked.connect(self.revert_selected)
        toolbar.addWidget(self.revert_btn)
        
        self.accept_btn = QPushButton(tr("review_btn_accept"))
        self.accept_btn.clicked.connect(self.accept_selected)
        toolbar.addWidget(self.accept_btn)
        
        layout.addLayout(toolbar)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([tr("review_col_row"), tr("review_col_diff"), tr("review_col_source")])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.itemDoubleClicked.connect(self.on_dbl_click)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.table)
        
        # Bottom Actions
        bottom_layout = QHBoxLayout()
        self.revert_all = QPushButton(tr("review_btn_revert_all"))
        self.revert_all.clicked.connect(self.revert_all_filtered)
        bottom_layout.addWidget(self.revert_all)
        
        self.accept_all = QPushButton(tr("review_btn_accept_all"))
        self.accept_all.clicked.connect(self.accept_all_filtered)
        bottom_layout.addWidget(self.accept_all)
        
        layout.addLayout(bottom_layout)
        
    def refresh_list(self):
        # Filter logic
        # For now, we only show changes for CURRENT File?
        # "Filter by file_path"
        current_data = self.main_window._get_current_file_data()
        current_path = current_data.file_path if current_data else None
        
        if not current_path:
            self.table.setRowCount(0)
            return

        filter_source = self.filter_combo.currentData()
        
        all_recs = self.change_log.get_records(file_path=current_path)
        
        filtered = []
        for r in all_recs:
            if filter_source != "all" and r.source != filter_source:
                continue
            filtered.append(r)
            
        self.current_records = filtered # Keep reference
        
        self.table.setRowCount(0)
        self.table.setRowCount(len(filtered))
        
        for i, rec in enumerate(filtered):
            # Row
            row_item = QTableWidgetItem(str(rec.display_row))
            row_item.setData(Qt.ItemDataRole.UserRole, rec.item_index)
            self.table.setItem(i, 0, row_item)
            
            # Diff (HTML)
            diff_html = generate_diff_html(rec.before_text, rec.after_text)
            diff_lbl = QLabel(diff_html)
            diff_lbl.setWordWrap(True)
            diff_lbl.setStyleSheet("padding: 2px;")
            self.table.setCellWidget(i, 1, diff_lbl)
            
            # Source
            src_str = tr(f"review_source_{rec.source.value}") if f"review_source_{rec.source.value}" in ["review_source_manual", "review_source_batch", "review_source_qa", "review_source_replace"] else rec.source.value
            src_item = QTableWidgetItem(src_str)
            self.table.setItem(i, 2, src_item)
            
        self.table.resizeRowsToContents()

    def on_dbl_click(self, item):
        row = item.row()
        item_idx_item = self.table.item(row, 0)
        if item_idx_item:
            idx = item_idx_item.data(Qt.ItemDataRole.UserRole)
            self.request_navigation.emit(idx)

    def revert_selected(self):
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        if not rows: return
        
        if QMessageBox.question(self, tr("review_title"), tr("review_revert_confirm")) != QMessageBox.StandardButton.Yes:
            return
            
        records_to_revert = [self.current_records[r] for r in rows]
        self._apply_revert(records_to_revert)

    def revert_all_filtered(self):
        if not self.current_records: return
        if QMessageBox.question(self, tr("review_title"), "Revert ALL visible changes?") != QMessageBox.StandardButton.Yes:
            return
        self._apply_revert(self.current_records)

    def accept_selected(self):
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()), reverse=True)
        if not rows: return
        
        # Remove from log means "Accepted" (History cleared for these items)
        for r in rows:
            rec = self.current_records[r]
            self._feed_tm(rec)
            self.change_log.remove_record(rec)
        self.refresh_list()

    def accept_all_filtered(self):
        if not self.current_records: return
        if QMessageBox.question(self, tr("review_title"), tr("review_accept_confirm")) != QMessageBox.StandardButton.Yes:
            return
        
        for rec in self.current_records:
            self._feed_tm(rec)
            self.change_log.remove_record(rec)
        self.refresh_list()

    def _feed_tm(self, rec):
        # Add to TM as high quality
        # Needed: get_tm_manager()
        from core.tm_store import get_tm_manager
        tm = get_tm_manager()
        # Source is original (before of batch? No, wait)
        # ChangeRecord has: before_text, after_text.
        # BUT for BATCH/SEARCH, before_text is what was there BEFORE. 
        # If I translate English -> Turkish.
        # before_text = "Hello" (English). after_text = "Merhaba" (Turkish).
        # Correct, assuming standard flow.
        # Use before_text as Source.
        
        # provenance: "review_<source>"
        prov = f"review_{rec.source.value}"
        tm.add_entry(rec.before_text, rec.after_text, provenance=prov, reviewed=True)

    def _apply_revert(self, records):
        # Revert means: Set text back to 'before_text'.
        # Capture Undo Snapshot for this Revert Action?
        # "Revert must... create an Undo transaction"
        
        current_data = self.main_window._get_current_file_data()
        if not current_data: return
        
        item_indices = [r.item_index for r in records]
        
        # Capture Undo before Revert
        self.main_window.batch_controller.capture_undo_snapshot(
             current_data.file_path, item_indices, current_data.items, batch_type="review_revert"
        )
        
        # Apply changes
        table = self.main_window._get_current_table()
        
        for rec in records:
            # Revert logic
            # Update data
            if rec.item_index < len(current_data.items):
                 item = current_data.items[rec.item_index]
                 item.current_text = rec.before_text
                 item.is_modified_session = True
                 
                 # Update Table UI
                 if table:
                     tm.update_table_item_text(self.main_window, table, rec.item_index, 4, rec.before_text)
                     tm.update_table_row_style(table, rec.item_index, item)
                     
            # Remove from ChangeLog (since it's reverted, it's no longer a "New Change" to review)
            # OR keep it as "Reverted"? 
            # Usually strict review queues remove item after action.
            self.change_log.remove_record(rec)
            
        self.main_window._set_current_tab_modified(True)
        self.refresh_list()
