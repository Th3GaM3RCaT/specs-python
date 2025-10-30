# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'specs_window.ui'
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
from PySide6.QtWidgets import (QApplication, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QMenu, QMenuBar,
    QPushButton, QScrollArea, QSizePolicy, QStatusBar,
    QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.setEnabled(True)
        MainWindow.resize(355, 500)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QSize(350, 500))
        MainWindow.setMaximumSize(QSize(700, 16777215))
        icon = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentPrint))
        MainWindow.setWindowIcon(icon)
        self.actionProgramar_hora_de_ejecuci_n = QAction(MainWindow)
        self.actionProgramar_hora_de_ejecuci_n.setObjectName(u"actionProgramar_hora_de_ejecuci_n")
        self.actionDetener_ejecuci_n = QAction(MainWindow)
        self.actionDetener_ejecuci_n.setObjectName(u"actionDetener_ejecuci_n")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_3 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.frame_2 = QFrame(self.centralwidget)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setMinimumSize(QSize(0, 157))
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame_2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.title_textLabel = QLabel(self.frame_2)
        self.title_textLabel.setObjectName(u"title_textLabel")

        self.verticalLayout_2.addWidget(self.title_textLabel)

        self.info_scrollArea = QScrollArea(self.frame_2)
        self.info_scrollArea.setObjectName(u"info_scrollArea")
        self.info_scrollArea.setEnabled(True)
        self.info_scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.info_scrollArea.setWidgetResizable(True)
        self.info_scrollAreaWidgetContents = QWidget()
        self.info_scrollAreaWidgetContents.setObjectName(u"info_scrollAreaWidgetContents")
        self.info_scrollAreaWidgetContents.setEnabled(True)
        self.info_scrollAreaWidgetContents.setGeometry(QRect(0, 0, 301, 345))
        self.formLayout = QFormLayout(self.info_scrollAreaWidgetContents)
        self.formLayout.setObjectName(u"formLayout")
        self.widget = QWidget(self.info_scrollAreaWidgetContents)
        self.widget.setObjectName(u"widget")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.widget)

        self.info_label = QLabel(self.info_scrollAreaWidgetContents)
        self.info_label.setObjectName(u"info_label")
        self.info_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.info_label.setWordWrap(False)
        self.info_label.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse|Qt.TextInteractionFlag.TextSelectableByMouse)

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.info_label)

        self.info_scrollArea.setWidget(self.info_scrollAreaWidgetContents)

        self.verticalLayout_2.addWidget(self.info_scrollArea)


        self.verticalLayout_3.addWidget(self.frame_2)

        self.frame = QFrame(self.centralwidget)
        self.frame.setObjectName(u"frame")
        self.frame.setMaximumSize(QSize(337, 44))
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.run_button = QPushButton(self.frame)
        self.run_button.setObjectName(u"run_button")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.run_button.sizePolicy().hasHeightForWidth())
        self.run_button.setSizePolicy(sizePolicy1)
        self.run_button.setMaximumSize(QSize(231, 16777215))
        self.run_button.setToolTipDuration(-1)

        self.horizontalLayout.addWidget(self.run_button)

        self.send_button = QPushButton(self.frame)
        self.send_button.setObjectName(u"send_button")
        self.send_button.setEnabled(False)
        self.send_button.setMaximumSize(QSize(80, 16777215))

        self.horizontalLayout.addWidget(self.send_button, 0, Qt.AlignmentFlag.AlignRight)


        self.verticalLayout_3.addWidget(self.frame)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setEnabled(True)
        self.menubar.setGeometry(QRect(0, 0, 355, 21))
        self.menuOpciones = QMenu(self.menubar)
        self.menuOpciones.setObjectName(u"menuOpciones")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        self.statusbar.setEnabled(True)
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuOpciones.menuAction())
        self.menuOpciones.addAction(self.actionProgramar_hora_de_ejecuci_n)
        self.menuOpciones.addAction(self.actionDetener_ejecuci_n)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Specs", None))
        self.actionProgramar_hora_de_ejecuci_n.setText(QCoreApplication.translate("MainWindow", u"Programar hora de ejecuci\u00f3n", None))
        self.actionDetener_ejecuci_n.setText(QCoreApplication.translate("MainWindow", u"Detener ejecuci\u00f3n", None))
        self.title_textLabel.setText(QCoreApplication.translate("MainWindow", u"Informe de especificaciones del dispositivo", None))
        self.info_label.setText(QCoreApplication.translate("MainWindow", u"Genere el informe para continuar...", None))
#if QT_CONFIG(tooltip)
        self.run_button.setToolTip("")
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(whatsthis)
        self.run_button.setWhatsThis("")
#endif // QT_CONFIG(whatsthis)
        self.run_button.setText(QCoreApplication.translate("MainWindow", u"Generar informe", None))
#if QT_CONFIG(shortcut)
        self.run_button.setShortcut("")
#endif // QT_CONFIG(shortcut)
        self.send_button.setText(QCoreApplication.translate("MainWindow", u"Enviar", None))
        self.menuOpciones.setTitle(QCoreApplication.translate("MainWindow", u"Opciones", None))
    # retranslateUi

