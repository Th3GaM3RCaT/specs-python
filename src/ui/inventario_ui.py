# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'inventario.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMenu,
    QMenuBar, QPushButton, QSizePolicy, QSpacerItem,
    QSplitter, QStatusBar, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1280, 720)
        MainWindow.setMinimumSize(QSize(1280, 720))
        MainWindow.setStyleSheet(u"\n"
"   /*Copyright (c) DevSec Studio. All rights reserved.\n"
"\n"
"MIT License\n"
"\n"
"Permission is hereby granted, free of charge, to any person obtaining a copy\n"
"of this software and associated documentation files (the \"Software\"), to deal\n"
"in the Software without restriction, including without limitation the rights\n"
"to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
"copies of the Software, and to permit persons to whom the Software is\n"
"furnished to do so, subject to the following conditions:\n"
"\n"
"The above copyright notice and this permission notice shall be included in all\n"
"copies or substantial portions of the Software.\n"
"\n"
"THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n"
"IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n"
"FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n"
"AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n"
"LIABILITY, WHETHER I"
                        "N AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n"
"OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n"
"*/\n"
"\n"
"/*-----QWidget-----*/\n"
"QWidget\n"
"{\n"
"	background-color: #3a3a3a;\n"
"	color: #fff;\n"
"	selection-background-color: #b78620;\n"
"	selection-color: #000;\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QLabel-----*/\n"
"QLabel\n"
"{\n"
"	background-color: transparent;\n"
"	color: #fff;\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QMenuBar-----*/\n"
"QMenuBar \n"
"{\n"
"	background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(57, 57, 57, 255),stop:1 rgba(50, 50, 50, 255));\n"
"	border: 1px solid #000;\n"
"	color: #fff;\n"
"\n"
"}\n"
"\n"
"\n"
"\n"
"QMenuBar::item:selected \n"
"{\n"
"	background-color: rgba(183, 134, 32, 20%);\n"
"	border: 1px solid #b78620;\n"
"	color: #fff;\n"
"\n"
"}\n"
"\n"
"\n"
"QMenuBar::item:pressed \n"
"{\n"
"	background-color: rgb(183, 134, 32);\n"
"	border: 1px solid #b78620;\n"
"	color: #fff;\n"
"\n"
"}\n"
"\n"
"\n"
""
                        "/*-----QMenu-----*/\n"
"QMenu\n"
"{\n"
"    background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(57, 57, 57, 255),stop:1 rgba(50, 50, 50, 255));\n"
"    border: 1px solid #222;\n"
"    padding: 4px;\n"
"	color: #fff;\n"
"\n"
"}\n"
"\n"
"\n"
"QMenu::item\n"
"{\n"
"    background-color: transparent;\n"
"    padding: 2px 20px 2px 20px;\n"
"\n"
"}\n"
"\n"
"\n"
"QMenu::separator\n"
"{\n"
"   	background-color: rgb(183, 134, 32);\n"
"	height: 1px;\n"
"\n"
"}\n"
"\n"
"\n"
"QMenu::item:disabled\n"
"{\n"
"    color: #555;\n"
"    background-color: transparent;\n"
"    padding: 2px 20px 2px 20px;\n"
"\n"
"}\n"
"\n"
"\n"
"QMenu::item:selected\n"
"{\n"
"	background-color: rgba(183, 134, 32, 20%);\n"
"	border: 1px solid #b78620;\n"
"	color: #fff;\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QToolBar-----*/\n"
"QToolBar\n"
"{\n"
"	background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(69, 69, 69, 255),stop:1 rgba(58, 58, 58, 255));\n"
"	border-top: none;\n"
"	border-bottom: 1"
                        "px solid #4f4f4f;\n"
"	border-left: 1px solid #4f4f4f;\n"
"	border-right: 1px solid #4f4f4f;\n"
"\n"
"}\n"
"\n"
"\n"
"QToolBar::separator\n"
"{\n"
"	background-color: #2e2e2e;\n"
"	width: 1px;\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QToolButton-----*/\n"
"QToolButton \n"
"{\n"
"	background-color: transparent;\n"
"	color: #fff;\n"
"	padding: 5px;\n"
"	padding-left: 8px;\n"
"	padding-right: 8px;\n"
"	margin-left: 1px;\n"
"}\n"
"\n"
"\n"
"QToolButton:hover\n"
"{\n"
"	background-color: rgba(183, 134, 32, 20%);\n"
"	border: 1px solid #b78620;\n"
"	color: #fff;\n"
"	\n"
"}\n"
"\n"
"\n"
"QToolButton:pressed\n"
"{\n"
"	background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(57, 57, 57, 255),stop:1 rgba(50, 50, 50, 255));\n"
"	border: 1px solid #b78620;\n"
"\n"
"}\n"
"\n"
"\n"
"QToolButton:checked\n"
"{\n"
"	background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(57, 57, 57, 255),stop:1 rgba(50, 50, 50, 255));\n"
"	border: 1px solid #222;\n"
"}\n"
"\n"
"\n"
"/*-----QPus"
                        "hButton-----*/\n"
"QPushButton\n"
"{\n"
"	background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(84, 84, 84, 255),stop:1 rgba(59, 59, 59, 255));\n"
"	color: #ffffff;\n"
"	min-width: 80px;\n"
"	border-style: solid;\n"
"	border-width: 1px;\n"
"	border-radius: 3px;\n"
"	border-color: #051a39;\n"
"	padding: 5px;\n"
"\n"
"}\n"
"\n"
"\n"
"QPushButton::flat\n"
"{\n"
"	background-color: transparent;\n"
"	border: none;\n"
"	color: #fff;\n"
"\n"
"}\n"
"\n"
"\n"
"QPushButton::disabled\n"
"{\n"
"	background-color: #404040;\n"
"	color: #656565;\n"
"	border-color: #051a39;\n"
"\n"
"}\n"
"\n"
"\n"
"QPushButton::hover\n"
"{\n"
"	background-color: rgba(183, 134, 32, 20%);\n"
"	border: 1px solid #b78620;\n"
"\n"
"}\n"
"\n"
"\n"
"QPushButton::pressed\n"
"{\n"
"	background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(74, 74, 74, 255),stop:1 rgba(49, 49, 49, 255));\n"
"	border: 1px solid #b78620;\n"
"\n"
"}\n"
"\n"
"\n"
"QPushButton::checked\n"
"{\n"
"	background-color: ql"
                        "ineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(74, 74, 74, 255),stop:1 rgba(49, 49, 49, 255));\n"
"	border: 1px solid #222;\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QLineEdit-----*/\n"
"QLineEdit\n"
"{\n"
"	background-color: #131313;\n"
"	color : #eee;\n"
"	border: 1px solid #343434;\n"
"	border-radius: 2px;\n"
"	padding: 3px;\n"
"	padding-left: 5px;\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QPlainTExtEdit-----*/\n"
"QPlainTextEdit\n"
"{\n"
"	background-color: #131313;\n"
"	color : #eee;\n"
"	border: 1px solid #343434;\n"
"	border-radius: 2px;\n"
"	padding: 3px;\n"
"	padding-left: 5px;\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QTabBar-----*/\n"
"QTabBar::tab\n"
"{\n"
"	background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(84, 84, 84, 255),stop:1 rgba(59, 59, 59, 255));\n"
"	color: #ffffff;\n"
"	border-style: solid;\n"
"	border-width: 1px;\n"
"	border-color: #666;\n"
"	border-bottom: none;\n"
"	padding: 5px;\n"
"	padding-left: 15px;\n"
"	padding-right: 15px;\n"
"\n"
"}\n"
"\n"
"\n"
"QTabWidg"
                        "et::pane \n"
"{\n"
"	background-color: red;\n"
"	border: 1px solid #666;\n"
"	top: 1px;\n"
"\n"
"}\n"
"\n"
"\n"
"QTabBar::tab:last\n"
"{\n"
"	margin-right: 0; \n"
"\n"
"}\n"
"\n"
"\n"
"QTabBar::tab:first:!selected\n"
"{\n"
"	background-color: #0c0c0d;\n"
"	margin-left: 0px;\n"
"\n"
"}\n"
"\n"
"\n"
"QTabBar::tab:!selected\n"
"{\n"
"	color: #b1b1b1;\n"
"	border-bottom-style: solid;\n"
"	background-color: #0c0c0d;\n"
"\n"
"}\n"
"\n"
"\n"
"QTabBar::tab:selected\n"
"{\n"
"	margin-bottom: 0px;\n"
"\n"
"}\n"
"\n"
"\n"
"QTabBar::tab:!selected:hover\n"
"{\n"
"	border-top-color: #b78620;\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QComboBox-----*/\n"
"QComboBox\n"
"{\n"
"    background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(84, 84, 84, 255),stop:1 rgba(59, 59, 59, 255));\n"
"    border: 1px solid #000;\n"
"    padding-left: 6px;\n"
"    color: #ffffff;\n"
"    height: 20px;\n"
"\n"
"}\n"
"\n"
"\n"
"QComboBox::disabled\n"
"{\n"
"	background-color: #404040;\n"
"	color: #656565;\n"
"	border-color: #0"
                        "51a39;\n"
"\n"
"}\n"
"\n"
"\n"
"QComboBox:on\n"
"{\n"
"    background-color: #b78620;\n"
"	color: #000;\n"
"\n"
"}\n"
"\n"
"\n"
"QComboBox QAbstractItemView\n"
"{\n"
"    background-color: #383838;\n"
"    color: #ffffff;\n"
"    border: 1px solid black;\n"
"    selection-background-color: #b78620;\n"
"    outline: 0;\n"
"\n"
"}\n"
"\n"
"\n"
"QComboBox::drop-down\n"
"{\n"
"	background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(57, 57, 57, 255),stop:1 rgba(50, 50, 50, 255));\n"
"    subcontrol-origin: padding;\n"
"    subcontrol-position: top right;\n"
"    width: 15px;\n"
"    border-left-width: 1px;\n"
"    border-left-color: black;\n"
"    border-left-style: solid; \n"
"\n"
"}\n"
"\n"
"\n"
"QComboBox::down-arrow\n"
"{\n"
"    image: url(://arrow-down.png);\n"
"    width: 8px;\n"
"    height: 8px;\n"
"}\n"
"\n"
"\n"
"/*-----QSpinBox and QDateTimeEdit-----*/\n"
"QSpinBox,\n"
"QDateTimeEdit \n"
"{\n"
"    background-color: #131313;\n"
"	color : #eee;\n"
"	border: 1px solid #343434"
                        ";\n"
"	padding: 3px;\n"
"	padding-left: 5px;\n"
"    border-radius : 2px;\n"
"\n"
"}\n"
"\n"
"\n"
"QSpinBox::up-button, \n"
"QDateTimeEdit::up-button\n"
"{\n"
"	border-top-right-radius:2px;\n"
"	background-color: #777777;\n"
"    width: 16px; \n"
"    border-width: 1px;\n"
"\n"
"}\n"
"\n"
"\n"
"QSpinBox::up-button:hover, \n"
"QDateTimeEdit::up-button:hover\n"
"{\n"
"	background-color: #585858;\n"
"\n"
"}\n"
"\n"
"\n"
"QSpinBox::up-button:pressed, \n"
"QDateTimeEdit::up-button:pressed\n"
"{\n"
"	background-color: #252525;\n"
"    width: 16px; \n"
"    border-width: 1px;\n"
"\n"
"}\n"
"\n"
"\n"
"QSpinBox::up-arrow,\n"
"QDateTimeEdit::up-arrow\n"
"{\n"
"    image: url(://arrow-up.png);\n"
"    width: 7px;\n"
"    height: 7px;\n"
"\n"
"}\n"
"\n"
"\n"
"QSpinBox::down-button, \n"
"QDateTimeEdit::down-button\n"
"{\n"
"	border-bottom-right-radius:2px;\n"
"	background-color: #777777;\n"
"    width: 16px; \n"
"    border-width: 1px;\n"
"\n"
"}\n"
"\n"
"\n"
"QSpinBox::down-button:hover, \n"
"QDateTimeEdit::down-button:ho"
                        "ver\n"
"{\n"
"	background-color: #585858;\n"
"\n"
"}\n"
"\n"
"\n"
"QSpinBox::down-button:pressed, \n"
"QDateTimeEdit::down-button:pressed\n"
"{\n"
"	background-color: #252525;\n"
"    width: 16px; \n"
"    border-width: 1px;\n"
"\n"
"}\n"
"\n"
"\n"
"QSpinBox::down-arrow,\n"
"QDateTimeEdit::down-arrow\n"
"{\n"
"    image: url(://arrow-down.png);\n"
"    width: 7px;\n"
"    height: 7px;\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QGroupBox-----*/\n"
"QGroupBox \n"
"{\n"
"    border: 1px solid;\n"
"    border-color: #666666;\n"
"	border-radius: 5px;\n"
"    margin-top: 20px;\n"
"\n"
"}\n"
"\n"
"\n"
"QGroupBox::title  \n"
"{\n"
"    background-color: transparent;\n"
"    color: #eee;\n"
"    subcontrol-origin: margin;\n"
"    padding: 5px;\n"
"	border-top-left-radius: 3px;\n"
"	border-top-right-radius: 3px;\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QHeaderView-----*/\n"
"QHeaderView::section\n"
"{\n"
"    background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(60, 60, 60, 255),stop:1 rgba(50, 50, 50, 255));"
                        "\n"
"	border: 1px solid #000;\n"
"    color: #fff;\n"
"    text-align: left;\n"
"	padding: 4px;\n"
"	\n"
"}\n"
"\n"
"\n"
"QHeaderView::section:disabled\n"
"{\n"
"    background-color: #525251;\n"
"    color: #656565;\n"
"\n"
"}\n"
"\n"
"\n"
"QHeaderView::section:checked\n"
"{\n"
"    background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(60, 60, 60, 255),stop:1 rgba(50, 50, 50, 255));\n"
"    color: #fff;\n"
"\n"
"}\n"
"\n"
"\n"
"QHeaderView::section::vertical::first,\n"
"QHeaderView::section::vertical::only-one\n"
"{\n"
"    border-top: 1px solid #353635;\n"
"\n"
"}\n"
"\n"
"\n"
"QHeaderView::section::vertical\n"
"{\n"
"    border-top: 1px solid #353635;\n"
"\n"
"}\n"
"\n"
"\n"
"QHeaderView::section::horizontal::first,\n"
"QHeaderView::section::horizontal::only-one\n"
"{\n"
"    border-left: 1px solid #353635;\n"
"\n"
"}\n"
"\n"
"\n"
"QHeaderView::section::horizontal\n"
"{\n"
"    border-left: 1px solid #353635;\n"
"\n"
"}\n"
"\n"
"\n"
"QTableCornerButton::section\n"
"{\n"
"    b"
                        "ackground-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(60, 60, 60, 255),stop:1 rgba(50, 50, 50, 255));\n"
"	border: 1px solid #000;\n"
"    color: #fff;\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QTreeWidget-----*/\n"
"QTreeView\n"
"{\n"
"	show-decoration-selected: 1;\n"
"	alternate-background-color: #3a3a3a;\n"
"	selection-color: #fff;\n"
"	background-color: #2d2d2d;\n"
"	border: 1px solid gray;\n"
"	padding-top : 5px;\n"
"	color: #fff;\n"
"	font: 8pt;\n"
"\n"
"}\n"
"\n"
"\n"
"QTreeView::item:selected\n"
"{\n"
"	color:#fff;\n"
"	background-color: #b78620;\n"
"	border-radius: 0px;\n"
"\n"
"}\n"
"\n"
"\n"
"QTreeView::item:!selected:hover\n"
"{\n"
"    background-color: #262626;\n"
"    border: none;\n"
"    color: white;\n"
"\n"
"}\n"
"\n"
"\n"
"QTreeView::branch:has-children:!has-siblings:closed,\n"
"QTreeView::branch:closed:has-children:has-siblings \n"
"{\n"
"	image: url(://tree-closed.png);\n"
"\n"
"}\n"
"\n"
"\n"
"QTreeView::branch:open:has-children:!has-siblings,\n"
"QTreeView::branch:op"
                        "en:has-children:has-siblings  \n"
"{\n"
"	image: url(://tree-open.png);\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QListView-----*/\n"
"QListView \n"
"{\n"
"	background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(83, 83, 83, 255),stop:0.293269 rgba(81, 81, 81, 255),stop:0.634615 rgba(79, 79, 79, 255),stop:1 rgba(83, 83, 83, 255));\n"
"    border : none;\n"
"    color: white;\n"
"    show-decoration-selected: 1; \n"
"    outline: 0;\n"
"	border: 1px solid gray;\n"
"\n"
"}\n"
"\n"
"\n"
"QListView::disabled \n"
"{\n"
"	background-color: #656565;\n"
"	color: #1b1b1b;\n"
"    border: 1px solid #656565;\n"
"\n"
"}\n"
"\n"
"\n"
"QListView::item \n"
"{\n"
"	background-color: #2d2d2d;\n"
"    padding: 1px;\n"
"\n"
"}\n"
"\n"
"\n"
"QListView::item:alternate \n"
"{\n"
"    background-color: #3a3a3a;\n"
"\n"
"}\n"
"\n"
"\n"
"QListView::item:selected \n"
"{\n"
"	background-color: #b78620;\n"
"	border: 1px solid #b78620;\n"
"	color: #fff;\n"
"\n"
"}\n"
"\n"
"\n"
"QListView::item:selected:!active \n"
"{\n"
""
                        "	background-color: #b78620;\n"
"	border: 1px solid #b78620;\n"
"	color: #fff;\n"
"\n"
"}\n"
"\n"
"\n"
"QListView::item:selected:active \n"
"{\n"
"	background-color: #b78620;\n"
"	border: 1px solid #b78620;\n"
"	color: #fff;\n"
"\n"
"}\n"
"\n"
"\n"
"QListView::item:hover {\n"
"    background-color: #262626;\n"
"    border: none;\n"
"    color: white;\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QCheckBox-----*/\n"
"QCheckBox\n"
"{\n"
"	background-color: transparent;\n"
"    color: lightgray;\n"
"	border: none;\n"
"\n"
"}\n"
"\n"
"\n"
"QCheckBox::indicator\n"
"{\n"
"    background-color: #323232;\n"
"    border: 1px solid darkgray;\n"
"    width: 12px;\n"
"    height: 12px;\n"
"\n"
"}\n"
"\n"
"\n"
"QCheckBox::indicator:checked\n"
"{\n"
"    image:url(\"./ressources/check.png\");\n"
"	background-color: #b78620;\n"
"    border: 1px solid #3a546e;\n"
"\n"
"}\n"
"\n"
"\n"
"QCheckBox::indicator:unchecked:hover\n"
"{\n"
"	border: 1px solid #b78620; \n"
"\n"
"}\n"
"\n"
"\n"
"QCheckBox::disabled\n"
"{\n"
"	color: #656565;\n"
"\n"
"}"
                        "\n"
"\n"
"\n"
"QCheckBox::indicator:disabled\n"
"{\n"
"	background-color: #656565;\n"
"	color: #656565;\n"
"    border: 1px solid #656565;\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QRadioButton-----*/\n"
"QRadioButton \n"
"{\n"
"	color: lightgray;\n"
"	background-color: transparent;\n"
"\n"
"}\n"
"\n"
"\n"
"QRadioButton::indicator::unchecked:hover \n"
"{\n"
"	background-color: lightgray;\n"
"	border: 2px solid #b78620;\n"
"	border-radius: 6px;\n"
"}\n"
"\n"
"\n"
"QRadioButton::indicator::checked \n"
"{\n"
"	border: 2px solid #b78620;\n"
"	border-radius: 6px;\n"
"	background-color: rgba(183,134,32,20%);  \n"
"	width: 9px; \n"
"	height: 9px; \n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QSlider-----*/\n"
"QSlider::groove:horizontal \n"
"{\n"
"	background-color: transparent;\n"
"	height: 3px;\n"
"\n"
"}\n"
"\n"
"\n"
"QSlider::sub-page:horizontal \n"
"{\n"
"	background-color: #b78620;\n"
"\n"
"}\n"
"\n"
"\n"
"QSlider::add-page:horizontal \n"
"{\n"
"	background-color: #131313;\n"
"\n"
"}\n"
"\n"
"\n"
"QSlider::handle:horizontal \n"
"{\n"
""
                        "	background-color: #b78620;\n"
"	width: 14px;\n"
"	margin-top: -6px;\n"
"	margin-bottom: -6px;\n"
"	border-radius: 6px;\n"
"\n"
"}\n"
"\n"
"\n"
"QSlider::handle:horizontal:hover \n"
"{\n"
"	background-color: #d89e25;\n"
"	border-radius: 6px;\n"
"\n"
"}\n"
"\n"
"\n"
"QSlider::sub-page:horizontal:disabled \n"
"{\n"
"	background-color: #bbb;\n"
"	border-color: #999;\n"
"\n"
"}\n"
"\n"
"\n"
"QSlider::add-page:horizontal:disabled \n"
"{\n"
"	background-color: #eee;\n"
"	border-color: #999;\n"
"\n"
"}\n"
"\n"
"\n"
"QSlider::handle:horizontal:disabled \n"
"{\n"
"	background-color: #eee;\n"
"	border: 1px solid #aaa;\n"
"	border-radius: 3px;\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QScrollBar-----*/\n"
"QScrollBar:horizontal\n"
"{\n"
"    border: 1px solid #222222;\n"
"    background-color: #3d3d3d;\n"
"    height: 15px;\n"
"    margin: 0px 16px 0 16px;\n"
"\n"
"}\n"
"\n"
"\n"
"QScrollBar::handle:horizontal\n"
"{\n"
"	background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(97, 97, 97, 255),stop:1 rg"
                        "ba(90, 90, 90, 255));\n"
"	border: 1px solid #2d2d2d;\n"
"    min-height: 20px;\n"
"\n"
"}\n"
"\n"
"\n"
"QScrollBar::add-line:horizontal\n"
"{\n"
"	background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(97, 97, 97, 255),stop:1 rgba(90, 90, 90, 255));\n"
"	border: 1px solid #2d2d2d;\n"
"    width: 15px;\n"
"    subcontrol-position: right;\n"
"    subcontrol-origin: margin;\n"
"\n"
"}\n"
"\n"
"\n"
"QScrollBar::sub-line:horizontal\n"
"{\n"
"	background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(97, 97, 97, 255),stop:1 rgba(90, 90, 90, 255));\n"
"	border: 1px solid #2d2d2d;\n"
"    width: 15px;\n"
"    subcontrol-position: left;\n"
"    subcontrol-origin: margin;\n"
"\n"
"}\n"
"\n"
"\n"
"QScrollBar::right-arrow:horizontal\n"
"{\n"
"    image: url(://arrow-right.png);\n"
"    width: 6px;\n"
"    height: 6px;\n"
"\n"
"}\n"
"\n"
"\n"
"QScrollBar::left-arrow:horizontal\n"
"{\n"
"    image: url(://arrow-left.png);\n"
"    width: 6px;\n"
"    height: 6px;\n"
""
                        "\n"
"}\n"
"\n"
"\n"
"QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal\n"
"{\n"
"    background: none;\n"
"\n"
"}\n"
"\n"
"\n"
"QScrollBar:vertical\n"
"{\n"
"    background-color: #3d3d3d;\n"
"    width: 16px;\n"
"	border: 1px solid #2d2d2d;\n"
"    margin: 16px 0px 16px 0px;\n"
"\n"
"}\n"
"\n"
"\n"
"QScrollBar::handle:vertical\n"
"{\n"
"    background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(97, 97, 97, 255),stop:1 rgba(90, 90, 90, 255));\n"
"	border: 1px solid #2d2d2d;\n"
"    min-height: 20px;\n"
"\n"
"}\n"
"\n"
"\n"
"QScrollBar::add-line:vertical\n"
"{\n"
"	background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(97, 97, 97, 255),stop:1 rgba(90, 90, 90, 255));\n"
"	border: 1px solid #2d2d2d;\n"
"    height: 15px;\n"
"    subcontrol-position: bottom;\n"
"    subcontrol-origin: margin;\n"
"\n"
"}\n"
"\n"
"\n"
"QScrollBar::sub-line:vertical\n"
"{\n"
"	background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 rgba"
                        "(97, 97, 97, 255),stop:1 rgba(90, 90, 90, 255));\n"
"	border: 1px solid #2d2d2d;\n"
"    height: 15px;\n"
"    subcontrol-position: top;\n"
"    subcontrol-origin: margin;\n"
"\n"
"}\n"
"\n"
"\n"
"QScrollBar::up-arrow:vertical\n"
"{\n"
"    image: url(://arrow-up.png);\n"
"    width: 6px;\n"
"    height: 6px;\n"
"\n"
"}\n"
"\n"
"\n"
"QScrollBar::down-arrow:vertical\n"
"{\n"
"    image: url(://arrow-down.png);\n"
"    width: 6px;\n"
"    height: 6px;\n"
"\n"
"}\n"
"\n"
"\n"
"QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical\n"
"{\n"
"    background: none;\n"
"\n"
"}\n"
"\n"
"\n"
"/*-----QProgressBar-----*/\n"
"QProgressBar\n"
"{\n"
"    border: 1px solid #666666;\n"
"    text-align: center;\n"
"	color: #000;\n"
"	font-weight: bold;\n"
"\n"
"}\n"
"\n"
"\n"
"QProgressBar::chunk\n"
"{\n"
"    background-color: #b78620;\n"
"    width: 30px;\n"
"    margin: 0.5px;\n"
"\n"
"}\n"
"\n"
"\n"
"")
        self.actionExportarExcel = QAction(MainWindow)
        self.actionExportarExcel.setObjectName(u"actionExportarExcel")
        self.actionExportarPDF = QAction(MainWindow)
        self.actionExportarPDF.setObjectName(u"actionExportarPDF")
        self.actionSalir = QAction(MainWindow)
        self.actionSalir.setObjectName(u"actionSalir")
        self.actionVerEstadisticas = QAction(MainWindow)
        self.actionVerEstadisticas.setObjectName(u"actionVerEstadisticas")
        self.actionVerReportes = QAction(MainWindow)
        self.actionVerReportes.setObjectName(u"actionVerReportes")
        self.actionConfiguracion = QAction(MainWindow)
        self.actionConfiguracion.setObjectName(u"actionConfiguracion")
        self.actionBackupBD = QAction(MainWindow)
        self.actionBackupBD.setObjectName(u"actionBackupBD")
        self.actionAcercaDe = QAction(MainWindow)
        self.actionAcercaDe.setObjectName(u"actionAcercaDe")
        self.actionManual = QAction(MainWindow)
        self.actionManual.setObjectName(u"actionManual")
        self.actiondetener = QAction(MainWindow)
        self.actiondetener.setObjectName(u"actiondetener")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(15, 15, 15, 15)
        self.frameHeader = QFrame(self.centralwidget)
        self.frameHeader.setObjectName(u"frameHeader")
        self.frameHeader.setMaximumSize(QSize(16777215, 66))
        self.frameHeader.setFrameShape(QFrame.Shape.NoFrame)
        self.horizontalLayout_header = QHBoxLayout(self.frameHeader)
        self.horizontalLayout_header.setSpacing(15)
        self.horizontalLayout_header.setObjectName(u"horizontalLayout_header")
        self.labelTitle = QLabel(self.frameHeader)
        self.labelTitle.setObjectName(u"labelTitle")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.labelTitle.setFont(font)

        self.horizontalLayout_header.addWidget(self.labelTitle)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_header.addItem(self.horizontalSpacer)

        self.labelBuscar = QLabel(self.frameHeader)
        self.labelBuscar.setObjectName(u"labelBuscar")

        self.horizontalLayout_header.addWidget(self.labelBuscar)

        self.lineEditBuscar = QLineEdit(self.frameHeader)
        self.lineEditBuscar.setObjectName(u"lineEditBuscar")
        self.lineEditBuscar.setMinimumSize(QSize(250, 0))

        self.horizontalLayout_header.addWidget(self.lineEditBuscar)

        self.labelFiltro = QLabel(self.frameHeader)
        self.labelFiltro.setObjectName(u"labelFiltro")

        self.horizontalLayout_header.addWidget(self.labelFiltro)

        self.comboBoxFiltro = QComboBox(self.frameHeader)
        self.comboBoxFiltro.addItem("")
        self.comboBoxFiltro.addItem("")
        self.comboBoxFiltro.addItem("")
        self.comboBoxFiltro.addItem("")
        self.comboBoxFiltro.addItem("")
        self.comboBoxFiltro.addItem("")
        self.comboBoxFiltro.setObjectName(u"comboBoxFiltro")
        self.comboBoxFiltro.setMinimumSize(QSize(150, 0))

        self.horizontalLayout_header.addWidget(self.comboBoxFiltro)

        self.btnActualizar = QPushButton(self.frameHeader)
        self.btnActualizar.setObjectName(u"btnActualizar")

        self.horizontalLayout_header.addWidget(self.btnActualizar)


        self.verticalLayout.addWidget(self.frameHeader)

        self.splitterPrincipal = QSplitter(self.centralwidget)
        self.splitterPrincipal.setObjectName(u"splitterPrincipal")
        self.splitterPrincipal.setMinimumSize(QSize(0, 0))
        self.splitterPrincipal.setOrientation(Qt.Orientation.Horizontal)
        self.splitterPrincipal.setHandleWidth(10)
        self.widgetTabla = QWidget(self.splitterPrincipal)
        self.widgetTabla.setObjectName(u"widgetTabla")
        self.verticalLayout_tabla = QVBoxLayout(self.widgetTabla)
        self.verticalLayout_tabla.setSpacing(8)
        self.verticalLayout_tabla.setObjectName(u"verticalLayout_tabla")
        self.verticalLayout_tabla.setContentsMargins(0, 0, 0, 0)
        self.labelContador = QLabel(self.widgetTabla)
        self.labelContador.setObjectName(u"labelContador")
        font1 = QFont()
        font1.setPointSize(9)
        self.labelContador.setFont(font1)

        self.verticalLayout_tabla.addWidget(self.labelContador)

        self.tableDispositivos = QTableWidget(self.widgetTabla)
        if (self.tableDispositivos.columnCount() < 10):
            self.tableDispositivos.setColumnCount(10)
        __qtablewidgetitem = QTableWidgetItem()
        self.tableDispositivos.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tableDispositivos.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tableDispositivos.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tableDispositivos.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.tableDispositivos.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.tableDispositivos.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.tableDispositivos.setHorizontalHeaderItem(6, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.tableDispositivos.setHorizontalHeaderItem(7, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.tableDispositivos.setHorizontalHeaderItem(8, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.tableDispositivos.setHorizontalHeaderItem(9, __qtablewidgetitem9)
        self.tableDispositivos.setObjectName(u"tableDispositivos")
        self.tableDispositivos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableDispositivos.setAlternatingRowColors(False)
        self.tableDispositivos.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tableDispositivos.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableDispositivos.setSortingEnabled(True)
        self.tableDispositivos.setColumnCount(10)
        self.tableDispositivos.horizontalHeader().setStretchLastSection(True)

        self.verticalLayout_tabla.addWidget(self.tableDispositivos)

        self.splitterPrincipal.addWidget(self.widgetTabla)
        self.widgetDetalles = QWidget(self.splitterPrincipal)
        self.widgetDetalles.setObjectName(u"widgetDetalles")
        self.widgetDetalles.setMinimumSize(QSize(380, 0))
        self.widgetDetalles.setMaximumSize(QSize(450, 16777215))
        self.verticalLayout_detalles = QVBoxLayout(self.widgetDetalles)
        self.verticalLayout_detalles.setSpacing(10)
        self.verticalLayout_detalles.setObjectName(u"verticalLayout_detalles")
        self.verticalLayout_detalles.setContentsMargins(0, 0, 0, 0)
        self.groupBoxInfo = QGroupBox(self.widgetDetalles)
        self.groupBoxInfo.setObjectName(u"groupBoxInfo")
        self.verticalLayout_info = QVBoxLayout(self.groupBoxInfo)
        self.verticalLayout_info.setObjectName(u"verticalLayout_info")
        self.gridLayoutInfo = QGridLayout()
        self.gridLayoutInfo.setObjectName(u"gridLayoutInfo")
        self.gridLayoutInfo.setHorizontalSpacing(10)
        self.gridLayoutInfo.setVerticalSpacing(8)
        self.labelInfoSerial = QLabel(self.groupBoxInfo)
        self.labelInfoSerial.setObjectName(u"labelInfoSerial")
        font2 = QFont()
        font2.setBold(True)
        self.labelInfoSerial.setFont(font2)

        self.gridLayoutInfo.addWidget(self.labelInfoSerial, 0, 0, 1, 1)

        self.labelInfoSerialValue = QLabel(self.groupBoxInfo)
        self.labelInfoSerialValue.setObjectName(u"labelInfoSerialValue")
        self.labelInfoSerialValue.setWordWrap(True)

        self.gridLayoutInfo.addWidget(self.labelInfoSerialValue, 0, 1, 1, 1)

        self.labelInfoDTI = QLabel(self.groupBoxInfo)
        self.labelInfoDTI.setObjectName(u"labelInfoDTI")
        self.labelInfoDTI.setFont(font2)

        self.gridLayoutInfo.addWidget(self.labelInfoDTI, 1, 0, 1, 1)

        self.labelInfoDTIValue = QLabel(self.groupBoxInfo)
        self.labelInfoDTIValue.setObjectName(u"labelInfoDTIValue")

        self.gridLayoutInfo.addWidget(self.labelInfoDTIValue, 1, 1, 1, 1)

        self.labelInfoMAC = QLabel(self.groupBoxInfo)
        self.labelInfoMAC.setObjectName(u"labelInfoMAC")
        self.labelInfoMAC.setFont(font2)

        self.gridLayoutInfo.addWidget(self.labelInfoMAC, 2, 0, 1, 1)

        self.labelInfoMACValue = QLabel(self.groupBoxInfo)
        self.labelInfoMACValue.setObjectName(u"labelInfoMACValue")
        self.labelInfoMACValue.setWordWrap(True)

        self.gridLayoutInfo.addWidget(self.labelInfoMACValue, 2, 1, 1, 1)

        self.labelInfoDisco = QLabel(self.groupBoxInfo)
        self.labelInfoDisco.setObjectName(u"labelInfoDisco")
        self.labelInfoDisco.setFont(font2)

        self.gridLayoutInfo.addWidget(self.labelInfoDisco, 3, 0, 1, 1)

        self.labelInfoDiscoValue = QLabel(self.groupBoxInfo)
        self.labelInfoDiscoValue.setObjectName(u"labelInfoDiscoValue")
        self.labelInfoDiscoValue.setWordWrap(True)

        self.gridLayoutInfo.addWidget(self.labelInfoDiscoValue, 3, 1, 1, 1)


        self.verticalLayout_info.addLayout(self.gridLayoutInfo)


        self.verticalLayout_detalles.addWidget(self.groupBoxInfo)

        self.groupBoxCambio = QGroupBox(self.widgetDetalles)
        self.groupBoxCambio.setObjectName(u"groupBoxCambio")
        self.verticalLayout_cambio = QVBoxLayout(self.groupBoxCambio)
        self.verticalLayout_cambio.setObjectName(u"verticalLayout_cambio")
        self.labelUltimoCambioFecha = QLabel(self.groupBoxCambio)
        self.labelUltimoCambioFecha.setObjectName(u"labelUltimoCambioFecha")
        font3 = QFont()
        font3.setPointSize(9)
        font3.setItalic(True)
        self.labelUltimoCambioFecha.setFont(font3)

        self.verticalLayout_cambio.addWidget(self.labelUltimoCambioFecha)

        self.textEditUltimoCambio = QTextEdit(self.groupBoxCambio)
        self.textEditUltimoCambio.setObjectName(u"textEditUltimoCambio")
        self.textEditUltimoCambio.setMaximumSize(QSize(16777215, 100))
        self.textEditUltimoCambio.setReadOnly(True)

        self.verticalLayout_cambio.addWidget(self.textEditUltimoCambio)

        self.btnVerHistorialCambios = QPushButton(self.groupBoxCambio)
        self.btnVerHistorialCambios.setObjectName(u"btnVerHistorialCambios")

        self.verticalLayout_cambio.addWidget(self.btnVerHistorialCambios)


        self.verticalLayout_detalles.addWidget(self.groupBoxCambio)

        self.groupBoxAcciones = QGroupBox(self.widgetDetalles)
        self.groupBoxAcciones.setObjectName(u"groupBoxAcciones")
        self.verticalLayout_acciones = QVBoxLayout(self.groupBoxAcciones)
        self.verticalLayout_acciones.setSpacing(8)
        self.verticalLayout_acciones.setObjectName(u"verticalLayout_acciones")
        self.btnVerDiagnostico = QPushButton(self.groupBoxAcciones)
        self.btnVerDiagnostico.setObjectName(u"btnVerDiagnostico")

        self.verticalLayout_acciones.addWidget(self.btnVerDiagnostico)

        self.btnVerAplicaciones = QPushButton(self.groupBoxAcciones)
        self.btnVerAplicaciones.setObjectName(u"btnVerAplicaciones")

        self.verticalLayout_acciones.addWidget(self.btnVerAplicaciones)

        self.btnVerAlmacenamiento = QPushButton(self.groupBoxAcciones)
        self.btnVerAlmacenamiento.setObjectName(u"btnVerAlmacenamiento")

        self.verticalLayout_acciones.addWidget(self.btnVerAlmacenamiento)

        self.btnVerMemoria = QPushButton(self.groupBoxAcciones)
        self.btnVerMemoria.setObjectName(u"btnVerMemoria")

        self.verticalLayout_acciones.addWidget(self.btnVerMemoria)


        self.verticalLayout_detalles.addWidget(self.groupBoxAcciones)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_detalles.addItem(self.verticalSpacer)

        self.splitterPrincipal.addWidget(self.widgetDetalles)

        self.verticalLayout.addWidget(self.splitterPrincipal)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        self.statusbar.setFont(font1)
        MainWindow.setStatusBar(self.statusbar)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1280, 23))
        self.menuArchivo = QMenu(self.menubar)
        self.menuArchivo.setObjectName(u"menuArchivo")
        self.menuVer = QMenu(self.menubar)
        self.menuVer.setObjectName(u"menuVer")
        self.menuHerramientas = QMenu(self.menubar)
        self.menuHerramientas.setObjectName(u"menuHerramientas")
        self.menuAyuda = QMenu(self.menubar)
        self.menuAyuda.setObjectName(u"menuAyuda")
        MainWindow.setMenuBar(self.menubar)

        self.menubar.addAction(self.menuArchivo.menuAction())
        self.menubar.addAction(self.menuVer.menuAction())
        self.menubar.addAction(self.menuHerramientas.menuAction())
        self.menubar.addAction(self.menuAyuda.menuAction())
        self.menuArchivo.addAction(self.actionExportarExcel)
        self.menuArchivo.addAction(self.actionExportarPDF)
        self.menuArchivo.addSeparator()
        self.menuArchivo.addAction(self.actionSalir)
        self.menuVer.addAction(self.actionVerEstadisticas)
        self.menuVer.addAction(self.actionVerReportes)
        self.menuHerramientas.addAction(self.actionConfiguracion)
        self.menuHerramientas.addAction(self.actionBackupBD)
        self.menuHerramientas.addAction(self.actiondetener)
        self.menuAyuda.addAction(self.actionAcercaDe)
        self.menuAyuda.addAction(self.actionManual)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Sistema de Inventario - \u00c1rea de Inform\u00e1tica", None))
        self.actionExportarExcel.setText(QCoreApplication.translate("MainWindow", u"Exportar a Excel", None))
        self.actionExportarPDF.setText(QCoreApplication.translate("MainWindow", u"Exportar a PDF", None))
        self.actionSalir.setText(QCoreApplication.translate("MainWindow", u"Salir", None))
        self.actionVerEstadisticas.setText(QCoreApplication.translate("MainWindow", u"Estad\u00edsticas", None))
        self.actionVerReportes.setText(QCoreApplication.translate("MainWindow", u"Generar Reportes", None))
        self.actionConfiguracion.setText(QCoreApplication.translate("MainWindow", u"Configuraci\u00f3n", None))
        self.actionBackupBD.setText(QCoreApplication.translate("MainWindow", u"Respaldar Base de Datos", None))
        self.actionAcercaDe.setText(QCoreApplication.translate("MainWindow", u"Acerca de", None))
        self.actionManual.setText(QCoreApplication.translate("MainWindow", u"Manual de Usuario", None))
        self.actiondetener.setText(QCoreApplication.translate("MainWindow", u"Detener anuncios (broadcast)", None))
#if QT_CONFIG(tooltip)
        self.actiondetener.setToolTip(QCoreApplication.translate("MainWindow", u"Para reducir ruido en la red, ahorrar recursos, prevenir problemas de seguridad/duplicaci\u00f3n y permitir tareas de mantenimiento o apagado ordenado", None))
#endif // QT_CONFIG(tooltip)
        self.labelTitle.setText(QCoreApplication.translate("MainWindow", u"Inventario de Dispositivos", None))
        self.labelBuscar.setText(QCoreApplication.translate("MainWindow", u"Buscar:", None))
        self.lineEditBuscar.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Serial, DTI, Usuario, Modelo...", None))
        self.labelFiltro.setText(QCoreApplication.translate("MainWindow", u"Filtrar:", None))
        self.comboBoxFiltro.setItemText(0, QCoreApplication.translate("MainWindow", u"Todos", None))
        self.comboBoxFiltro.setItemText(1, QCoreApplication.translate("MainWindow", u"Activos", None))
        self.comboBoxFiltro.setItemText(2, QCoreApplication.translate("MainWindow", u"Inactivos", None))
        self.comboBoxFiltro.setItemText(3, QCoreApplication.translate("MainWindow", u"Encendidos", None))
        self.comboBoxFiltro.setItemText(4, QCoreApplication.translate("MainWindow", u"Apagados", None))
        self.comboBoxFiltro.setItemText(5, QCoreApplication.translate("MainWindow", u"Sin Licencia", None))

        self.btnActualizar.setText(QCoreApplication.translate("MainWindow", u"Actualizar", None))
        self.labelContador.setText(QCoreApplication.translate("MainWindow", u"Mostrando 0 dispositivos", None))
        ___qtablewidgetitem = self.tableDispositivos.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("MainWindow", u"Estado", None));
        ___qtablewidgetitem1 = self.tableDispositivos.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("MainWindow", u"DTI", None));
        ___qtablewidgetitem2 = self.tableDispositivos.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("MainWindow", u"Serial", None));
        ___qtablewidgetitem3 = self.tableDispositivos.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("MainWindow", u"Usuario", None));
        ___qtablewidgetitem4 = self.tableDispositivos.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("MainWindow", u"Modelo", None));
        ___qtablewidgetitem5 = self.tableDispositivos.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("MainWindow", u"Procesador", None));
        ___qtablewidgetitem6 = self.tableDispositivos.horizontalHeaderItem(6)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("MainWindow", u"RAM (GB)", None));
        ___qtablewidgetitem7 = self.tableDispositivos.horizontalHeaderItem(7)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("MainWindow", u"GPU", None));
        ___qtablewidgetitem8 = self.tableDispositivos.horizontalHeaderItem(8)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("MainWindow", u"Licencia", None));
        ___qtablewidgetitem9 = self.tableDispositivos.horizontalHeaderItem(9)
        ___qtablewidgetitem9.setText(QCoreApplication.translate("MainWindow", u"IP", None));
        self.groupBoxInfo.setTitle(QCoreApplication.translate("MainWindow", u"Informaci\u00f3n del Dispositivo", None))
        self.labelInfoSerial.setText(QCoreApplication.translate("MainWindow", u"Serial:", None))
        self.labelInfoSerialValue.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.labelInfoDTI.setText(QCoreApplication.translate("MainWindow", u"DTI:", None))
        self.labelInfoDTIValue.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.labelInfoMAC.setText(QCoreApplication.translate("MainWindow", u"MAC:", None))
        self.labelInfoMACValue.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.labelInfoDisco.setText(QCoreApplication.translate("MainWindow", u"Disco:", None))
        self.labelInfoDiscoValue.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.groupBoxCambio.setTitle(QCoreApplication.translate("MainWindow", u"\u00daltimo Cambio Registrado", None))
        self.labelUltimoCambioFecha.setText(QCoreApplication.translate("MainWindow", u"Fecha: -", None))
        self.textEditUltimoCambio.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Seleccione un dispositivo para ver los cambios...", None))
        self.btnVerHistorialCambios.setText(QCoreApplication.translate("MainWindow", u"Ver Historial Completo", None))
        self.groupBoxAcciones.setTitle(QCoreApplication.translate("MainWindow", u"Acciones", None))
        self.btnVerDiagnostico.setText(QCoreApplication.translate("MainWindow", u"Ver Diagn\u00f3stico Completo", None))
        self.btnVerAplicaciones.setText(QCoreApplication.translate("MainWindow", u"Ver Aplicaciones Instaladas", None))
        self.btnVerAlmacenamiento.setText(QCoreApplication.translate("MainWindow", u"Ver Detalles de Almacenamiento", None))
        self.btnVerMemoria.setText(QCoreApplication.translate("MainWindow", u"Ver Detalles de Memoria RAM", None))
        self.menuArchivo.setTitle(QCoreApplication.translate("MainWindow", u"Archivo", None))
        self.menuVer.setTitle(QCoreApplication.translate("MainWindow", u"Ver", None))
        self.menuHerramientas.setTitle(QCoreApplication.translate("MainWindow", u"Herramientas", None))
        self.menuAyuda.setTitle(QCoreApplication.translate("MainWindow", u"Ayuda", None))
    # retranslateUi

