
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                           QPushButton, QHeaderView, QDockWidget, QLabel, QLineEdit, 
                           QComboBox, QMessageBox, QDialog, QFormLayout, QFileDialog, QCheckBox)
from PySide6.QtCore import Qt, Signal
from renforge_logger import get_logger
from locales import tr
from core.glossary_manager import GlossaryManager

logger = get_logger("gui.glossary")

class GlossaryEditDialog(QDialog):
    def __init__(self, parent, source="", target="", mode="case", enabled=True):
        super().__init__(parent)
        self.setWindowTitle(tr("glossary_edit") if source else tr("glossary_add"))
        self.setFixedWidth(400)
        
        layout = QFormLayout(self)
        
        self.source_edit = QLineEdit(source)
        self.target_edit = QLineEdit(target)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItem(tr("glossary_mode_case"), "case")
        self.mode_combo.addItem(tr("glossary_mode_exact"), "exact")
        self.mode_combo.addItem(tr("glossary_mode_regex"), "regex")
        
        index = self.mode_combo.findData(mode)
        if index >= 0:
            self.mode_combo.setCurrentIndex(index)
            
        self.enabled_check = QCheckBox(tr("glossary_col_enabled"))
        self.enabled_check.setChecked(enabled)
        
        layout.addRow(tr("glossary_col_source"), self.source_edit)
        layout.addRow(tr("glossary_col_target"), self.target_edit)
        layout.addRow(tr("glossary_col_mode"), self.mode_combo)
        layout.addRow("", self.enabled_check)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton(tr("menu_save")) # Reuse generic save
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        
    def get_data(self):
        return {
            "source": self.source_edit.text(),
            "target": self.target_edit.text(),
            "mode": self.mode_combo.currentData(),
            "enabled": self.enabled_check.isChecked()
        }

class GlossaryPanel(QDockWidget):
    
    def __init__(self, parent=None):
        super().__init__(tr("glossary_title"), parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.manager = GlossaryManager()
        
        main_widget = QWidget()
        self.setWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton(tr("glossary_add"))
        self.add_btn.clicked.connect(self.add_term)
        self.edit_btn = QPushButton(tr("glossary_edit"))
        self.edit_btn.clicked.connect(self.edit_term)
        self.delete_btn = QPushButton(tr("glossary_delete"))
        self.delete_btn.clicked.connect(self.delete_term)
        
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.delete_btn)
        layout.addLayout(toolbar)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            tr("glossary_col_source"), 
            tr("glossary_col_target"), 
            tr("glossary_col_mode"),
            tr("glossary_col_enabled")
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.doubleClicked.connect(self.edit_term)
        layout.addWidget(self.table)
        
        # Import/Export
        io_layout = QHBoxLayout()
        imp_btn = QPushButton(tr("glossary_import"))
        imp_btn.clicked.connect(self.import_json)
        exp_btn = QPushButton(tr("glossary_export"))
        exp_btn.clicked.connect(self.export_json)
        
        io_layout.addWidget(imp_btn)
        io_layout.addWidget(exp_btn)
        layout.addLayout(io_layout)
        
        self.refresh_table()

    def refresh_table(self):
        self.table.setRowCount(0)
        terms = self.manager.get_terms()
        self.table.setRowCount(len(terms))
        
        for i, term in enumerate(terms):
            source = QTableWidgetItem(term.get("source", ""))
            source.setFlags(source.flags() ^ Qt.ItemFlag.ItemIsEditable)
            
            target = QTableWidgetItem(term.get("target", ""))
            target.setFlags(target.flags() ^ Qt.ItemFlag.ItemIsEditable)
            
            mode_text = term.get("mode", "case")
            if mode_text == "case": mode_display = tr("glossary_mode_case")
            elif mode_text == "exact": mode_display = tr("glossary_mode_exact")
            else: mode_display = tr("glossary_mode_regex")
            
            mode_item = QTableWidgetItem(mode_display)
            mode_item.setFlags(mode_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            
            enabled = QTableWidgetItem("Yes" if term.get("enabled", True) else "No")
            enabled.setFlags(enabled.flags() ^ Qt.ItemFlag.ItemIsEditable)
            
            self.table.setItem(i, 0, source)
            self.table.setItem(i, 1, target)
            self.table.setItem(i, 2, mode_item)
            self.table.setItem(i, 3, enabled)

    def add_term(self):
        dlg = GlossaryEditDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if data["source"]:
                self.manager.add_term(data["source"], data["target"], data["mode"], data["enabled"])
                self.refresh_table()

    def edit_term(self):
        row = self.table.currentRow()
        if row < 0: return
        
        term = self.manager.get_terms()[row]
        dlg = GlossaryEditDialog(self, term["source"], term["target"], term.get("mode", "case"), term.get("enabled", True))
        
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if data["source"]:
                self.manager.update_term(row, data)
                self.refresh_table()

    def delete_term(self):
        row = self.table.currentRow()
        if row < 0: return
        
        reply = QMessageBox.question(self, tr("confirmation"), tr("glossary_confirm_delete"), 
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            term = self.manager.get_terms()[row]
            self.manager.delete_term(term["source"])
            self.refresh_table()

    def import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("glossary_import"), "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            self.manager.add_term(item.get("source"), item.get("target"), 
                                                item.get("mode", "case"), item.get("enabled", True))
                        self.refresh_table()
            except Exception as e:
                logger.error(f"Import failed: {e}")
                QMessageBox.critical(self, tr("error"), str(e))

    def export_json(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("glossary_export"), "glossary.json", "JSON Files (*.json)")
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self.manager.get_terms(), f, indent=4, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Export failed: {e}")
                QMessageBox.critical(self, tr("error"), str(e))
