
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                             QProgressBar, QCheckBox, QMessageBox, QMenu, QDockWidget)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QAction, QIcon

from renforge_localization import tr
from gui.gui_utils import get_icon
from core.preflight_engine import PreflightEngine, PreflightIssue

class ScanWorker(QThread):
    progress = Signal(int, int, str)
    finished = Signal(list) # list of issues
    error = Signal(str)
    
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        
    def run(self):
        try:
            issues = self.engine.run_scan(self.emit_progress)
            self.finished.emit(issues)
        except Exception as e:
            self.error.emit(str(e))
            
    def emit_progress(self, current, total, msg):
        self.progress.emit(current, total, msg)

class PreflightPanel(QWidget):
    # Signal requested to jump to file/line
    # (file_path, line_number)
    navigate_requested = Signal(str, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = PreflightEngine()
        self.worker = None
        self.current_issues = []
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.btn_run = QPushButton(get_icon("play"), tr("pf_btn_run"))
        self.btn_run.clicked.connect(self.start_scan)
        
        self.btn_cancel = QPushButton(tr("pf_btn_cancel"))
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_scan)
        
        self.btn_export = QPushButton(tr("pf_btn_export_report"))
        self.btn_export.setEnabled(False)
        # self.btn_export.clicked.connect(self.export_report) # TODO: Implement report export
        
        toolbar.addWidget(self.btn_run)
        toolbar.addWidget(self.btn_cancel)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_export)
        
        layout.addLayout(toolbar)
        
        # Status & Progress
        self.status_label = QLabel(tr("pf_status_idle"))
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Filter Checkboxes (Optional future enhancement)
        # filter_layout = QHBoxLayout()
        # filter_layout.addWidget(QLabel("Ciddiyet:"))
        # self.chk_error = QCheckBox("Error")
        # filter_layout.addWidget(self.chk_error)
        # layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            tr("pf_col_severity"), 
            tr("pf_col_file"), 
            tr("pf_col_line"), 
            tr("pf_col_message")
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Icon
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # File 
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Line
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)          # Message
        
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.on_item_double_clicked)
        
        layout.addWidget(self.table)
        
    def start_scan(self):
        if self.worker and self.worker.isRunning():
            return
            
        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.table.setRowCount(0)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(tr("pf_status_running").format(current=0, total="?"))
        
        self.worker = ScanWorker(self.engine)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
        
    def cancel_scan(self):
        if self.engine:
            self.engine.cancel()
        self.btn_cancel.setEnabled(False)
        self.status_label.setText(tr("pf_status_canceled"))

    def on_progress(self, current, total, msg):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(tr("pf_status_running").format(current=current, total=total))
        
    def on_finished(self, issues):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        self.current_issues = issues
        self._populate_table(issues)
        
        err_count = sum(1 for i in issues if i.severity == "error")
        warn_count = sum(1 for i in issues if i.severity == "warning")
        
        self.status_label.setText(tr("pf_status_finished", errors=err_count, warnings=warn_count))
        
    def on_error(self, err_msg):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText(tr("pf_status_error"))
        QMessageBox.critical(self, tr("error"), err_msg)
        
    def _populate_table(self, issues):
        self.table.setRowCount(len(issues))
        for r, issue in enumerate(issues):
            # Severity Icon
            icon_item = QTableWidgetItem(issue.severity.upper())
            # Simple color coding text for now, or icon if available
            if issue.severity == "error":
                icon_item.setBackground(Qt.GlobalColor.red)
                icon_item.setForeground(Qt.GlobalColor.white)
            elif issue.severity == "warning":
                icon_item.setBackground(Qt.GlobalColor.yellow)
                icon_item.setForeground(Qt.GlobalColor.black)
                
            file_item = QTableWidgetItem(os.path.basename(issue.file_path))
            file_item.setToolTip(issue.file_path)
            
            line_item = QTableWidgetItem(str(issue.line_num))
            msg_item = QTableWidgetItem(issue.message)
            
            self.table.setItem(r, 0, icon_item)
            self.table.setItem(r, 1, file_item)
            self.table.setItem(r, 2, line_item)
            self.table.setItem(r, 3, msg_item)
            
    def on_item_double_clicked(self, index):
        row = index.row()
        if row < 0 or row >= len(self.current_issues):
            return
            
        issue = self.current_issues[row]
        self.navigate_requested.emit(issue.file_path, issue.line_num)
