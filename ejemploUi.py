from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
import sys
from ui.inventario_ui import Ui_MainWindow  # Importar el .ui convertido
# from sql_specs.consultas_sql import cursor, abrir_consulta  # Tus funciones de DB

class InventarioWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Agregar emojis a los botones después de cargar la UI
        self.agregar_iconos_texto()
        
        # Conectar señales
        self.ui.tableDispositivos.itemSelectionChanged.connect(self.on_dispositivo_seleccionado)
        self.ui.lineEditBuscar.textChanged.connect(self.filtrar_dispositivos)
        self.ui.comboBoxFiltro.currentTextChanged.connect(self.aplicar_filtro)
        self.ui.btnActualizar.clicked.connect(self.cargar_dispositivos)
        
        # Botones de acciones
        self.ui.btnVerDiagnostico.clicked.connect(self.ver_diagnostico)
        self.ui.btnVerAplicaciones.clicked.connect(self.ver_aplicaciones)
        self.ui.btnVerAlmacenamiento.clicked.connect(self.ver_almacenamiento)
        self.ui.btnVerMemoria.clicked.connect(self.ver_memoria)
        self.ui.btnVerHistorialCambios.clicked.connect(self.ver_historial)
        
        # Configurar tabla
        self.configurar_tabla()
        
        # Deshabilitar botones hasta seleccionar dispositivo
        self.deshabilitar_botones_detalle()
        
        # Cargar datos iniciales
        self.cargar_dispositivos()
    
    def agregar_iconos_texto(self):
        """Agrega emojis/iconos a los botones después de cargar la UI"""
        self.ui.btnActualizar.setText("🔄 Actualizar")
        self.ui.btnVerHistorialCambios.setText("📋 Ver Historial Completo")
        self.ui.btnVerDiagnostico.setText("📄 Ver Diagnóstico Completo")
        self.ui.btnVerAplicaciones.setText("💿 Ver Aplicaciones Instaladas")
        self.ui.btnVerAlmacenamiento.setText("💾 Ver Detalles de Almacenamiento")
        self.ui.btnVerMemoria.setText("🔧 Ver Detalles de Memoria RAM")
    
    def configurar_tabla(self):
        """Configura el ancho de columnas y otros ajustes de la tabla"""
        header = self.ui.tableDispositivos.horizontalHeader()
        
        # Ajustar ancho de columnas
        self.ui.tableDispositivos.setColumnWidth(0, 80)   # Estado
        self.ui.tableDispositivos.setColumnWidth(1, 60)   # DTI
        self.ui.tableDispositivos.setColumnWidth(2, 150)  # Serial
        self.ui.tableDispositivos.setColumnWidth(3, 120)  # Usuario
        self.ui.tableDispositivos.setColumnWidth(4, 180)  # Modelo
        self.ui.tableDispositivos.setColumnWidth(5, 200)  # Procesador
        self.ui.tableDispositivos.setColumnWidth(6, 80)   # RAM
        self.ui.tableDispositivos.setColumnWidth(7, 150)  # GPU
        self.ui.tableDispositivos.setColumnWidth(8, 80)   # Licencia
        # IP se estira automáticamente
    
    def cargar_dispositivos(self):
        """Carga los dispositivos desde la base de datos"""
        # NOTA: Descomenta cuando conectes con tu DB real
        # from sql_specs.consultas_sql import cursor, abrir_consulta
        
        # Limpiar tabla
        self.ui.tableDispositivos.setRowCount(0)
        
        # DATOS DE PRUEBA - Reemplazar con consulta real
        dispositivos = [
            ("SN001", 101, "jperez", "00:1A:2B:3C:4D:5E", "Dell Optiplex 7090", 
             "Intel Core i7-11700", "Intel UHD Graphics 750", 16, "512GB SSD", True, "192.168.1.50", True),
            ("SN002", 102, "mgarcia", "00:1A:2B:3C:4D:5F", "HP EliteDesk 800 G6", 
             "Intel Core i5-10500", "Intel UHD Graphics 630", 8, "256GB SSD", True, "192.168.1.51", True),
            ("SN003", 103, "alopez", "00:1A:2B:3C:4D:60", "Lenovo ThinkCentre M90q", 
             "Intel Core i5-10400", "Intel UHD Graphics 630", 8, "512GB SSD", False, "192.168.1.52", True),
        ]
        
        # Estados de ejemplo (True = Encendido)
        estados = {
            "SN001": True,
            "SN002": False,
            "SN003": True,
        }
        
        # CONSULTA REAL (descomenta y adapta):
        # sql, params = abrir_consulta("Dispositivos-select.sql")
        # cursor.execute(sql, params)
        # dispositivos = cursor.fetchall()
        
        # sql_activo = """SELECT Dispositivos_serial, powerOn 
        #                 FROM activo 
        #                 WHERE id IN (SELECT MAX(id) FROM activo GROUP BY Dispositivos_serial)"""
        # cursor.execute(sql_activo)
        # estados = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Llenar tabla
        for dispositivo in dispositivos:
            row_position = self.ui.tableDispositivos.rowCount()
            self.ui.tableDispositivos.insertRow(row_position)
            
            # Desempaquetar datos
            serial, dti, user, mac, model, processor, gpu, ram, disk, license_status, ip, activo = dispositivo
            
            # Columna Estado (con color y emoji)
            estado_item = QtWidgets.QTableWidgetItem()
            if not activo:
                estado_item.setText("❌ Inactivo")
                estado_item.setBackground(QBrush(QColor(220, 220, 220)))
            elif estados.get(serial, False):
                estado_item.setText("🟢 Encendido")
                estado_item.setBackground(QBrush(QColor(200, 255, 200)))
            else:
                estado_item.setText("🔴 Apagado")
                estado_item.setBackground(QBrush(QColor(255, 220, 220)))
            self.ui.tableDispositivos.setItem(row_position, 0, estado_item)
            
            # Resto de columnas
            self.ui.tableDispositivos.setItem(row_position, 1, QtWidgets.QTableWidgetItem(str(dti or '-')))
            self.ui.tableDispositivos.setItem(row_position, 2, QtWidgets.QTableWidgetItem(serial))
            self.ui.tableDispositivos.setItem(row_position, 3, QtWidgets.QTableWidgetItem(user or '-'))
            self.ui.tableDispositivos.setItem(row_position, 4, QtWidgets.QTableWidgetItem(model or '-'))
            self.ui.tableDispositivos.setItem(row_position, 5, QtWidgets.QTableWidgetItem(processor or '-'))
            self.ui.tableDispositivos.setItem(row_position, 6, QtWidgets.QTableWidgetItem(str(ram or '-')))
            self.ui.tableDispositivos.setItem(row_position, 7, QtWidgets.QTableWidgetItem(gpu or '-'))
            
            # Licencia con color
            lic_item = QtWidgets.QTableWidgetItem("✅ Activa" if license_status else "❌ Inactiva")
            if not license_status:
                lic_item.setForeground(QBrush(QColor(200, 0, 0)))
            self.ui.tableDispositivos.setItem(row_position, 8, lic_item)
            
            self.ui.tableDispositivos.setItem(row_position, 9, QtWidgets.QTableWidgetItem(ip or '-'))
        
        # Actualizar contador
        self.ui.labelContador.setText(f"Mostrando {len(dispositivos)} dispositivos")
        self.ui.statusbar.showMessage(f"✓ Datos actualizados - {len(dispositivos)} dispositivos cargados", 3000)
    
    def on_dispositivo_seleccionado(self):
        """Cuando se selecciona un dispositivo en la tabla"""
        selected_items = self.ui.tableDispositivos.selectedItems()
        if not selected_items:
            self.deshabilitar_botones_detalle()
            return
        
        # Obtener serial de la fila seleccionada
        row = selected_items[0].row()
        serial = self.ui.tableDispositivos.item(row, 2).text() # type: ignore
        
        # Cargar detalles
        self.cargar_detalles_dispositivo(serial)
        self.habilitar_botones_detalle()
    
    def cargar_detalles_dispositivo(self, serial):
        """Carga los detalles del dispositivo seleccionado"""
        # DATOS DE PRUEBA - Reemplazar con consulta real
        if serial == "SN001":
            dti, mac, disk = 101, "00:1A:2B:3C:4D:5E", "512GB SSD"
            ultimo_cambio = ("jperez", "Intel Core i7-11700", "Intel UHD 750", 16, 
                           "512GB SSD", True, "192.168.1.50", "2024-10-15 14:30:00")
        elif serial == "SN002":
            dti, mac, disk = 102, "00:1A:2B:3C:4D:5F", "256GB SSD"
            ultimo_cambio = ("mgarcia", "Intel Core i5-10500", "Intel UHD 630", 8, 
                           "256GB SSD", True, "192.168.1.51", "2024-09-20 10:15:00")
        else:
            dti, mac, disk = 103, "00:1A:2B:3C:4D:60", "512GB SSD"
            ultimo_cambio = None
        
        # CONSULTA REAL (descomenta):
        # sql, params = abrir_consulta("Dispositivos-select.sql", {"serial": serial})
        # cursor.execute(sql, params)
        # dispositivo = cursor.fetchone()
        
        # Actualizar labels de información
        self.ui.labelInfoSerialValue.setText(serial)
        self.ui.labelInfoDTIValue.setText(str(dti or '-'))
        self.ui.labelInfoMACValue.setText(mac or '-')
        self.ui.labelInfoDiscoValue.setText(disk or '-')
        
        # Cargar último cambio
        # sql_cambio = """SELECT user, processor, GPU, RAM, disk, license_status, ip, date 
        #                 FROM registro_cambios 
        #                 WHERE Dispositivos_serial = ? 
        #                 ORDER BY date DESC LIMIT 1"""
        # cursor.execute(sql_cambio, (serial,))
        # ultimo_cambio = cursor.fetchone()
        
        if ultimo_cambio:
            user, processor, gpu, ram, disk, lic, ip, fecha = ultimo_cambio
            self.ui.labelUltimoCambioFecha.setText(f"Fecha: {fecha}")
            
            # Formatear cambios con HTML
            texto_cambio = f"""
            <b>Usuario:</b> {user or '-'}<br>
            <b>Procesador:</b> {processor or '-'}<br>
            <b>GPU:</b> {gpu or '-'}<br>
            <b>RAM:</b> {ram or '-'} GB<br>
            <b>Disco:</b> {disk or '-'}<br>
            <b>Licencia:</b> {'Activa' if lic else 'Inactiva'}<br>
            <b>IP:</b> {ip or '-'}
            """
            self.ui.textEditUltimoCambio.setHtml(texto_cambio)
        else:
            self.ui.labelUltimoCambioFecha.setText("Fecha: Sin cambios registrados")
            self.ui.textEditUltimoCambio.setPlainText("No hay cambios registrados para este dispositivo.")
    
    def deshabilitar_botones_detalle(self):
        """Deshabilita botones cuando no hay selección"""
        self.ui.btnVerDiagnostico.setEnabled(False)
        self.ui.btnVerAplicaciones.setEnabled(False)
        self.ui.btnVerAlmacenamiento.setEnabled(False)
        self.ui.btnVerMemoria.setEnabled(False)
        self.ui.btnVerHistorialCambios.setEnabled(False)
        
        # Limpiar info
        self.ui.labelInfoSerialValue.setText('-')
        self.ui.labelInfoDTIValue.setText('-')
        self.ui.labelInfoMACValue.setText('-')
        self.ui.labelInfoDiscoValue.setText('-')
        self.ui.labelUltimoCambioFecha.setText('Fecha: -')
        self.ui.textEditUltimoCambio.setPlainText('Seleccione un dispositivo para ver los cambios...')
    
    def habilitar_botones_detalle(self):
        """Habilita botones cuando hay selección"""
        self.ui.btnVerDiagnostico.setEnabled(True)
        self.ui.btnVerAplicaciones.setEnabled(True)
        self.ui.btnVerAlmacenamiento.setEnabled(True)
        self.ui.btnVerMemoria.setEnabled(True)
        self.ui.btnVerHistorialCambios.setEnabled(True)
    
    def filtrar_dispositivos(self, texto):
        """Filtra dispositivos según texto de búsqueda"""
        for row in range(self.ui.tableDispositivos.rowCount()):
            match = False
            for col in range(self.ui.tableDispositivos.columnCount()):
                item = self.ui.tableDispositivos.item(row, col)
                if item and texto.lower() in item.text().lower():
                    match = True
                    break
            self.ui.tableDispositivos.setRowHidden(row, not match)
        
        # Actualizar contador
        visible_count = sum(1 for row in range(self.ui.tableDispositivos.rowCount()) 
                          if not self.ui.tableDispositivos.isRowHidden(row))
        self.ui.labelContador.setText(f"Mostrando {visible_count} dispositivos")
    
    def aplicar_filtro(self, filtro):
        """Aplica filtro según combo seleccionado"""
        for row in range(self.ui.tableDispositivos.rowCount()):
            estado_item = self.ui.tableDispositivos.item(row, 0)
            lic_item = self.ui.tableDispositivos.item(row, 8)
            
            mostrar = True
            if filtro == "Activos":
                mostrar = "Inactivo" not in estado_item.text() # type: ignore
            elif filtro == "Inactivos":
                mostrar = "Inactivo" in estado_item.text() # type: ignore
            elif filtro == "Encendidos":
                mostrar = "Encendido" in estado_item.text() # type: ignore
            elif filtro == "Apagados":
                mostrar = "Apagado" in estado_item.text() # type: ignore
            elif filtro == "Sin Licencia":
                mostrar = "Inactiva" in lic_item.text() # type: ignore
            
            self.ui.tableDispositivos.setRowHidden(row, not mostrar)
        
        # Actualizar contador
        visible_count = sum(1 for row in range(self.ui.tableDispositivos.rowCount()) 
                          if not self.ui.tableDispositivos.isRowHidden(row))
        self.ui.labelContador.setText(f"Mostrando {visible_count} dispositivos")
    
    def ver_diagnostico(self):
        """Abre ventana de diagnóstico completo"""
        selected = self.ui.tableDispositivos.selectedItems()
        if selected:
            serial = self.ui.tableDispositivos.item(selected[0].row(), 2).text() # type: ignore
            QtWidgets.QMessageBox.information(self, "Diagnóstico", 
                                            f"Abriendo diagnóstico completo de {serial}")
    
    def ver_aplicaciones(self):
        """Abre ventana de aplicaciones instaladas"""
        selected = self.ui.tableDispositivos.selectedItems()
        if selected:
            serial = self.ui.tableDispositivos.item(selected[0].row(), 2).text() # type: ignore
            QtWidgets.QMessageBox.information(self, "Aplicaciones", 
                                            f"Mostrando aplicaciones instaladas en {serial}")
    
    def ver_almacenamiento(self):
        """Abre ventana de detalles de almacenamiento"""
        selected = self.ui.tableDispositivos.selectedItems()
        if selected:
            serial = self.ui.tableDispositivos.item(selected[0].row(), 2).text() # type: ignore
            QtWidgets.QMessageBox.information(self, "Almacenamiento", 
                                            f"Detalles de almacenamiento de {serial}")
    
    def ver_memoria(self):
        """Abre ventana de detalles de memoria"""
        selected = self.ui.tableDispositivos.selectedItems()
        if selected:
            serial = self.ui.tableDispositivos.item(selected[0].row(), 2).text() # type: ignore
            QtWidgets.QMessageBox.information(self, "Memoria RAM", 
                                            f"Detalles de memoria RAM de {serial}")
    
    def ver_historial(self):
        """Abre ventana de historial completo de cambios"""
        selected = self.ui.tableDispositivos.selectedItems()
        if selected:
            serial = self.ui.tableDispositivos.item(selected[0].row(), 2).text() # type: ignore
            QtWidgets.QMessageBox.information(self, "Historial", 
                                            f"Historial completo de cambios de {serial}")


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = InventarioWindow()
    window.show()
    sys.exit(app.exec())