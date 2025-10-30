from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
import sys
from ui.inventario_ui import Ui_MainWindow  # Importar el .ui convertido
from sql_specs.consultas_sql import cursor, abrir_consulta, connection  # Funciones de DB
import logica_servidor as ls  # Importar lógica del servidor
from logica_Hilo import Hilo  # Para operaciones en background

class InventarioWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Hilos para operaciones de red
        self.hilo_servidor = None
        self.hilo_escaneo = None
        self.hilo_consulta = None
        
        # Agregar emojis a los botones después de cargar la UI
        #self.agregar_iconos_texto()
        
        # Conectar señales
        self.ui.tableDispositivos.itemSelectionChanged.connect(self.on_dispositivo_seleccionado)
        self.ui.lineEditBuscar.textChanged.connect(self.filtrar_dispositivos)
        self.ui.comboBoxFiltro.currentTextChanged.connect(self.aplicar_filtro)
        self.ui.btnActualizar.clicked.connect(self.iniciar_escaneo_completo)  # Cambio: ahora hace escaneo completo
        
        # Botones de acciones
        self.ui.btnVerDiagnostico.clicked.connect(self.ver_diagnostico)
        self.ui.btnVerAplicaciones.clicked.connect(self.ver_aplicaciones)
        self.ui.btnVerAlmacenamiento.clicked.connect(self.ver_almacenamiento)
        self.ui.btnVerMemoria.clicked.connect(self.ver_memoria)
        self.ui.btnVerHistorialCambios.clicked.connect(self.ver_historial)
        
        # Botón de escaneo inicial
        if hasattr(self.ui, 'btnEscanear'):
            self.ui.btnEsc
            anear.clicked.connect(self.iniciar_escaneo_completo) # type: ignore
        self.configurar_tabla()
        
        # Deshabilitar botones hasta seleccionar dispositivo
        self.deshabilitar_botones_detalle()
        
        # Cargar datos iniciales
        self.cargar_dispositivos()
        
        # Iniciar servidor en segundo plano
        self.iniciar_servidor()
    
    
    def iniciar_servidor(self):
        """Inicia el servidor TCP en segundo plano para recibir datos de clientes."""
        def iniciar_tcp():
            ls.main()
        
        self.hilo_servidor = Hilo(iniciar_tcp)
        self.hilo_servidor.start()
        self.ui.statusbar.showMessage("✓ Servidor iniciado - Esperando conexiones de clientes", 3000)
        print("Servidor TCP iniciado en puerto 5255")
    
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
        # Limpiar tabla
        self.ui.tableDispositivos.setRowCount(0)
        
        try:
            # Consultar dispositivos desde la DB
            sql, params = abrir_consulta("Dispositivos-select.sql")
            cursor.execute(sql, params)
            dispositivos = cursor.fetchall()
            
            # Consultar estados activos más recientes (por fecha)
            sql_activo = """SELECT a1.Dispositivos_serial, a1.powerOn 
                           FROM activo a1
                           INNER JOIN (
                               SELECT Dispositivos_serial, MAX(date) as max_date
                               FROM activo
                               GROUP BY Dispositivos_serial
                           ) a2 ON a1.Dispositivos_serial = a2.Dispositivos_serial 
                               AND a1.date = a2.max_date"""
            cursor.execute(sql_activo)
            estados = {row[0]: row[1] for row in cursor.fetchall()}
            
        except Exception as e:
            print(f"Error consultando base de datos: {e}")
            import traceback
            traceback.print_exc()
            self.ui.statusbar.showMessage(f"❌ Error cargando datos: {e}", 5000)
            # Usar datos de prueba si falla la DB
            dispositivos = []
            estados = {}
        
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
    
    def iniciar_escaneo_completo(self):
        """
        Flujo completo:
        1. Escanear red con optimized_block_scanner.py
        2. Poblar DB inicial con IPs/MACs del CSV
        3. Solicitar datos completos a cada cliente
        4. Actualizar tabla
        """
        self.ui.statusbar.showMessage("🔍 Paso 1/4: Iniciando escaneo de red...", 0)
        self.ui.btnActualizar.setEnabled(False)
        
        # Paso 1: Escanear red
        self.ejecutar_escaneo_red()
    
    def ejecutar_escaneo_red(self):
        """Paso 1: Ejecuta optimized_block_scanner.py"""
        def callback_escaneo():
            import subprocess
            try:
                print("\n=== Ejecutando escaneo de red ===")
                result = subprocess.run(
                    ['python', 'optimized_block_scanner.py', '--start', '100', '--end', '119', '--use-broadcast-probe'],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                print(result.stdout)
                if result.stderr:
                    print("Errores:", result.stderr)
                
                if result.returncode == 0:
                    print("✓ Escaneo completado exitosamente")
                    return True
                else:
                    print(f"✗ Error en escaneo: código {result.returncode}")
                    return False
            except Exception as e:
                print(f"✗ Excepción en escaneo: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        self.hilo_escaneo = Hilo(callback_escaneo)
        self.hilo_escaneo.terminado.connect(self.on_escaneo_terminado)
        self.hilo_escaneo.error.connect(self.on_escaneo_error)
        self.hilo_escaneo.start()
    
    def on_escaneo_terminado(self, resultado):
        """Callback Paso 1 completado"""
        if resultado:
            self.ui.statusbar.showMessage("✓ Paso 1/4: Escaneo completado - Poblando DB inicial...", 0)
            # Paso 2: Poblar DB con CSV
            self.poblar_db_desde_csv()
        else:
            self.ui.statusbar.showMessage("❌ Error en escaneo de red", 5000)
            self.ui.btnActualizar.setEnabled(True)
    
    def on_escaneo_error(self, error):
        """Error en Paso 1"""
        self.ui.statusbar.showMessage(f"❌ Error en escaneo: {error}", 5000)
        self.ui.btnActualizar.setEnabled(True)
    
    def poblar_db_desde_csv(self):
        """Paso 2: Lee CSV y crea registros básicos en DB (solo IP/MAC)"""
        def callback_poblar():
            try:
                print("\n=== Poblando DB desde CSV ===")
                # Cargar IPs del CSV
                ips_macs = ls.cargar_ips_desde_csv()
                
                if not ips_macs:
                    print("⚠ No se encontraron IPs en el CSV")
                    return 0
                
                insertados = 0
                for ip, mac in ips_macs:
                    if not mac:
                        continue
                    
                    # Verificar si ya existe
                    sql_check, params = ls.sql.abrir_consulta("Dispositivos-select.sql", {"MAC": mac})
                    ls.sql.cursor.execute(sql_check, params)
                    existe = ls.sql.cursor.fetchone()
                    
                    if not existe:
                        # Insertar dispositivo básico (sin serial, solo con IP/MAC)
                        # serial, DTI, user, MAC, model, processor, GPU, RAM, disk, license_status, ip, activo
                        datos_basicos = (
                            f"TEMP_{mac.replace(':', '')}",  # Serial temporal basado en MAC
                            None,  # DTI
                            None,  # user
                            mac,   # MAC
                            "Pendiente escaneo",  # model
                            None,  # processor
                            None,  # GPU
                            0,     # RAM
                            None,  # disk
                            False, # license_status
                            ip,    # ip
                            False  # activo (aún no confirmado)
                        )
                        ls.sql.setDevice(datos_basicos)
                        insertados += 1
                        print(f"  + Insertado: {ip} ({mac})")
                    else:
                        # Actualizar solo la IP si cambió
                        serial_existente = existe[0]
                        ls.sql.cursor.execute(
                            "UPDATE Dispositivos SET ip = ? WHERE serial = ?",
                            (ip, serial_existente)
                        )
                        print(f"  ↻ Actualizado IP: {ip} ({mac})")
                
                ls.sql.connection.commit()
                print(f"✓ DB poblada: {insertados} nuevos, {len(ips_macs) - insertados} existentes")
                return insertados
                
            except Exception as e:
                print(f"✗ Error poblando DB: {e}")
                import traceback
                traceback.print_exc()
                return 0
        
        self.hilo_poblado = Hilo(callback_poblar)
        self.hilo_poblado.terminado.connect(self.on_poblado_terminado)
        self.hilo_poblado.error.connect(self.on_poblado_error)
        self.hilo_poblado.start()
    
    def on_poblado_terminado(self, insertados):
        """Callback Paso 2 completado"""
        self.ui.statusbar.showMessage(f"✓ Paso 2/4: DB poblada ({insertados} nuevos) - Anunciando servidor...", 0)
        # Paso 3: Anunciar servidor y esperar conexiones
        self.anunciar_y_esperar_clientes()
    
    def on_poblado_error(self, error):
        """Error en Paso 2"""
        self.ui.statusbar.showMessage(f"❌ Error poblando DB: {error}", 5000)
        self.ui.btnActualizar.setEnabled(True)
    
    def anunciar_y_esperar_clientes(self):
        """Paso 3: Anuncia servidor y consulta cada cliente"""
        def callback_anuncio():
            try:
                print("\n=== Anunciando servidor y consultando clientes ===")
                # Anunciar presencia
                print("📡 Enviando broadcast...")
                ls.anunciar_ip()
                
                # Esperar un poco para que clientes respondan
                import time
                time.sleep(2)
                
                # Consultar dispositivos desde CSV
                print("🔍 Consultando dispositivos...")
                activos, total = ls.consultar_dispositivos_desde_csv()
                
                print(f"✓ Consulta completada: {activos}/{total} dispositivos respondieron")
                return (activos, total)
                
            except Exception as e:
                print(f"✗ Error en consulta: {e}")
                import traceback
                traceback.print_exc()
                return (0, 0)
        
        self.hilo_consulta = Hilo(callback_anuncio)
        self.hilo_consulta.terminado.connect(self.on_consulta_terminada)
        self.hilo_consulta.error.connect(self.on_consulta_error)
        self.hilo_consulta.start()
    
    def on_consulta_terminada(self, resultado):
        """Callback Paso 3 completado"""
        activos, total = resultado
        self.ui.statusbar.showMessage(f"✓ Paso 3/4: {activos}/{total} clientes respondieron - Actualizando vista...", 0)
        # Paso 4: Recargar tabla
        self.finalizar_escaneo_completo()
    
    def on_consulta_error(self, error):
        """Error en Paso 3"""
        self.ui.statusbar.showMessage(f"❌ Error consultando clientes: {error}", 5000)
        self.ui.btnActualizar.setEnabled(True)
    
    def finalizar_escaneo_completo(self):
        """Paso 4: Recargar tabla con datos actualizados"""
        print("\n=== Finalizando escaneo completo ===")
        self.cargar_dispositivos()
        self.ui.statusbar.showMessage("✅ Escaneo completo finalizado exitosamente", 5000)
        self.ui.btnActualizar.setEnabled(True)
        print("✓ Proceso completado\n")


if __name__ == '__main__':
    # Usar instancia existente si ya hay una, o crear nueva
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    
    window = InventarioWindow()
    window.show()
    sys.exit(app.exec())