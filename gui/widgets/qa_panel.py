
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHeaderView, QLabel,
                             QCheckBox, QAbstractItemView, QMenu, QLineEdit)
from PySide6.QtCore import Qt, Signal, QThread, Slot
from PySide6.QtGui import QColor, QIcon, QAction

from renforge_logger import get_logger
from core.qa_engine import QAEngine, QAIssue, QASeverity
from locales import tr


logger = get_logger("gui.widgets.qa_panel")

class QAWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(list)
    
    def __init__(self, engine, items):
        super().__init__()
        self.engine = engine
        self.items = items
        self.is_cancelled = False
        
    def run(self):
        def cb(curr, total):
            if self.is_cancelled: return False
            if curr % 100 == 0: self.progress.emit(curr, total)
            return True
            
        results = self.engine.scan(self.items, cb)
        self.finished.emit(results)
        
    def cancel(self):
        self.is_cancelled = True

class QAPanel(QWidget):
    request_navigation = Signal(int) # raw_index
    request_refresh_overlay = Signal()
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.engine = QAEngine()
        self.issues = []
        self.worker = None
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.run_btn = QPushButton(tr("qa_run_btn"))
        self.run_btn.setIcon(QIcon("pics/play.svg")) # Use generic play icon if available
        self.run_btn.clicked.connect(self.run_scan)
        toolbar.addWidget(self.run_btn)
        
        self.auto_chk = QCheckBox(tr("qa_auto_chk"))
        self.auto_chk.setToolTip("Run QA automatically on file load")
        toolbar.addWidget(self.auto_chk)
        
        layout.addLayout(toolbar)
        
        # Filter/Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter issues...")
        self.search_input.textChanged.connect(self.filter_issues)
        layout.addWidget(self.search_input)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([tr("qa_col_severity"), tr("qa_col_line"), tr("qa_col_message"), ""])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemDoubleClicked.connect(self.on_item_dbl_click)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.table)
        
        # Status
        self.status_lbl = QLabel(tr("qa_no_issues"))
        layout.addWidget(self.status_lbl)
        
    def run_scan(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
            
        items = self.main_window._get_current_translatable_items()
        if not items:
            self.status_lbl.setText("No items to scan.")
            return
            
        self.run_btn.setEnabled(False)
        self.status_lbl.setText(tr("qa_status_scanning", progress=0))
        
        self.worker = QAWorker(self.engine, items)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.start()
        
    def on_progress(self, curr, total):
        pct = int((curr / total) * 100)
        self.status_lbl.setText(tr("qa_status_scanning", progress=pct))
        
    def on_scan_finished(self, issues):
        self.run_btn.setEnabled(True)
        self.issues = issues
        self.update_table(issues)
        self.status_lbl.setText(tr("qa_status_done", count=len(issues)))
        self.worker = None
        
    def update_table(self, issues):
        self.table.setRowCount(0)
        filter_text = self.search_input.text().lower()
        
        visible_issues = []
        for issue in issues:
            if filter_text and filter_text not in issue.message.lower():
                continue
            visible_issues.append(issue)
            
        self.table.setRowCount(len(visible_issues))
        
        for i, issue in enumerate(visible_issues):
            # Severity
            sev_item = QTableWidgetItem(issue.severity.value.upper())
            if issue.severity == QASeverity.ERROR:
                sev_item.setForeground(QColor("red"))
            elif issue.severity == QASeverity.WARNING:
                sev_item.setForeground(QColor("orange"))
            else:
                sev_item.setForeground(QColor("lightblue"))
            
            # Line
            line_item = QTableWidgetItem(str(issue.line_index))
            line_item.setData(Qt.ItemDataRole.UserRole, issue.raw_index) # Store raw index
            
            # Message
            msg_item = QTableWidgetItem(issue.message)
            msg_item.setToolTip(issue.message)
            
            self.table.setItem(i, 0, sev_item)
            self.table.setItem(i, 1, line_item)
            self.table.setItem(i, 2, msg_item)
            
            # Fix Button? (Maybe just context menu to save space)
            # If fixable, add icon?
            if issue.can_fix:
                fix_item = QTableWidgetItem("🔧")
                fix_item.setToolTip(tr("qa_col_fix"))
                self.table.setItem(i, 3, fix_item)

    def filter_issues(self):
        self.update_table(self.issues)
        
    def on_item_dbl_click(self, item):
        row = item.row()
        raw_index_item = self.table.item(row, 1) # Line Col has data
        if raw_index_item:
            raw_index = raw_index_item.data(Qt.ItemDataRole.UserRole)
            self.request_navigation.emit(raw_index)
            
    def open_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item: return
        
        row = item.row()
        # Find issue object
        # O(N) lookup in current list... 
        # Better: Store issue object in UserRole of Col 0?
        # Re-map row to local issue list would require syncing.
        # Simple: Get raw_index and message, find in self.issues
        
        raw_index_item = self.table.item(row, 1)
        raw_index = raw_index_item.data(Qt.ItemDataRole.UserRole)
        msg = self.table.item(row, 2).text()
        
        target_issue = None
        for iss in self.issues:
            if iss.raw_index == raw_index and iss.message == msg:
                target_issue = iss
                break
                
        menu = QMenu()
        nav_action = menu.addAction("Go to Line")
        fix_action = None
        if target_issue and target_issue.can_fix:
             fix_action = menu.addAction(tr("qa_col_fix"))
             
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        
        if action == nav_action:
             self.request_navigation.emit(raw_index)
        elif action == fix_action and target_issue:
             self.apply_fix(target_issue)
             
    def apply_fix(self, issue):
        items = self.main_window._get_current_translatable_items()
        if not items or issue.raw_index >= len(items): return
        
        item = items[issue.raw_index]
        
        # Undo Snapshot
        current_data = self.main_window._get_current_file_data()
        self.main_window.batch_controller.capture_undo_snapshot(
             current_data.file_path, [issue.raw_index], items, batch_type="qa_fix"
        )
        
        before_text = item.current_text or ""
        
        if self.engine.fix_issue(item, issue):
             # Stage 10: Change Logging
             from core.change_log import get_change_log, ChangeRecord, ChangeSource
             import time
             
             rec = ChangeRecord(
                timestamp=time.time(),
                file_path=current_data.file_path,
                item_index=issue.raw_index,
                display_row=issue.line_index,
                before_text=before_text,
                after_text=item.current_text,
                source=ChangeSource.QA_FIX
             )
             get_change_log().add_record(rec)
             
             # Update table row?
             from gui import gui_table_manager as tm
             table = self.main_window._get_current_table()
             if table:
                  tm.update_table_item_text(self.main_window, table, issue.raw_index, 4, item.current_text)
                  tm.update_table_row_style(table, issue.raw_index, item)
                  
             self.main_window._set_current_tab_modified(True)
             
             # Remove issue from list? or just refresh?
             self.issues.remove(issue)
             self.update_table(self.issues)
