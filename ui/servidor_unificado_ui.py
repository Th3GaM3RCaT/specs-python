# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'servidor_unificado.ui'
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
from PySide6.QtWidgets import (QApplication, QMainWindow, QMenuBar, QSizePolicy,
    QStatusBar, QWidget)

class Ui_servidor_unificado(object):
    def setupUi(self, servidor_unificado):
        if not servidor_unificado.objectName():
            servidor_unificado.setObjectName(u"servidor_unificado")
        servidor_unificado.resize(800, 600)
        self.centralwidget = QWidget(servidor_unificado)
        self.centralwidget.setObjectName(u"centralwidget")
        servidor_unificado.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(servidor_unificado)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 21))
        servidor_unificado.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(servidor_unificado)
        self.statusbar.setObjectName(u"statusbar")
        servidor_unificado.setStatusBar(self.statusbar)

        self.retranslateUi(servidor_unificado)

        QMetaObject.connectSlotsByName(servidor_unificado)
    # setupUi

    def retranslateUi(self, servidor_unificado):
        servidor_unificado.setWindowTitle(QCoreApplication.translate("servidor_unificado", u"MainWindow", None))
    # retranslateUi

