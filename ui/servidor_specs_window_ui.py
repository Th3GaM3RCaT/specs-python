# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'servidor_specs_window.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QMainWindow, QMenuBar,
    QPushButton, QScrollArea, QSizePolicy, QStatusBar,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(543, 331)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.frame_2 = QFrame(self.centralwidget)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setMinimumSize(QSize(260, 270))
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout = QGridLayout(self.frame_2)
        self.gridLayout.setObjectName(u"gridLayout")
        self.frame_3 = QFrame(self.frame_2)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMaximumSize(QSize(240, 103))
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_3 = QGridLayout(self.frame_3)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.usuario_label = QLabel(self.frame_3)
        self.usuario_label.setObjectName(u"usuario_label")

        self.gridLayout_3.addWidget(self.usuario_label, 5, 0, 1, 1)

        self.mac_label = QLabel(self.frame_3)
        self.mac_label.setObjectName(u"mac_label")

        self.gridLayout_3.addWidget(self.mac_label, 6, 0, 1, 1)

        self.modelo_label = QLabel(self.frame_3)
        self.modelo_label.setObjectName(u"modelo_label")

        self.gridLayout_3.addWidget(self.modelo_label, 3, 0, 1, 1)

        self.equipo_comboBox = QComboBox(self.frame_3)
        self.equipo_comboBox.setObjectName(u"equipo_comboBox")
        self.equipo_comboBox.setMinimumSize(QSize(0, 20))

        self.gridLayout_3.addWidget(self.equipo_comboBox, 2, 0, 1, 1)


        self.gridLayout.addWidget(self.frame_3, 1, 0, 1, 1)

        self.frame_4 = QFrame(self.frame_2)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setMaximumSize(QSize(240, 103))
        self.frame_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_4 = QGridLayout(self.frame_4)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.actualizar_pushButton = QPushButton(self.frame_4)
        self.actualizar_pushButton.setObjectName(u"actualizar_pushButton")

        self.gridLayout_4.addWidget(self.actualizar_pushButton, 3, 0, 1, 1, Qt.AlignmentFlag.AlignRight)

        self.scan_pushButton = QPushButton(self.frame_4)
        self.scan_pushButton.setObjectName(u"scan_pushButton")

        self.gridLayout_4.addWidget(self.scan_pushButton, 4, 0, 1, 1, Qt.AlignmentFlag.AlignRight)


        self.gridLayout.addWidget(self.frame_4, 2, 0, 1, 1)

        self.label = QLabel(self.frame_2)
        self.label.setObjectName(u"label")
        self.label.setMaximumSize(QSize(240, 16))

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)


        self.horizontalLayout.addWidget(self.frame_2, 0, Qt.AlignmentFlag.AlignTop)

        self.frame = QFrame(self.centralwidget)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_2 = QGridLayout(self.frame)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.info_scrollArea = QScrollArea(self.frame)
        self.info_scrollArea.setObjectName(u"info_scrollArea")
        self.info_scrollArea.setFrameShadow(QFrame.Shadow.Sunken)
        self.info_scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.info_scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 223, 226))
        self.info_scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.info_scrollArea, 1, 0, 1, 1)

        self.label_5 = QLabel(self.frame)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout_2.addWidget(self.label_5, 0, 0, 1, 1)


        self.horizontalLayout.addWidget(self.frame)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 543, 21))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.usuario_label.setText(QCoreApplication.translate("MainWindow", u"Usuario:", None))
        self.mac_label.setText(QCoreApplication.translate("MainWindow", u"MAC:", None))
        self.modelo_label.setText(QCoreApplication.translate("MainWindow", u"Modelo:", None))
        self.actualizar_pushButton.setText(QCoreApplication.translate("MainWindow", u"Actualizar dispositivos", None))
        self.scan_pushButton.setText(QCoreApplication.translate("MainWindow", u"Escanear red", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Selecci\u00f3n del dispositivo:", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Informaci\u00f3n del dispositivo:", None))
    # retranslateUi

