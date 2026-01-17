# -*- coding: utf-8 -*-
"""
Central Qt Import Module for RenForge

This module provides a single source for all Qt imports, ensuring consistency
across the application. The project uses PySide6 exclusively.

Usage:
    from gui.qt import Qt, Signal, Slot, QWidget, QMainWindow, ...

DO NOT import from the old Qt binding (PyQt) anywhere in this project.
"""

# =============================================================================
# PySide6 Core
# =============================================================================
from PySide6.QtCore import (
    Qt,
    Signal,
    Slot,
    Property,
    QObject,
    QTimer,
    QThread,
    QRunnable,
    QThreadPool,
    QModelIndex,
    QItemSelection,
    QItemSelectionModel,
    QSortFilterProxyModel,
    QAbstractItemModel,
    QAbstractTableModel,
    QSettings,
    QDir,
    QByteArray,
    QSize,
    QPoint,
    QRect,
    QEvent,
    QMimeData,
    QUrl,
)

# =============================================================================
# PySide6 GUI (includes QShortcut, QKeySequence, QAction)
# =============================================================================
from PySide6.QtGui import (
    QKeySequence,
    QShortcut,
    QAction,
    QFont,
    QColor,
    QBrush,
    QPen,
    QIcon,
    QPixmap,
    QImage,
    QPainter,
    QCursor,
    QClipboard,
    QFileSystemModel,
    QStandardItem,
    QStandardItemModel,
)

# =============================================================================
# PySide6 Widgets
# =============================================================================
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QDialog,
    QMessageBox,
    QFileDialog,
    QInputDialog,
    QProgressDialog,
    # Layouts
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFormLayout,
    QStackedLayout,
    QStackedWidget,
    QSplitter,
    # Containers
    QFrame,
    QGroupBox,
    QScrollArea,
    QTabWidget,
    QToolBox,
    # Views
    QTableWidget,
    QTableWidgetItem,
    QTableView,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeView,
    QListWidget,
    QListWidgetItem,
    QListView,
    QHeaderView,
    QAbstractItemView,
    # Controls
    QLabel,
    QPushButton,
    QToolButton,
    QRadioButton,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QSlider,
    QProgressBar,
    # Text
    QLineEdit,
    QTextEdit,
    QPlainTextEdit,
    QTextBrowser,
    # Menus
    QMenu,
    QMenuBar,
    QToolBar,
    QStatusBar,
    # Misc
    QSizePolicy,
    QSpacerItem,
    QDialogButtonBox,
    QButtonGroup,
    QCompleter,
    QStyle,
    QStyleFactory,
)

# =============================================================================
# Aliases for PyQt6 compatibility (naming differences)
# =============================================================================
# PyQt6 uses Signal, PySide6 uses Signal
Signal = Signal
Slot = Slot

# =============================================================================
# Utility function to check Qt binding
# =============================================================================
def get_qt_binding():
    """Return the name of the Qt binding in use."""
    return "PySide6"

__all__ = [
    # Core
    'Qt', 'Signal', 'Slot', 'Property', 'QObject', 'QTimer', 'QThread',
    'QRunnable', 'QThreadPool', 'QModelIndex', 'QItemSelection',
    'QItemSelectionModel', 'QSortFilterProxyModel', 'QAbstractItemModel',
    'QAbstractTableModel', 'QSettings', 'QDir', 'QByteArray', 'QSize',
    'QPoint', 'QRect', 'QEvent', 'QMimeData', 'QUrl',
    # GUI
    'QKeySequence', 'QShortcut', 'QAction', 'QFont', 'QColor', 'QBrush',
    'QPen', 'QIcon', 'QPixmap', 'QImage', 'QPainter', 'QCursor', 'QClipboard',
    'QFileSystemModel', 'QStandardItem', 'QStandardItemModel',
    # Widgets
    'QApplication', 'QMainWindow', 'QWidget', 'QDialog', 'QMessageBox',
    'QFileDialog', 'QInputDialog', 'QProgressDialog',
    'QVBoxLayout', 'QHBoxLayout', 'QGridLayout', 'QFormLayout',
    'QStackedLayout', 'QStackedWidget', 'QSplitter',
    'QFrame', 'QGroupBox', 'QScrollArea', 'QTabWidget', 'QToolBox',
    'QTableWidget', 'QTableWidgetItem', 'QTableView',
    'QTreeWidget', 'QTreeWidgetItem', 'QTreeView',
    'QListWidget', 'QListWidgetItem', 'QListView',
    'QHeaderView', 'QAbstractItemView',
    'QLabel', 'QPushButton', 'QToolButton', 'QRadioButton', 'QCheckBox',
    'QComboBox', 'QSpinBox', 'QDoubleSpinBox', 'QSlider', 'QProgressBar',
    'QLineEdit', 'QTextEdit', 'QPlainTextEdit', 'QTextBrowser',
    'QMenu', 'QMenuBar', 'QToolBar', 'QStatusBar',
    'QSizePolicy', 'QSpacerItem', 'QDialogButtonBox', 'QButtonGroup',
    'QCompleter', 'QStyle', 'QStyleFactory',
    # Aliases
    'Signal', 'Slot',
    # Utility
    'get_qt_binding',
]
