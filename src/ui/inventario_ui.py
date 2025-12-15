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
"    @import url(\"Combinear.qss\");\n"
"  ")
        self.actionExportarExcel = QAction(MainWindow)
        self.actionExportarExcel.setObjectName(u"actionExportarExcel")
        self.actionExportarCSV = QAction(MainWindow)
        self.actionExportarCSV.setObjectName(u"actionExportarCSV")
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
        self.lineEditBuscar.setMinimumSize(QSize(200, 0))

        self.horizontalLayout_header.addWidget(self.lineEditBuscar)

        self.ip_start_input = QLineEdit(self.frameHeader)
        self.ip_start_input.setObjectName(u"ip_start_input")

        self.horizontalLayout_header.addWidget(self.ip_start_input)

        self.ip_end_input = QLineEdit(self.frameHeader)
        self.ip_end_input.setObjectName(u"ip_end_input")

        self.horizontalLayout_header.addWidget(self.ip_end_input)

        self.scan_button = QPushButton(self.frameHeader)
        self.scan_button.setObjectName(u"scan_button")

        self.horizontalLayout_header.addWidget(self.scan_button)

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
        self.menubar.setGeometry(QRect(0, 0, 1280, 21))
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
        self.menuArchivo.addAction(self.actionExportarCSV)
        self.menuArchivo.addSeparator()
        self.menuArchivo.addAction(self.actionSalir)
        self.menuVer.addAction(self.actionVerEstadisticas)
        self.menuVer.addAction(self.actionVerReportes)
        self.menuHerramientas.addAction(self.actionConfiguracion)
        self.menuHerramientas.addAction(self.actionBackupBD)
        self.menuAyuda.addAction(self.actionAcercaDe)
        self.menuAyuda.addAction(self.actionManual)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Sistema de Inventario - \u00c1rea de Inform\u00e1tica", None))
        MainWindow.setProperty(u"qss_file", QCoreApplication.translate("MainWindow", u"ui/Combinear.qss", None))
        self.actionExportarExcel.setText(QCoreApplication.translate("MainWindow", u"Exportar a Excel", None))
        self.actionExportarCSV.setText(QCoreApplication.translate("MainWindow", u"Exportar a CSV", None))
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
        self.ip_start_input.setPlaceholderText(QCoreApplication.translate("MainWindow", u"IP Inicio", None))
        self.ip_end_input.setPlaceholderText(QCoreApplication.translate("MainWindow", u"IP Fin (opcional)", None))
        self.scan_button.setText(QCoreApplication.translate("MainWindow", u"Iniciar Escaneo", None))
        self.labelFiltro.setText(QCoreApplication.translate("MainWindow", u"Filtrar:", None))
        self.comboBoxFiltro.setItemText(0, QCoreApplication.translate("MainWindow", u"Todos", None))
        self.comboBoxFiltro.setItemText(1, QCoreApplication.translate("MainWindow", u"Activos", None))
        self.comboBoxFiltro.setItemText(2, QCoreApplication.translate("MainWindow", u"Inactivos", None))
        self.comboBoxFiltro.setItemText(3, QCoreApplication.translate("MainWindow", u"Encendidos", None))
        self.comboBoxFiltro.setItemText(4, QCoreApplication.translate("MainWindow", u"Apagados", None))
        self.comboBoxFiltro.setItemText(5, QCoreApplication.translate("MainWindow", u"Sin Licencia", None))

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

