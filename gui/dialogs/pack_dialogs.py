
import os
from pathlib import Path

from renforge_logger import get_logger
from renforge_localization import tr

try:
    from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                               QLineEdit, QCheckBox, QComboBox, QFileDialog, QProgressBar, 
                               QGroupBox, QTextEdit, QMessageBox)
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
except ImportError:
    pass

from core.packaging import PackManager, HAS_CRYPTO

logger = get_logger("gui.pack_dialogs")

class ExportRequest:
    def __init__(self, path, options, password):
        self.path = path
        self.options = options
        self.password = password

class ExportWorker(QThread):
    finished = pyqtSignal(bool, str) # success, message
    
    def __init__(self, request: ExportRequest):
        super().__init__()
        self.request = request
        
    def run(self):
        try:
            pack_mgr = PackManager()
            pack_mgr.export_pack(self.request.path, self.request.options, self.request.password)
            self.finished.emit(True, tr("pack_export_success"))
        except Exception as e:
            self.finished.emit(False, str(e))

class ImportWorker(QThread):
    finished = pyqtSignal(list, str) # report, error
    
    def __init__(self, path, strategies, password):
        super().__init__()
        self.path = path
        self.strategies = strategies
        self.password = password
        
    def run(self):
        try:
            pack_mgr = PackManager()
            report = pack_mgr.import_pack(self.path, self.strategies, self.password)
            self.finished.emit(report, "")
        except Exception as e:
            self.finished.emit([], str(e))


class ExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("pack_export_title"))
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Options Group
        opts_group = QGroupBox(tr("pack_export_options"))
        opts_layout = QVBoxLayout()
        
        self.chk_settings = QCheckBox(tr("pack_opt_settings"))
        self.chk_settings.setChecked(True)
        self.chk_glossary = QCheckBox(tr("pack_opt_glossary"))
        self.chk_glossary.setChecked(True)
        self.chk_plugins = QCheckBox(tr("pack_opt_plugins"))
        self.chk_plugins.setChecked(True)
        
        self.chk_tm = QCheckBox(tr("pack_opt_tm"))
        self.chk_tm.setToolTip(tr("pack_opt_tm_tooltip"))
        
        self.chk_history = QCheckBox(tr("pack_opt_history"))
        
        opts_layout.addWidget(self.chk_settings)
        opts_layout.addWidget(self.chk_glossary)
        opts_layout.addWidget(self.chk_plugins)
        opts_layout.addWidget(self.chk_tm)
        opts_layout.addWidget(self.chk_history)
        opts_group.setLayout(opts_layout)
        
        layout.addWidget(opts_group)
        
        # Security Group
        sec_group = QGroupBox(tr("pack_sec_title"))
        sec_layout = QVBoxLayout()
        
        self.chk_secrets = QCheckBox(tr("pack_opt_secrets"))
        self.chk_secrets.toggled.connect(self._toggle_password)
        
        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setPlaceholderText(tr("pack_sec_pwd_placeholder"))
        self.pwd_input.setEnabled(False)
        
        if not HAS_CRYPTO:
            self.chk_secrets.setEnabled(False)
            self.chk_secrets.setToolTip(tr("pack_sec_no_crypto"))
            
        sec_layout.addWidget(self.chk_secrets)
        sec_layout.addWidget(self.pwd_input)
        sec_group.setLayout(sec_layout)
        
        layout.addWidget(sec_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_export = QPushButton(tr("pack_btn_export"))
        self.btn_export.clicked.connect(self.start_export)
        self.btn_cancel = QPushButton(tr("cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
    def _toggle_password(self, checked):
        self.pwd_input.setEnabled(checked)
        if checked:
            self.pwd_input.setFocus()
            
    def start_export(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("pack_export_save"), "", "RenForge Pack (*.rfpack);;Zip (*.zip)")
        if not path:
            return
            
        password = self.pwd_input.text()
        if self.chk_secrets.isChecked() and not password:
            QMessageBox.warning(self, tr("warning"), tr("pack_sec_pwd_required"))
            return
            
        options = {
            "settings": self.chk_settings.isChecked(),
            "glossary": self.chk_glossary.isChecked(),
            "plugins": self.chk_plugins.isChecked(),
            "tm": self.chk_tm.isChecked(),
            "history": self.chk_history.isChecked(),
            "secrets": self.chk_secrets.isChecked()
        }
        
        self.btn_export.setEnabled(False)
        self.worker = ExportWorker(ExportRequest(path, options, password))
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
        
    def on_finished(self, success, msg):
        self.btn_export.setEnabled(True)
        if success:
            QMessageBox.information(self, tr("success"), msg)
            self.accept()
        else:
            QMessageBox.critical(self, tr("error"), msg)


class ImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("pack_import_title"))
        self.resize(600, 500)
        
        self.pack_path = None
        self.meta = {}
        
        layout = QVBoxLayout(self)
        
        # File Selection
        file_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        btn_browse = QPushButton("...")
        btn_browse.clicked.connect(self.browse_file)
        
        file_layout.addWidget(QLabel(tr("pack_import_file")))
        file_layout.addWidget(self.path_input)
        file_layout.addWidget(btn_browse)
        layout.addLayout(file_layout)
        
        # Info Box
        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)
        layout.addWidget(self.info_box)
        
        # Strategies
        strat_group = QGroupBox(tr("pack_import_strategies"))
        strat_layout = QGridLayout()
        
        strat_layout.addWidget(QLabel(tr("pack_strat_settings")), 0, 0)
        self.combo_settings = QComboBox()
        self.combo_settings.addItems(["SKIP", "OVERWRITE"])
        strat_layout.addWidget(self.combo_settings, 0, 1)
        
        strat_layout.addWidget(QLabel(tr("pack_strat_glossary")), 1, 0)
        self.combo_glossary = QComboBox()
        self.combo_glossary.addItems(["MERGE_PREFER_LOCAL", "MERGE_PREFER_IMPORTED", "OVERWRITE", "SKIP"])
        strat_layout.addWidget(self.combo_glossary, 1, 1)
        
        strat_layout.addWidget(QLabel(tr("pack_strat_tm")), 2, 0)
        self.combo_tm = QComboBox()
        self.combo_tm.addItems(["MERGE", "REPLACE", "SKIP"])
        strat_layout.addWidget(self.combo_tm, 2, 1)

        strat_group.setLayout(strat_layout)
        layout.addWidget(strat_group)
        
        # Password (Hidden unless needed?)
        # Ideally we only ask if needed, but for simplicity:
        pwd_layout = QHBoxLayout()
        pwd_layout.addWidget(QLabel(tr("pack_sec_pwd_label")))
        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        pwd_layout.addWidget(self.pwd_input)
        layout.addLayout(pwd_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_import = QPushButton(tr("pack_btn_import"))
        self.btn_import.clicked.connect(self.start_import)
        self.btn_import.setEnabled(False)
        self.btn_cancel = QPushButton(tr("cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_import)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("pack_import_select"), "", "RenForge Pack (*.rfpack *.zip)")
        if path:
            self.path_input.setText(path)
            self.pack_path = path
            self.analyze_pack(path)
            
    def analyze_pack(self, path):
        try:
            pack_mgr = PackManager()
            self.meta = pack_mgr.inspect_pack(path)
            
            info = f"Format Version: {self.meta.get('format_version')}\n"
            info += f"Created At: {self.meta.get('created_at')}\n"
            info += f"App Version: {self.meta.get('app_version')}\n"
            info += f"Contents: {', '.join(self.meta.get('contents', []))}\n"
            
            self.info_box.setText(info)
            self.btn_import.setEnabled(True)
            
        except Exception as e:
            self.info_box.setText(f"Error analyzing pack: {e}")
            self.btn_import.setEnabled(False)

    def start_import(self):
        strategies = {
            "settings": self.combo_settings.currentText(),
            "glossary": self.combo_glossary.currentText(),
            "tm": self.combo_tm.currentText()
        }
        password = self.pwd_input.text()
        
        self.btn_import.setEnabled(False)
        self.worker = ImportWorker(self.pack_path, strategies, password)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
        
    def on_finished(self, report, error):
        self.btn_import.setEnabled(True)
        if error:
            QMessageBox.critical(self, tr("error"), error)
        else:
            msg = "\n".join(report)
            QMessageBox.information(self, tr("pack_import_success"), f"{tr('pack_import_report')}:\n\n{msg}")
            self.accept()
