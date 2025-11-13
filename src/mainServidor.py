from PySide6 import QtWidgets, QtCore
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import QMainWindow
import sys
import asyncio
from ui.inventario_ui import Ui_MainWindow  # Importar el .ui convertido
from sql.ejecutar_sql import cursor, abrir_consulta  # Funciones de DB
import sql.ejecutar_sql as sql_mod
from logica import logica_servidor as ls  # Importar lógica del servidor
from logica.logica_Hilo import Hilo, HiloConProgreso  # Para operaciones en background
# Utilitario compartido de ping asíncrono (evitar duplicación)
from logica.ping_utils import ping_host

# Constantes de colores para estados de dispositivos
COLOR_ENCENDIDO = "green"
COLOR_APAGADO = "darkred"
COLOR_SIN_IP = "grey"
COLOR_VERIFICANDO = "grey"

def actualizar_estado_item(item: QtWidgets.QTableWidgetItem, estado: str):
    """Actualiza el texto y color de un QTableWidgetItem según el estado.
    
    Args:
        item: QTableWidgetItem a actualizar
        estado: 'encendido', 'apagado', 'sin_ip', o 'verificando'
    """
    if estado == 'encendido':
        item.setText("Encendido")
        item.setBackground(QBrush(QColor(COLOR_ENCENDIDO)))
    elif estado == 'apagado':
        item.setText("Apagado")
        item.setBackground(QBrush(QColor(COLOR_APAGADO)))
    elif estado == 'sin_ip':
        item.setText("[?] Sin IP")
        item.setBackground(QBrush(QColor(COLOR_SIN_IP)))
    elif estado == 'verificando':
        item.setText("[...]")
        item.setBackground(QBrush(QColor(COLOR_VERIFICANDO)))


class IPAddressTableWidgetItem(QtWidgets.QTableWidgetItem):
    """QTableWidgetItem personalizado que ordena direcciones IP numéricamente.
    
    Convierte la IP a una tupla de enteros para ordenamiento correcto:
    Ejemplo: "10.100.1.12" -> (10, 100, 1, 12) < (10, 100, 1, 110)
    """
    
    def __lt__(self, other):
        """Operador menor que (<) para ordenamiento."""
        try:
            # Convertir ambas IPs a tuplas de enteros
            self_ip = tuple(int(part) for part in self.text().split('.'))
            other_ip = tuple(int(part) for part in other.text().split('.'))
            return self_ip < other_ip
        except (ValueError, AttributeError):
            # Si no son IPs válidas, usar ordenamiento alfabético por defecto
            return super().__lt__(other)


class InventarioWindow(QMainWindow, Ui_MainWindow):
    # Atributos de instancia (anotaciones) para Pylance
    from typing import Optional as _Opt  # solo para anotación local
    server_mgr: _Opt[ls.ServerManager]
    ip_to_row: dict

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Hilos para operaciones de red
        self.hilo_servidor = None
        self.hilo_escaneo = None
        self.hilo_consulta = None

        # Ruta del último CSV generado por Scanner (si aplica)
        self._last_csv = None

        # Facade server manager (puede ser None si no se pudo instanciar)
        self.server_mgr = None

        # Mapa de IP a fila de tabla para actualización en tiempo real
        self.ip_to_row = {}

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

        # Botón de escaneo inicial (opcional)
        btn_escanear = getattr(self.ui, 'btnEscanear', None)
        if btn_escanear:
            btn_escanear.clicked.connect(self.iniciar_escaneo_completo)
        self.configurar_tabla()

        # Deshabilitar botones hasta seleccionar dispositivo
        self.deshabilitar_botones_detalle()

        # Cargar datos iniciales y verificar si hay datos
        self.cargar_datos_iniciales()

        # Iniciar servidor en segundo plano
        self.iniciar_servidor()
        
        # Timer para verificación automática de estados cada 10 segundos
        self.timer_estados = QtCore.QTimer(self)
        self.timer_estados.timeout.connect(self.verificar_estados_automatico)
        self.timer_estados.start(10000)  # 10 segundos
    
    def cargar_datos_iniciales(self):
        """Carga datos de la DB. Si no hay datos, inicia actualización automática."""
        try:
            # Verificar si hay dispositivos en la DB
            cursor.execute("SELECT COUNT(*) FROM Dispositivos")
            count = cursor.fetchone()[0]
            
            if count > 0:
                # Hay datos, cargarlos
                print(f">> Cargando {count} dispositivos de la DB...")
                self.cargar_dispositivos()
            else:
                # No hay datos, iniciar actualización automática
                print(">> DB vacía - Iniciando actualización automática...")
                self.ui.statusbar.showMessage(">> DB vacía - Iniciando escaneo automático...", 0)
                # Esperar 1 segundo y luego iniciar escaneo
                QtCore.QTimer.singleShot(1000, self.iniciar_escaneo_completo)
        except Exception as e:
            print(f"Error verificando DB: {e}")
            self.ui.statusbar.showMessage(f"ERROR: No se pudo acceder a la DB", 5000)
    
    
    def iniciar_servidor(self):
        """Inicia el servidor TCP en segundo plano para recibir datos de clientes."""
        # Asegurar que el schema de la DB existe (útil en la primera ejecución o en ejecutable)
        try:
            try:
                sql_mod.inicializar_db()
            except Exception as e:
                # No cortar el arranque si la inicialización falla; mostrarse en consola para diagnóstico
                print(f"[WARN] Inicialización de DB falló: {e}")
        except Exception:
            # Si importar el módulo falla por alguna razón, seguir adelante
            pass

        # Instanciar ServerManager como facade si está disponible
        try:
            self.server_mgr = ls.ServerManager()
        except Exception:
            self.server_mgr = None

        def iniciar_tcp():
            if self.server_mgr:
                self.server_mgr.start_tcp_server()
            else:
                ls.main()

        self.hilo_servidor = Hilo(iniciar_tcp)
        self.hilo_servidor.start()
        self.ui.statusbar.showMessage(">> Servidor iniciado - Esperando conexiones de clientes", 3000)
        print("Servidor TCP iniciado en puerto 5255")
    
    def configurar_tabla(self):
        """Configura el ancho de columnas y otros ajustes de la tabla"""
        header = self.ui.tableDispositivos.horizontalHeader()
        
        # Ajustar ancho de columnas
        self.ui.tableDispositivos.setColumnWidth(0, 80)   # Estado
        self.ui.tableDispositivos.setColumnWidth(1, 60)   # DTI
        self.ui.tableDispositivos.setColumnWidth(2, 90)  # Serial
        self.ui.tableDispositivos.setColumnWidth(3, 120)  # Usuario
        self.ui.tableDispositivos.setColumnWidth(4, 180)  # Modelo
        self.ui.tableDispositivos.setColumnWidth(5, 200)  # Procesador
        self.ui.tableDispositivos.setColumnWidth(6, 80)   # RAM
        self.ui.tableDispositivos.setColumnWidth(7, 150)  # GPU
        self.ui.tableDispositivos.setColumnWidth(8, 85)   # Licencia
        # IP se estira automáticamente
    
    def cargar_dispositivos(self, verificar_ping=True):
        """Carga los dispositivos desde la base de datos y opcionalmente verifica estado con ping
        
        Args:
            verificar_ping (bool): Si False, carga estados desde tabla 'activo' sin hacer ping.
                                   Usar False después de escaneo completo para no sobrescribir estados.
        """
        # Limpiar tabla
        self.ui.tableDispositivos.setRowCount(0)
        
        try:
            # Consultar dispositivos desde la DB
            sql, params = abrir_consulta("Dispositivos-select.sql")
            cursor.execute(sql, params)
            dispositivos = cursor.fetchall()
            
            if not dispositivos:
                self.ui.statusbar.showMessage(">> No hay dispositivos en la DB", 3000)
                return
            
            # Limpiar mapa ip_to_row
            self.ip_to_row.clear()
            
            # Llenar tabla primero con estado "Verificando..." o desde DB
            for dispositivo in dispositivos:
                row_position = self.ui.tableDispositivos.rowCount()
                self.ui.tableDispositivos.insertRow(row_position)
                
                # Desempaquetar datos
                serial, dti, user, mac, model, processor, gpu, ram, disk, license_status, ip, activo = dispositivo
                
                # Guardar mapeo ip -> row
                if ip:
                    self.ip_to_row[ip] = row_position
                
                # Columna Estado
                estado_item = QtWidgets.QTableWidgetItem()
                if verificar_ping:
                    # Inicialmente "Verificando..." (haremos ping)
                    actualizar_estado_item(estado_item, 'verificando')
                else:
                    # Cargar estado desde tabla 'activo' (ya verificado por escaneo completo)
                    try:
                        sql_activo = "SELECT powerOn FROM activo WHERE Dispositivos_serial = ? ORDER BY date DESC LIMIT 1"
                        cursor.execute(sql_activo, (serial,))
                        estado_db = cursor.fetchone()
                        
                        if estado_db:
                            actualizar_estado_item(estado_item, 'encendido' if estado_db[0] else 'apagado')
                        else:
                            actualizar_estado_item(estado_item, 'sin_ip')
                    except Exception as e:
                        print(f"Error cargando estado para {serial}: {e}")
                        actualizar_estado_item(estado_item, 'sin_ip')
                
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
                lic_item = QtWidgets.QTableWidgetItem("[OK] Activa" if license_status else "[X] Inactiva")
                if not license_status:
                    lic_item.setForeground(QBrush(QColor("darkred")))
                self.ui.tableDispositivos.setItem(row_position, 8, lic_item)
                
                # IP con ordenamiento numérico personalizado
                ip_item = IPAddressTableWidgetItem(ip or '-')
                self.ui.tableDispositivos.setItem(row_position, 9, ip_item)
            
            # Actualizar contador
            self.ui.labelContador.setText(f"Mostrando {len(dispositivos)} dispositivos")
            
            # Verificar estado de conexión en background SOLO si verificar_ping=True
            if verificar_ping:
                self._verificar_estados_ping(dispositivos, verbose=True)
            else:
                print(f">> Estados cargados desde DB (sin ping) - {len(dispositivos)} dispositivos")
            
        except Exception as e:
            print(f"Error consultando base de datos: {e}")
            import traceback
            traceback.print_exc()
            self.ui.statusbar.showMessage(f"ERROR: Error cargando datos: {e}", 5000)
    
    def verificar_estados_automatico(self):
        """Verificación automática silenciosa de estados cada 10 segundos"""
        # Solo verificar si hay dispositivos en la tabla
        if self.ui.tableDispositivos.rowCount() == 0:
            return
        
        # Obtener lista de dispositivos actuales de la tabla
        dispositivos = []
        for row in range(self.ui.tableDispositivos.rowCount()):
            ip_item = self.ui.tableDispositivos.item(row, 9)  # Columna IP
            if ip_item:
                ip = ip_item.text()
                dispositivos.append((row, ip))
        
        # Ejecutar verificación silenciosa
        self._verificar_estados_ping(dispositivos, verbose=False)
    
    def _verificar_estados_ping(self, dispositivos_data, verbose=True):
        """Verifica el estado de conexión (ping) de dispositivos en background.
        
        Args:
            dispositivos_data: Lista de tuplas (row, ip) o lista de tuplas de DB
            verbose: Si True, muestra mensajes en consola/statusbar. Si False, silencioso.
        
        Note:
            Función consolidada que reemplaza verificar_estados_conexion y 
            verificar_estados_conexion_silencioso para evitar duplicación.
        """
        def verificar_estados():
            async def ping_dispositivo(row, ip):
                """Hace ping a un dispositivo y retorna resultado"""
                try:
                    if not ip or ip == '-':
                        return (row, False, "sin_ip")

                    conectado = await ping_host(ip, 1.0)
                    return (row, conectado, ip)
                except Exception:
                    return (row, False, ip)
            
            async def verificar_todos():
                # Crear tareas para todos los dispositivos
                tareas = []
                for item in dispositivos_data:
                    # Detectar formato: (row, ip) o tupla de DB
                    if isinstance(item, tuple) and len(item) == 2:
                        row, ip = item
                    else:
                        # Tupla de DB: IP está en posición 10
                        row = dispositivos_data.index(item)
                        ip = item[10]
                    
                    tareas.append(ping_dispositivo(row, ip))
                
                # Ejecutar todos los pings en paralelo
                resultados = await asyncio.gather(*tareas, return_exceptions=True)
                return resultados
            
            # Ejecutar verificación asíncrona
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                resultados = loop.run_until_complete(verificar_todos())
                return resultados
            finally:
                loop.close()
        
        # Ejecutar en hilo separado
        def callback_estados(resultados):
            # Actualizar UI con resultados (estamos en el thread principal)
            for resultado in resultados:
                if isinstance(resultado, tuple):
                    row, conectado, ip = resultado
                    estado_item = self.ui.tableDispositivos.item(row, 0)
                    
                    if estado_item:
                        if ip == "sin_ip":
                            actualizar_estado_item(estado_item, 'sin_ip')
                        elif conectado:
                            actualizar_estado_item(estado_item, 'encendido')
                        else:
                            actualizar_estado_item(estado_item, 'apagado')
            
            # Mensaje solo si verbose=True
            if verbose:
                print(f">> Verificación de estados completada")
        
        self.hilo_verificacion = Hilo(verificar_estados)
        self.hilo_verificacion.terminado.connect(callback_estados)
        self.hilo_verificacion.start()
        
        if verbose:
            print(">> Verificando estado de conexión de dispositivos...")
    
    def on_consulta_progreso(self, datos):
        """Callback para actualizar estado en tiempo real durante escaneo y consulta de dispositivos"""
        try:
            # Detectar tipo de progreso
            tipo = datos.get('tipo')
            
            # Progreso del SCANNER (escaneo de red)
            if tipo == 'segmento':
                segmento = datos.get('segmento_actual')
                idx = datos.get('segmento_index')
                total_seg = datos.get('segmentos_totales')
                mensaje = datos.get('mensaje', '')
                self.ui.statusbar.showMessage(f"[ESCANEO {idx}/{total_seg}] {mensaje}", 0)
                print(f">> {mensaje}")
                return
            
            elif tipo == 'bloque':
                mensaje = datos.get('mensaje', '')
                self.ui.statusbar.showMessage(f"[ESCANEO] {mensaje}", 0)
                # No imprimir en consola para evitar spam
                return
            
            elif tipo == 'fase':
                fase = datos.get('fase')
                mensaje = datos.get('mensaje', '')
                self.ui.statusbar.showMessage(f"[{fase.upper()}] {mensaje}", 0)
                print(f">> {mensaje}")
                return
            
            # Progreso de CONSULTA de dispositivos (ping + solicitud de datos)
            ip = datos.get('ip')
            activo = datos.get('activo')
            index = datos.get('index')
            total = datos.get('total')
            
            # Actualizar barra de estado con progreso de consulta
            if index is not None and total is not None:
                self.ui.statusbar.showMessage(f"[CONSULTA {index}/{total}] Verificando: {ip or '?'}", 0)
            
            # Actualizar tabla si tenemos el mapeo
            if ip and ip in self.ip_to_row:
                row = self.ip_to_row[ip]
                estado_item = self.ui.tableDispositivos.item(row, 0)
                
                if estado_item:
                    actualizar_estado_item(estado_item, 'encendido' if activo else 'apagado')
            
            # Mostrar progreso en consola (solo cada 10 dispositivos para no saturar)
            if index is not None and total is not None and (index % 10 == 0 or index == total):
                print(f">> Consultando dispositivo {index}/{total}: {ip} - {'Encendido' if activo else 'Apagado'}")
        
        except Exception as e:
            print(f"Error en on_consulta_progreso: {e}")
    
    def on_dispositivo_seleccionado(self):
        """Cuando se selecciona un dispositivo en la tabla"""
        selected_items = self.ui.tableDispositivos.selectedItems()
        if not selected_items:
            self.deshabilitar_botones_detalle()
            return
        
        # Obtener serial de la fila seleccionada
        row = selected_items[0].row()
        serial_item = self.ui.tableDispositivos.item(row, 2)
        if not serial_item:
            return
        serial = serial_item.text()
        
        # Cargar detalles
        self.cargar_detalles_dispositivo(serial)
        self.habilitar_botones_detalle()
    
    def cargar_detalles_dispositivo(self, serial):
        """Carga los detalles del dispositivo seleccionado"""
        # CONSULTA REAL: Obtener datos del dispositivo
        sql, params = abrir_consulta("Dispositivos-select.sql", {"serial": serial})
        cursor.execute(sql, params)
        dispositivo = cursor.fetchone()
        
        if not dispositivo:
            # Si no hay datos, limpiar labels
            self.ui.labelInfoSerialValue.setText(serial)
            self.ui.labelInfoDTIValue.setText('-')
            self.ui.labelInfoMACValue.setText('-')
            self.ui.labelInfoDiscoValue.setText('-')
            return
        
        # Desempaquetar datos del dispositivo
        # serial, DTI, user, MAC, model, processor, GPU, RAM, disk, license_status, ip, activo
        db_serial, dti, user, mac, model, processor, gpu, ram, disk, license_status, ip, activo = dispositivo
        
        # Actualizar labels de información
        self.ui.labelInfoSerialValue.setText(serial)
        self.ui.labelInfoDTIValue.setText(str(dti or '-'))
        self.ui.labelInfoMACValue.setText(mac or '-')
        self.ui.labelInfoDiscoValue.setText(disk or '-')
        
        # Cargar último cambio
        sql_cambio = """SELECT user, processor, GPU, RAM, disk, license_status, ip, date 
                        FROM registro_cambios 
                        WHERE Dispositivos_serial = ? 
                        ORDER BY date DESC LIMIT 1"""
        cursor.execute(sql_cambio, (serial,))
        ultimo_cambio = cursor.fetchone()
        
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
            if filtro == "Activos" and estado_item:
                mostrar = "Inactivo" not in estado_item.text()
            elif filtro == "Inactivos" and estado_item:
                mostrar = "Inactivo" in estado_item.text()
            elif filtro == "Encendidos" and estado_item:
                mostrar = "Encendido" in estado_item.text()
            elif filtro == "Apagados" and estado_item:
                mostrar = "Apagado" in estado_item.text()
            elif filtro == "Sin Licencia" and lic_item:
                mostrar = "Inactiva" in lic_item.text()
            
            self.ui.tableDispositivos.setRowHidden(row, not mostrar)
        
        # Actualizar contador
        visible_count = sum(1 for row in range(self.ui.tableDispositivos.rowCount()) 
                          if not self.ui.tableDispositivos.isRowHidden(row))
        self.ui.labelContador.setText(f"Mostrando {visible_count} dispositivos")
    
    def ver_diagnostico(self):
        """Abre ventana de diagnóstico completo"""
        selected = self.ui.tableDispositivos.selectedItems()
        if selected:
            serial_item = self.ui.tableDispositivos.item(selected[0].row(), 2)
            if serial_item:
                serial = serial_item.text()
                
                # Consultar información de diagnóstico
                sql, params = abrir_consulta("informacion_diagnostico-select.sql", {"Dispositivos_serial": serial})
                cursor.execute(sql, params)
                diagnostico = cursor.fetchone()
                
                # Crear ventana de diálogo
                dialog = QtWidgets.QDialog(self)
                dialog.setWindowTitle(f"Diagnóstico Completo - {serial}")
                dialog.resize(600, 400)
                
                layout = QtWidgets.QVBoxLayout(dialog)
                
                # Texto con información
                text_edit = QtWidgets.QTextEdit()
                text_edit.setReadOnly(True)
                
                if diagnostico:
                    # informacion_diagnostico: id, Dispositivos_serial, dxdiag_output_txt
                    texto = f"<h2>Diagnóstico DirectX</h2><pre>{diagnostico[2] or 'No hay información de diagnóstico'}</pre>"
                else:
                    texto = "<p>No hay información de diagnóstico para este dispositivo.</p>"
                
                text_edit.setHtml(texto)
                layout.addWidget(text_edit)
                
                # Botón cerrar
                btn_cerrar = QtWidgets.QPushButton("Cerrar")
                btn_cerrar.clicked.connect(dialog.close)
                layout.addWidget(btn_cerrar)
                
                dialog.exec()
    
    def ver_aplicaciones(self):
        """Abre ventana de aplicaciones instaladas"""
        selected = self.ui.tableDispositivos.selectedItems()
        if selected:
            serial_item = self.ui.tableDispositivos.item(selected[0].row(), 2)
            if serial_item:
                serial = serial_item.text()
                
                # Consultar aplicaciones
                sql, params = abrir_consulta("aplicaciones-select.sql", {"Dispositivos_serial": serial})
                cursor.execute(sql, params)
                aplicaciones = cursor.fetchall()
                
                # Crear ventana de diálogo
                dialog = QtWidgets.QDialog(self)
                dialog.setWindowTitle(f"Aplicaciones Instaladas - {serial}")
                dialog.resize(800, 500)
                
                layout = QtWidgets.QVBoxLayout(dialog)
                
                # Tabla de aplicaciones
                table = QtWidgets.QTableWidget()
                table.setColumnCount(3)
                table.setHorizontalHeaderLabels(["Nombre", "Versión", "Editor"])
                table.horizontalHeader().setStretchLastSection(True)
                
                if aplicaciones:
                    table.setRowCount(len(aplicaciones))
                    for i, app in enumerate(aplicaciones):
                        # aplicaciones SQL: Dispositivos_serial, name, version, publisher, id
                        # Indices:           0,                  1,    2,       3,         4
                        table.setItem(i, 0, QtWidgets.QTableWidgetItem(app[1] or '-'))  # name
                        table.setItem(i, 1, QtWidgets.QTableWidgetItem(app[2] or '-'))  # version
                        table.setItem(i, 2, QtWidgets.QTableWidgetItem(app[3] or '-'))  # publisher
                else:
                    table.setRowCount(1)
                    table.setItem(0, 0, QtWidgets.QTableWidgetItem("No hay aplicaciones registradas"))
                
                layout.addWidget(table)
                
                # Botón cerrar
                btn_cerrar = QtWidgets.QPushButton("Cerrar")
                btn_cerrar.clicked.connect(dialog.close)
                layout.addWidget(btn_cerrar)
                
                dialog.exec()
    
    def ver_almacenamiento(self):
        """Abre ventana de detalles de almacenamiento"""
        selected = self.ui.tableDispositivos.selectedItems()
        if selected:
            serial_item = self.ui.tableDispositivos.item(selected[0].row(), 2)
            if serial_item:
                serial = serial_item.text()
                
                # Consultar almacenamiento
                sql, params = abrir_consulta("almacenamiento-select.sql", {"Dispositivos_serial": serial})
                cursor.execute(sql, params)
                discos = cursor.fetchall()
                
                # Crear ventana de diálogo
                dialog = QtWidgets.QDialog(self)
                dialog.setWindowTitle(f"Detalles de Almacenamiento - {serial}")
                dialog.resize(700, 400)
                
                layout = QtWidgets.QVBoxLayout(dialog)
                
                # Tabla de discos
                table = QtWidgets.QTableWidget()
                table.setColumnCount(4)
                table.setHorizontalHeaderLabels(["Unidad", "Tipo", "Capacidad (GB)", "Fecha"])
                table.horizontalHeader().setStretchLastSection(True)
                
                if discos:
                    table.setRowCount(len(discos))
                    for i, disco in enumerate(discos):
                        # almacenamiento SQL: Dispositivos_serial, nombre, capacidad, tipo, actual, id, fecha_instalacion
                        # Indices:            0,                  1,      2,         3,     4,      5,  6
                        table.setItem(i, 0, QtWidgets.QTableWidgetItem(disco[1] or '-'))  # nombre (unidad)
                        table.setItem(i, 1, QtWidgets.QTableWidgetItem(disco[3] or '-'))  # tipo
                        table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(disco[2] or '-')))  # capacidad
                        fecha = disco[5][:10]
                        table.setItem(i, 3, QtWidgets.QTableWidgetItem(fecha))
                else:
                    table.setRowCount(1)
                    table.setItem(0, 0, QtWidgets.QTableWidgetItem("No hay información de almacenamiento"))
                
                layout.addWidget(table)
                
                # Botón cerrar
                btn_cerrar = QtWidgets.QPushButton("Cerrar")
                btn_cerrar.clicked.connect(dialog.close)
                layout.addWidget(btn_cerrar)
                
                dialog.exec()
    
    def ver_memoria(self):
        """Abre ventana de detalles de memoria"""
        selected = self.ui.tableDispositivos.selectedItems()
        if selected:
            serial_item = self.ui.tableDispositivos.item(selected[0].row(), 2)
            if serial_item:
                serial = serial_item.text()
                
                # Consultar memoria
                sql, params = abrir_consulta("memoria-select.sql", {"Dispositivos_serial": serial})
                cursor.execute(sql, params)
                modulos = cursor.fetchall()
                
                # Crear ventana de diálogo
                dialog = QtWidgets.QDialog(self)
                dialog.setWindowTitle(f"Detalles de Memoria RAM - {serial}")
                dialog.resize(700, 400)
                
                layout = QtWidgets.QVBoxLayout(dialog)
                
                # Tabla de módulos de RAM
                table = QtWidgets.QTableWidget()
                table.setColumnCount(5)
                table.setHorizontalHeaderLabels(["Módulo", "Fabricante", "Capacidad (GB)", "Velocidad (MHz)", "Número de Serie"])
                table.horizontalHeader().setStretchLastSection(True)
                
                if modulos:
                    table.setRowCount(len(modulos))
                    for i, mod in enumerate(modulos):
                        # memoria SQL: Dispositivos_serial, modulo, fabricante, capacidad, velocidad, numero_serie, actual, id, fecha_instalacion
                        # Indices:     0,                  1,      2,          3,          4,         5,             6,      7,  8
                        table.setItem(i, 0, QtWidgets.QTableWidgetItem(mod[1] or '-'))  # modulo
                        table.setItem(i, 1, QtWidgets.QTableWidgetItem(mod[2] or '-'))  # fabricante
                        table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(mod[3] or '-')))  # capacidad
                        table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(mod[4] or '-')))  # velocidad
                        table.setItem(i, 4, QtWidgets.QTableWidgetItem(mod[5] or '-'))  # numero_serie
                else:
                    table.setRowCount(1)
                    table.setItem(0, 0, QtWidgets.QTableWidgetItem("No hay información de memoria"))
                
                layout.addWidget(table)
                
                # Botón cerrar
                btn_cerrar = QtWidgets.QPushButton("Cerrar")
                btn_cerrar.clicked.connect(dialog.close)
                layout.addWidget(btn_cerrar)
                
                dialog.exec()
    
    def ver_historial(self):
        """Abre ventana de historial completo de cambios"""
        selected = self.ui.tableDispositivos.selectedItems()
        if selected:
            serial_item = self.ui.tableDispositivos.item(selected[0].row(), 2)
            if serial_item:
                serial = serial_item.text()
                
                # Consultar historial completo
                sql = """SELECT user, processor, GPU, RAM, disk, license_status, ip, date 
                         FROM registro_cambios 
                         WHERE Dispositivos_serial = ? 
                         ORDER BY date DESC"""
                cursor.execute(sql, (serial,))
                cambios = cursor.fetchall()
                
                # Crear ventana de diálogo
                dialog = QtWidgets.QDialog(self)
                dialog.setWindowTitle(f"Historial de Cambios - {serial}")
                dialog.resize(900, 500)
                
                layout = QtWidgets.QVBoxLayout(dialog)
                
                # Tabla de historial
                table = QtWidgets.QTableWidget()
                table.setColumnCount(8)
                table.setHorizontalHeaderLabels(["Fecha", "Usuario", "Procesador", "GPU", "RAM (GB)", "Disco", "Licencia", "IP"])
                table.horizontalHeader().setStretchLastSection(False)
                
                if cambios:
                    table.setRowCount(len(cambios))
                    for i, cambio in enumerate(cambios):
                        # user, processor, GPU, RAM, disk, license_status, ip, date
                        user, processor, gpu, ram, disk, lic, ip, fecha = cambio
                        table.setItem(i, 0, QtWidgets.QTableWidgetItem(fecha or '-'))
                        table.setItem(i, 1, QtWidgets.QTableWidgetItem(user or '-'))
                        table.setItem(i, 2, QtWidgets.QTableWidgetItem(processor or '-'))
                        table.setItem(i, 3, QtWidgets.QTableWidgetItem(gpu or '-'))
                        table.setItem(i, 4, QtWidgets.QTableWidgetItem(str(ram or '-')))
                        table.setItem(i, 5, QtWidgets.QTableWidgetItem(disk or '-'))
                        
                        lic_item = QtWidgets.QTableWidgetItem('Activa' if lic else 'Inactiva')
                        if not lic:
                            lic_item.setForeground(QBrush(QColor("darkred")))
                        table.setItem(i, 6, lic_item)
                        
                        table.setItem(i, 7, QtWidgets.QTableWidgetItem(ip or '-'))
                else:
                    table.setRowCount(1)
                    table.setItem(0, 0, QtWidgets.QTableWidgetItem("No hay cambios registrados para este dispositivo"))
                
                layout.addWidget(table)
                
                # Botón cerrar
                btn_cerrar = QtWidgets.QPushButton("Cerrar")
                btn_cerrar.clicked.connect(dialog.close)
                layout.addWidget(btn_cerrar)
                
                dialog.exec()
    
    def iniciar_escaneo_completo(self):
        """
        Flujo completo:
        1. Escanear red con optimized_block_scanner.py
        2. Poblar DB inicial con IPs/MACs del CSV
        3. Solicitar datos completos a cada cliente
        4. Actualizar tabla
        """
        self.ui.statusbar.showMessage("Paso 1/4: Iniciando escaneo de red...", 0)
        self.ui.btnActualizar.setEnabled(False)
        
        # Detener timer de verificación automática durante escaneo
        if hasattr(self, 'timer_estados') and self.timer_estados:
            self.timer_estados.stop()

        # Si existe ServerManager, delegar todo el flujo a run_full_scan
        if hasattr(self, 'server_mgr') and self.server_mgr:
            def callback_full(callback_progreso=None):
                try:
                    print('\n=== Ejecutando run_full_scan via ServerManager ===')
                    mgr = self.server_mgr
                    if not mgr:
                        return (0, 0, 0, None)
                    inserted, activos, total, csv_path = mgr.run_full_scan(callback_progreso=callback_progreso)
                    return (inserted, activos, total, csv_path)
                except Exception as e:
                    print(f'Exception en run_full_scan wrapper: {e}')
                    import traceback
                    traceback.print_exc()
                    return (0, 0, 0, None)

            # Usar HiloConProgreso para recibir actualizaciones en tiempo real
            self.hilo_escaneo = HiloConProgreso(callback_full)
            self.hilo_escaneo.progreso.connect(self.on_consulta_progreso)
            self.hilo_escaneo.terminado.connect(self.on_full_scan_terminado)
            self.hilo_escaneo.error.connect(self.on_escaneo_error)
            self.hilo_escaneo.start()
            return

        # Fallback: flujo antiguo si no hay ServerManager
        self.ejecutar_escaneo_red()
    
    def ejecutar_escaneo_red(self):
        """Paso 1: Ejecuta optimized_block_scanner.py"""
        def callback_escaneo():
            try:
                print("\n=== Ejecutando escaneo de red (Scanner facade) ===")
                scanner = ls.Scanner()

                # Ejecutar el escaneo; run_scan devuelve la ruta al CSV generado
                csv_path = scanner.run_scan()
                print(f">> Escaneo completado, CSV: {csv_path}")

                # Guardar ruta para uso posterior (poblar DB)
                self._last_csv = csv_path
                return True

            except Exception as e:
                print(f">> Excepción en escaneo: {e}")
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
            self.ui.statusbar.showMessage(">> Paso 1/4: Escaneo completado - Poblando DB inicial...", 0)
            # Paso 2: Poblar DB con CSV
            self.poblar_db_desde_csv()
        else:
            self.ui.statusbar.showMessage("ERROR: Error en escaneo de red", 5000)
            self.ui.btnActualizar.setEnabled(True)
            # Reiniciar timer en caso de error
            if hasattr(self, 'timer_estados') and self.timer_estados:
                self.timer_estados.start(10000)
    
    def on_escaneo_error(self, error):
        """Error en Paso 1"""
        self.ui.statusbar.showMessage(f"ERROR: Error en escaneo: {error}", 5000)
        self.ui.btnActualizar.setEnabled(True)
        # Reiniciar timer en caso de error
        if hasattr(self, 'timer_estados') and self.timer_estados:
            self.timer_estados.start(10000)

    def on_full_scan_terminado(self, resultado):
        """Handler para cuando ServerManager.run_full_scan finaliza.

        Resultado esperado: (inserted, activos, total, csv_path)
        """
        try:
            inserted, activos, total, csv_path = resultado
        except Exception:
            # Si la forma no es la esperada, intentar desempaquetar parcialmente
            try:
                inserted = resultado[0]
                activos = resultado[1] if len(resultado) > 1 else 0
                total = resultado[2] if len(resultado) > 2 else 0
            except Exception:
                inserted = 0; activos = 0; total = 0

        # Actualizar status y recargar vista (equivalente a finalizar_escaneo_completo)
        self.ui.statusbar.showMessage(f">> Paso 4/4: Escaneo finalizado. Insertados: {inserted}. {activos}/{total} clientes respondieron", 5000)
        # Recargar tabla SIN verificar ping (estados ya actualizados por escaneo)
        self.cargar_dispositivos(verificar_ping=False)
        self.ui.btnActualizar.setEnabled(True)
        
        # Reiniciar timer de verificación automática
        if hasattr(self, 'timer_estados') and self.timer_estados:
            self.timer_estados.start(10000)
    
    def poblar_db_desde_csv(self):
        """Paso 2: Lee CSV y crea registros básicos en DB (solo IP/MAC)"""
        def callback_poblar():
            try:
                print("\n=== Poblando DB desde CSV (Scanner.parse_csv_to_db) ===")
                csv_path = getattr(self, '_last_csv', None)
                if csv_path:
                    print(f">> Usando CSV generado por Scanner: {csv_path}")
                else:
                    print(">> Usando CSV por defecto (si existe)")

                scanner = ls.Scanner()
                inserted = scanner.parse_csv_to_db(csv_path)

                print(f"\n>> Resumen poblado DB:")
                print(f"   - Insertados: {inserted}")
                return inserted
            except Exception as e:
                print(f">> Error poblando DB: {e}")
                import traceback
                traceback.print_exc()
                return 0
        
        self.hilo_poblado = Hilo(callback_poblar)
        self.hilo_poblado.terminado.connect(self.on_poblado_terminado)
        self.hilo_poblado.error.connect(self.on_poblado_error)
        self.hilo_poblado.start()

    def on_poblado_terminado(self, insertados):
        """Callback Paso 2 completado"""
        self.ui.statusbar.showMessage(f">> Paso 2/4: DB poblada ({insertados} nuevos) - Anunciando servidor...", 0)
        # Paso 3: Anunciar servidor y esperar conexiones
        self.anunciar_y_esperar_clientes()
    
    def on_poblado_error(self, error):
        """Error en Paso 2"""
        self.ui.statusbar.showMessage(f"ERROR: Error poblando DB: {error}", 5000)
        self.ui.btnActualizar.setEnabled(True)
    
    def anunciar_y_esperar_clientes(self):
        """Paso 3: Consulta cada cliente directamente con actualizaciones en tiempo real (sin broadcasts)"""
        def callback_consulta(callback_progreso=None):
            try:
                print("\n=== Consultando clientes desde lista de IPs ===")
                
                # Consultar dispositivos desde CSV con callback de progreso
                print(">> Consultando dispositivos...")
                # Usar Monitor facade para la consulta y progreso
                try:
                    monitor = ls.Monitor()
                    activos, total = monitor.query_all_from_csv(None, callback_progreso)
                except Exception:
                    activos, total = ls.consultar_dispositivos_desde_csv(callback_progreso=callback_progreso)
                
                print(f">> Consulta completada: {activos}/{total} dispositivos respondieron")
                return (activos, total)
                
            except Exception as e:
                print(f">> Error en consulta: {e}")
                import traceback
                traceback.print_exc()
                return (0, 0)
        
        # Usar HiloConProgreso para recibir actualizaciones en tiempo real
        self.hilo_consulta = HiloConProgreso(callback_consulta)
        self.hilo_consulta.progreso.connect(self.on_consulta_progreso)
        self.hilo_consulta.terminado.connect(self.on_consulta_terminada)
        self.hilo_consulta.error.connect(self.on_consulta_error)
        self.hilo_consulta.start()
    
    def on_consulta_terminada(self, resultado):
        """Callback Paso 3 completado"""
        activos, total = resultado
        self.ui.statusbar.showMessage(f">> Paso 3/4: {activos}/{total} clientes respondieron - Actualizando vista...", 0)
        # Paso 4: Recargar tabla
        self.finalizar_escaneo_completo()
    
    def on_consulta_error(self, error):
        """Error en Paso 3"""
        self.ui.statusbar.showMessage(f"ERROR: Error consultando clientes: {error}", 5000)
        self.ui.btnActualizar.setEnabled(True)
    
    def finalizar_escaneo_completo(self):
        """Paso 4: Recargar tabla con datos actualizados"""
        print("\n=== Finalizando escaneo completo ===")
        # Cargar dispositivos SIN verificar ping (ya se verificó en consultar_dispositivos_desde_csv)
        self.cargar_dispositivos(verificar_ping=False)
        self.ui.statusbar.showMessage(">> Escaneo completo finalizado exitosamente", 5000)
        self.ui.btnActualizar.setEnabled(True)
        print(">> Proceso completado\n")
        
        # Reiniciar timer de verificación automática
        if hasattr(self, 'timer_estados') and self.timer_estados:
            self.timer_estados.start(10000)



app = QtWidgets.QApplication.instance()
if app is None:
    app = QtWidgets.QApplication(sys.argv)

window = InventarioWindow()
window.show()
sys.exit(app.exec())