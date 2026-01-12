
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFormLayout, QDialog, QLineEdit, QCheckBox, QScrollArea,
    QGroupBox
)
from PyQt6.QtCore import Qt
from core.plugin_manager import PluginManager
from renforge_logger import get_logger
from locales import tr
from interfaces.i_plugin import PluginType, ITranslationEngine

logger = get_logger("gui.widgets.plugin_settings")

class PluginConfigDialog(QDialog):
    """
    Dynamic configuration dialog based on plugin schema.
    """
    def __init__(self, plugin, current_config, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.config = current_config.copy() if current_config else {}
        self.setWindowTitle(f"{tr('plugins_btn_config')} - {plugin.name}")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        schema = plugin.get_config_schema()
        
        self.inputs = {}
        
        if not schema:
            layout.addWidget(QLabel(tr("plugins_no_config")))
        else:
            for field in schema:
                key = field["key"]
                label_text = field.get("label", key)
                default_val = field.get("default", "")
                type_ = field.get("type", "text")
                
                curr_val = self.config.get(key, default_val)
                
                input_widget = None
                if type_ == "bool":
                    input_widget = QCheckBox()
                    input_widget.setChecked(bool(curr_val))
                else: 
                    # text or password
                    input_widget = QLineEdit()
                    input_widget.setText(str(curr_val))
                    if type_ == "password":
                        input_widget.setEchoMode(QLineEdit.EchoMode.Password)
                
                self.inputs[key] = {"widget": input_widget, "type": type_}
                form_layout.addRow(label_text, input_widget)
                
        layout.addLayout(form_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton(tr("save"))
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
    def get_config(self):
        result = {}
        for key, data in self.inputs.items():
            widget = data["widget"]
            type_ = data["type"]
            if type_ == "bool":
                result[key] = widget.isChecked()
            else:
                result[key] = widget.text()
        return result


class PluginSettingsWidget(QWidget):
    """
    Widget to manage plugins and select active engine.
    """
    def __init__(self, settings_model, parent=None):
        super().__init__(parent)
        self.settings = settings_model
        self.plugin_manager = PluginManager()
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. Active Engine Selection
        engine_group = QGroupBox(tr("translation_mode_label")) # Reuse similar label or new
        engine_form = QFormLayout()
        
        self.engine_combo = QComboBox()
        self.engines = self.plugin_manager.get_all_engines()
        
        current_engine_id = self.settings.get("active_plugin_engine", "renforge.engine.google_free")
        
        for engine in self.engines:
            self.engine_combo.addItem(f"{engine.name} ({engine.version})", engine.id)
            if engine.id == current_engine_id:
                self.engine_combo.setCurrentIndex(self.engine_combo.count() - 1)
        
        self.engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        engine_form.addRow(tr("plugins_status_active"), self.engine_combo)
        
        # Test Button
        self.btn_test = QPushButton("Test Engine")
        self.btn_test.clicked.connect(self._run_test)
        engine_form.addRow("", self.btn_test)
        
        engine_group.setLayout(engine_form)
        layout.addWidget(engine_group)
        
        # 2. Installed Plugins Table
        lbl_list = QLabel(tr("plugins_tab_installed"))
        layout.addWidget(lbl_list)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            tr("plugins_col_name"),
            tr("plugins_col_version"),
            tr("plugins_col_type"),
            tr("plugins_col_status"),
            "" # Actions
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # Failed Plugins Section
        self.failed_group = QGroupBox("Failed Load Plugins")
        self.failed_layout = QVBoxLayout(self.failed_group)
        self.failed_label = QLabel("")
        self.failed_label.setStyleSheet("color: red;")
        self.failed_layout.addWidget(self.failed_label)
        layout.addWidget(self.failed_group)
        self.failed_group.setVisible(False)
        
        self._refresh_table()
        
    def _refresh_table(self):
        self.table.setRowCount(0)
        plugins = self.plugin_manager.plugins.values()
        
        for row, plugin in enumerate(plugins):
            self.table.insertRow(row)
            
            # Name
            self.table.setItem(row, 0, QTableWidgetItem(plugin.name))
            # Version
            self.table.setItem(row, 1, QTableWidgetItem(plugin.version))
            # Type
            type_str = "Engine" if plugin.plugin_type == PluginType.ENGINE else "Tool"
            self.table.setItem(row, 2, QTableWidgetItem(type_str))
            # Status (Mock for now, assume valid)
            self.table.setItem(row, 3, QTableWidgetItem(tr("plugins_status_active")))
            
            # Action Button (Configure)
            btn = QPushButton(tr("plugins_btn_config"))
            btn.clicked.connect(lambda checked, p=plugin: self._configure_plugin(p))
            self.table.setCellWidget(row, 4, btn)

        # Update Failed Plugins
        failed = self.plugin_manager.failed_plugins
        if failed:
            self.failed_group.setVisible(True)
            txt = "\n".join([f"- {f['name']}: {f['error']}" for f in failed])
            self.failed_label.setText(txt)
        else:
            self.failed_group.setVisible(False)
            
    def _run_test(self):
        from PyQt6.QtWidgets import QMessageBox
        # Test active engine
        engine_id = self.engine_combo.currentData()
        if not engine_id: 
            QMessageBox.warning(self, "Test", "No engine selected.")
            return
            
        try:
             from core.translation_service import TranslationService
             # Create temp service
             service = TranslationService(self.settings)
             
             # Override active engine to selected one (in case settings not saved/synced perfectly yet)
             # But Service reads from settings dict, so we must ensure it's set
             self.settings["active_plugin_engine"] = engine_id
             
             item = {"i": 1, "original": "Hello [player]! System test."}
             QMessageBox.information(self, "Test", "Running test translation...")
             
             # Run batch
             results = service.batch_translate([item], "en", "tr")
             res = results[0]
             
             if "error" in res:
                 QMessageBox.warning(self, "Test Failed", f"Error: {res['error']}")
             else:
                 QMessageBox.information(self, "Test Success", f"Original: {item['original']}\nTranslation: {res['t']}")
                 
        except Exception as e:
             QMessageBox.critical(self, "Test Error", str(e))

    def _on_engine_changed(self):
        engine_id = self.engine_combo.currentData()
        self.settings["active_plugin_engine"] = engine_id
        logger.info(f"Active engine changed to: {engine_id}")

    def _configure_plugin(self, plugin):
        # Load existing config from settings
        all_plugins_config = self.settings.get("plugins_config", {})
        plugin_config = all_plugins_config.get(plugin.id, {})
        
        dialog = PluginConfigDialog(plugin, plugin_config, self)
        if dialog.exec():
            new_config = dialog.get_config()
            # Save back
            all_plugins_config[plugin.id] = new_config
            self.settings["plugins_config"] = all_plugins_config
            logger.info(f"Updated configuration for plugin {plugin.id}")
