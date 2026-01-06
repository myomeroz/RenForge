import renforge_config as config

pics = ["pics/branch-expand.svg", "pics/branch-collapse.svg"]

MODERN_STYLE_SHEET = """
QWidget {{
    background-color: #202124; /* Darker base */
    color: #E8EAED; /* Lighter text */
    font-family: "Segoe UI", Arial, sans-serif; /* Common modern font */
    font-size: 10pt;
    border: none;
}}

QMainWindow, QDialog {{
    background-color: #2D2E30; /* Slightly lighter container background */
}}

QRadioButton, QCheckBox {{
    background-color: transparent;
    spacing: 5px; /* Space between button and text */
}}

QCheckBox::indicator {{
    width: 13px;
    height: 13px;
    border: 1px solid #5F6368;
    border-radius: 2px; /* Circular */
    background-color: #202124;
}}
QRadioButton::indicator {{
    width: 13px;
    height: 13px;
    border: 1px solid #5F6368;
    border-radius: 7px; /* Circular */
    background-color: #202124;
}}

QRadioButton::indicator:checked, QCheckBox::indicator:checked {{
    background-color: #565656; /* Accent color */
    border: 1px solid #565656;
    image: none; /* Optional: remove checkmark image if desired */
}}

QRadioButton::indicator:hover, QCheckBox::indicator:hover {{
    border: 1px solid #8AB4F8; /* Lighter accent on hover */
}}


QMenuBar {{
    background-color: #2D2E30;
    color: #E8EAED;
    padding: 1px; /* Add some padding */
}}

QMenuBar::item {{
    background-color: transparent;
    color: #E8EAED;
    padding: 4px 6px; /* More padding */
    border-radius: 4px; /* Subtle rounding */
}}

QMenuBar::item:selected {{
    background-color: #3C4043; /* Subtle selection */
}}

QMenu {{
    background-color: #2D2E30;
    color: #E8EAED;
    border: 1px solid #44474E; /* Slightly more prominent border */
    border-radius: 4px;
    padding: 4px; /* Padding around items */
}}

QMenu::item {{
    padding: 3px 12px; /* More padding */
    border-radius: 3px; /* Rounded item selection */
}}

QMenu::item:selected {{
    background-color: #565656; /* Accent color for selection */
    color: #ffffff; /* White text on accent */
}}
QMenu::separator {{
    height: 1px;
    background: #44474E;
    margin: 4px 0px;
}}

QGroupBox {{
    background-color: #2D2E30;
    border: 1px solid #44474E; /* Subtle border */
    border-radius: 4px; /* More rounding */
    margin-top: 5px;
    padding: 4px; /* More padding inside */
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left; /* Title top-left */
    padding: 0 5px 0 10px; /* Adjust padding */
    color: #BDC1C6; /* Slightly muted title color */
    left: 10px; /* Indent title slightly */
    background-color: #2D2E30; /* Ensure title background matches */
}}

QLabel {{
    background-color: transparent;
    color: #E8EAED;
    padding: 2px;
}}

QLineEdit, QTextEdit, QListWidget, QComboBox {{
    background-color: #202124; /* Base background for inputs */
    color: #E8EAED;
    border: 1px solid #5F6368; /* Subtle border */
    border-radius: 6px; /* Consistent rounding */
    padding: 3px 4px; /* More padding */
}}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border: 1px solid #565656; /* Accent border on focus */
}}
QLineEdit:disabled, QTextEdit:disabled, QListWidget:disabled, QComboBox:disabled {{
    background-color: #3C4043;
    color: #9AA0A6;
    border-color: #44474E;
}}


QTextEdit {{
    selection-background-color: #565656; /* Accent selection */
    selection-color: #ffffff;
}}

QListWidget {{
    selection-background-color: #565656;
    selection-color: #ffffff;
    outline: 0;
    border: 1px solid #5F6368; /* Consistent border */
    alternate-background-color: #26282B; /* Subtle alternating rows */
}}

QListWidget::item {{
    padding: 8px 5px; /* More vertical padding */
    border-bottom: 1px solid #3C4043; /* Subtle separator */
    border-radius: 0px; /* Items should be flat */
}}
QListWidget::item:last {{
    border-bottom: none; /* No border on the last item */
}}

QListWidget::item:selected {{
    background-color: #565656;
    color: #ffffff;
    border-bottom: 1px solid #565656; /* Keep separator consistent */
}}
QListWidget::item:hover:!selected {{ /* Hover only if not selected */
    background-color: #3C4043;
    color: #E8EAED;
    border-bottom: 1px solid #3C4043; /* Keep separator consistent */
}}


QComboBox::drop-down {{
    border: none;
    background-color: transparent;
    width: 20px; /* Slightly wider */
    padding-right: 5px;
}}

QComboBox::down-arrow {{
     /* Using a standard character (chevron down) */
     image: url(icons:downarrow.png); /* Using a standard Qt icon if available, or replace with custom */
     /* Fallback using border: */
     /* width: 0; */
     /* height: 0; */
     /* border-left: 5px solid transparent; */
     /* border-right: 5px solid transparent; */
     /* border-top: 6px solid #BDC1C6; */ /* Arrow color */
     /* margin: 0 auto; */
}}
QComboBox::down-arrow:on {{ /* Arrow when dropdown is open */
     /* image: url(icons:uparrow.png); */
     /* border-top: none; */
     /* border-bottom: 6px solid #BDC1C6; */
}}

QComboBox QAbstractItemView {{ /* Style dropdown list */
    background-color: #2D2E30;
    color: #E8EAED;
    border: 1px solid #44474E;
    border-radius: 4px; /* Rounded dropdown */
    selection-background-color: #565656;
    selection-color: #ffffff;
    padding: 4px; /* Padding inside dropdown list */
    outline: 0px; /* No focus outline on dropdown */
}}
QComboBox QAbstractItemView::item {{
    padding: 3px 5px; /* Padding for dropdown items */
    border-radius: 3px; /* Rounded selection */
    min-height: 25px; /* Ensure items are not too small */
}}


QPushButton {{
    background-color: #3C4043; /* Button background */
    color: #E8EAED;
    border: 1px solid transparent; /* No border by default */
    border-radius: 3px; /* Rounded corners */
    padding: 4px 8px; /* Уменьшаем вертикальный padding, оставляем горизонтальный */
    min-width: 20px;
    font-weight: 500; /* Slightly bolder font */
}}

QPushButton:hover {{
    background-color: #4E5155; /* Slightly lighter on hover */
    border-color: transparent;
}}

QPushButton:pressed {{
    background-color: #565656; /* Accent color when pressed */
    color: #ffffff;
    border-color: transparent;
}}

QPushButton:disabled {{
    background-color: #2D2E30; /* Muted background */
    color: #5F6368; /* Muted text */
    border-color: transparent;
}}
/* Optional: Style the default button */
QPushButton:default {{
    background-color: #565656; /* Accent background for default button */
    color: #ffffff;
}}
QPushButton:default:hover {{
    background-color: #6A8EC8; /* Lighter accent */
}}
QPushButton:default:pressed {{
    background-color: #4A6984; /* Darker accent */
}}


QStatusBar {{
    background-color: #202124; /* Match base background */
    color: #BDC1C6; /* Slightly muted text */
    padding: 3px;
}}
QStatusBar::item {{
    border: none; /* No borders between status items */
}}

QSplitter::handle {{
    background-color: #44474E; /* Neutral handle color */
    border: none;
    width: 3px; /* Thinner handle */
    height: 3px;
    margin: 1px 0;
}}

QSplitter::handle:horizontal {{
    height: 3px;
    width: 1px;
}}

QSplitter::handle:pressed {{
    background-color: #565656; /* Accent color when dragging */
}}


QDialogButtonBox QPushButton {{
    /* Ensure dialog buttons follow the main style */
    /* Inherits QPushButton styles */
    min-width: 80px; /* Keep min-width for dialog buttons */
    padding: 3px;
}}

/* --- Стили для таблицы --- */
QTableWidget {{
    background-color: #202124; /* Base background */
    color: #E8EAED;
    border: 1px solid #44474E; /* Consistent border */
    gridline-color: #3C4043; /* Subtle grid lines */
    selection-background-color: #565656; /* Accent selection */
    selection-color: #ffffff;
    border-radius: 6px; /* Rounded corners for the table itself */
    alternate-background-color: #26282B; /* Subtle alternating rows */
    margin: 0;
}}

QTableWidget::item {{
    padding: 1px;
    border-style: none; /* Remove individual cell borders */
    border-bottom: 1px solid #3C4043; /* Use row separators */
}}

QTableWidget::item:selected {{
    background-color: #565656;
    color: #ffffff;
}}

QHeaderView {{
    background-color: #2D2E30; /* Header background */
    border: none; /* No border around header sections */
}}
QHeaderView::section {{
    background-color: transparent; /* Use QHeaderView background */
    color: #BDC1C6; /* Header text color */
    padding: 3px 4px;
    border-style: none; /* No borders for sections */
    border-bottom: 1px solid #44474E; /* Border below header */
    font-weight: 500; /* Slightly bolder */
    text-align: left; /* Align text left */
}}
QHeaderView::section:horizontal {{
    border-right: 1px solid #44474E; /* Separator between horizontal sections */
}}
QHeaderView::section:vertical {{
    border-bottom: 1px solid #44474E; /* Separator between vertical sections */
}}

QHeaderView::section:last:horizontal, QHeaderView::section:only-one:horizontal {{
    border-right: none; /* No border on last horizontal section */
}}
QHeaderView::section:last:vertical, QHeaderView::section:only-one:vertical {{
    border-bottom: none; /* No border on last vertical section */
}}

/* Style the top-left corner button */
QTableCornerButton::section {{
    background-color: #2D2E30;
    border: none;
    border-bottom: 1px solid #44474E;
    border-right: 1px solid #44474E;
}}

/* --- Стили для вкладок --- */
QTabWidget {{
    border: none;
    background-color: transparent;
}}

QTabWidget::pane {{
    border: 1px solid #44474E;
    border-top: none; /* Pane border connected to tab bar bottom */
    background-color: #2D2E30; /* Pane background */
    border-bottom-left-radius: 6px; /* Round bottom corners */
    border-bottom-right-radius: 6px;
    padding: 0px; /* Padding inside the tab content area */
}}

QTabBar {{
    background-color: transparent;
    border: none;
    qproperty-drawBase: 0; /* Important to prevent double background draw */
}}

QTabBar::tab {{
    background-color: #2D2E30; /* Tab background */
    color: #BDC1C6; /* Muted text for inactive tabs */
    border: 1px solid #44474E;
    border-bottom: none; /* No bottom border for inactive tabs */
    padding: 6px; /* Tab padding */
    margin: 0;
    border-top-left-radius: 2px; /* Rounded top corners */
    border-top-right-radius: 2px;
    min-width: 100px; /* Minimum tab width */
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background-color: #3C4043; /* Selected tab matches pane background */
    color: #E8EAED; /* Active tab text */
    border-color: #44474E;
    /* Simulate connection to pane */
    margin-bottom: -1px; /* Pull tab down slightly */
    border-bottom: 1px solid #2D2E30; /* Match pane background color */
}}

QTabBar::tab:hover:!selected {{
    background-color: #3C4043; /* Hover effect for inactive tabs */
    color: #E8EAED;
}}

QTabBar::tab:disabled {{
    color: #5F6368;
    background-color: #202124;
    border-color: #3C4043;
}}

QTabBar::tab:first {{
    margin-left: 4px;
}}

QTabBar::tab:last {{
    margin-right: 4px;
}}

QTabBar::tab:only-one {{
    margin: 0 4px;
}}

QTabBar::close-button {{
    background-color: rgba(255, 100, 100, 0.5);
    color: #BDC1C6;
    subcontrol-position: right;
    margin-right: 2px;
    border-radius: 4px;
}}

QTabBar::close-button:hover {{
    background-color: #E84135;
    color: white;
}}

QTabBar::close-button:pressed {{
    background-color: #E84135;
    color: white;
}}

/* Style tab scroll buttons if needed */
QTabBar QToolButton {{
    background-color: #3C4043;
    border: 1px solid #44474E;
    border-radius: 4px;
    padding: 4px;
}}
QTabBar QToolButton:hover {{
    background-color: #4E5155;
}}
QTabBar QToolButton::right-arrow, QTabBar QToolButton::left-arrow {{
    /* Use icons or characters */
}}

/* --- Scrollbars --- */
QScrollBar:vertical {{
    border: none;
    background: #2D2E30; /* Scrollbar track */
    width: 10px; /* Width of vertical scrollbar */
    margin: 0px 0px 0px 0px;
}}
QScrollBar::handle:vertical {{
    background: #5F6368; /* Scrollbar handle */
    min-height: 20px; /* Minimum handle size */
    border-radius: 5px; /* Rounded handle */
}}
QScrollBar::handle:vertical:hover {{
    background: #8AB4F8; /* Lighter handle on hover */
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
    height: 0px; /* Hide arrow buttons */
    subcontrol-position: top;
    subcontrol-origin: margin;
}}
/* QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }} */ /* Optional: Remove page step background */

QScrollBar:horizontal {{
    border: none;
    background: #2D2E30; /* Scrollbar track */
    height: 10px; /* Height of horizontal scrollbar */
    margin: 0px 0px 0px 0px;
}}
QScrollBar::handle:horizontal {{
    background: #5F6368; /* Scrollbar handle */
    min-width: 20px; /* Minimum handle size */
    border-radius: 5px; /* Rounded handle */
}}
QScrollBar::handle:horizontal:hover {{
    background: #8AB4F8; /* Lighter handle on hover */
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    border: none;
    background: none;
    width: 0px; /* Hide arrow buttons */
    subcontrol-position: left;
    subcontrol-origin: margin;
}}
/* QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }} */ /* Optional: Remove page step background */

/* --- Activity Bar --- */
#activityBar {{
    background-color: #2D2E30; /* Slightly lighter than base */
    border-right: 1px solid #44474E; /* Separator line */
}}

#activityBar QToolButton {{
    background-color: transparent;
    border: none;
    color: #BDC1C6; /* Muted icon/text color */
    padding: 1px; /* Padding around icon/text */
    margin: 0px;
    min-width: 40px; /* Fixed width for the bar */
    max-width: 40px;
    min-height: 35px;
    font-size: 14pt; /* Larger size for icon-like text */
    border-left: 3px solid transparent; /* Indicator border */
}}

#activityBar QToolButton:hover {{
    background-color: #3C4043; /* Subtle hover */
    color: #E8EAED; /* Brighter icon/text on hover */
}}

#activityBar QToolButton:checked {{
    background-color: #3C4043; /* Background for active button */
    color: #E8EAED; /* Active icon/text color */
    border-left: 3px solid #565656; /* Accent color indicator */
}}

#activityBar QToolButton:disabled {{
    color: #5F6368; /* Muted color for disabled */
    background-color: transparent;
}}

/* --- Project Panel & Tree View --- */
#projectPanel {{
    background-color: #2D2E30; /* Match activity bar neighbor */
    border: none; /* Splitter handle provides separation */
}}

QTreeView {{
    background-color: #2D2E30; /* Match panel background */
    color: #E8EAED;
    border: none; /* No border around the tree itself */
    alternate-background-color: #3C4043; /* Slightly different for contrast if needed */
    outline: 0; /* No focus outline */
}}

QTreeView::item {{
    padding: 2px 1px; /* Padding for items */
    border-radius: 3px; /* Slight rounding for selection */
    min-height: 10px; /* Ensure items are not too small */
}}

QTreeView::item:hover {{
    background-color: #3C4043; /* Hover background */
}}

QTreeView::item:selected {{
    background-color: #565656; /* Accent selection background */
    color: #ffffff; /* Selection text color */
}}

/* Branch indicators (arrows) */
QTreeView::branch {{
    background: transparent; /* Ensure branch area is transparent */
}}

QTreeView::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children:has-siblings {{
    /* Collapsed branch arrow */
    border-image: none;
    image: url({0});
    /* Fallback character: image: none; content: ">"; */
}}

QTreeView::branch:open:has-children:!has-siblings,
QTreeView::branch:open:has-children:has-siblings {{
    /* Expanded branch arrow */
    border-image: none;
    image: url({1});
    /* Fallback character: image: none; content: "v"; */
}}

/* Optional: Style the lines connecting branches */
/* QTreeView::branch:has-siblings:!adjoins-item {{ border-image: url(path/to/vline.png) 0; }} */
/* QTreeView::branch:has-siblings:adjoins-item {{ border-image: url(path/to/branch-more.png) 0; }} */
/* QTreeView::branch:!has-children:!has-siblings:adjoins-item {{ border-image: url(path/to/branch-end.png) 0; }} */

/* --- Search/Replace Panel --- */
#searchReplacePanel {{
    background-color: #2D2E30; /* Match project panel */
    border: none;
}}

#searchReplacePanel QLabel {{
    color: #BDC1C6; /* Slightly muted label color */
    padding-bottom: 0px; /* Less space below labels */
    margin-bottom: 0px;
}}

#searchReplacePanel QLineEdit {{
    margin-bottom: 5px; /* Space below input fields */
}}

#searchReplacePanel QCheckBox {{
    margin-top: 5px; /* Space above checkbox */
    margin-bottom: 5px; /* Space below checkbox */
}}

#searchReplacePanel QPushButton {{
    /* Inherits general QPushButton style */
    /* Add specific overrides if needed */
    padding: 3px 6px; /* Slightly smaller padding */
}}



""".format(config.resource_path(pics[0]).replace('\\','/'), config.resource_path(pics[1]).replace('\\','/'))

DARK_STYLE_SHEET = MODERN_STYLE_SHEET

print("gui/renforge_gui_styles.py updated with Modern Style")
