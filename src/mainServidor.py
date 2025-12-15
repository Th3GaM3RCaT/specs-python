import os
from sys import path, argv
from pathlib import Path
from datetime import datetime

# Agregar la raíz del proyecto al path para importaciones absolutas
project_root = Path(__file__).parent.parent
path.insert(0, str(project_root))

from traceback import print_exc

from PySide6 import QtWidgets, QtCore
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import QMainWindow
from asyncio import set_event_loop, new_event_loop, sleep, gather
from ui.inventario_ui import Ui_MainWindow  # Importar el .ui convertido
from sql.ejecutar_sql import (
    cursor,
    connection,
    abrir_consulta,
    setDevice,
)  # Funciones de DB
import sql.ejecutar_sql as sql_mod
from logica import logica_servidor as ls  # Importar lógica del servidor
from logica.logica_Hilo import Hilo, HiloConProgreso  # Para operaciones en background

# Utilitario compartido de ping asíncrono (evitar duplicación)
from logica.ping_utils import ping_host
from logica.logica_Hilo import HiloConProgreso

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
    if estado == "encendido":
        item.setText("Encendido")
        item.setBackground(QBrush(QColor(COLOR_ENCENDIDO)))
    elif estado == "apagado":
        item.setText("Apagado")
        item.setBackground(QBrush(QColor(COLOR_APAGADO)))
    elif estado == "sin_ip":
        item.setText("[?]")
        item.setBackground(QBrush(QColor(COLOR_SIN_IP)))
    elif estado == "verificando":
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
            self_ip = tuple(int(part) for part in self.text().split("."))
            other_ip = tuple(int(part) for part in other.text().split("."))
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
        qss_path = self.property("qss_file")
        if qss_path:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            qss_path = os.path.join(base_dir, qss_path)
            with open(qss_path, "r") as f:
                self.setStyleSheet(f.read())
       

        # Hilos para operaciones de red
        self.hilo_servidor = None
        self.hilo_escaneo = None
        self.hilo_escaneo_rangos = None        
        self.hilo_consulta = None
        self.hilo_procesamiento = None
        self.procesamiento_en_curso = False
        self.consulta_en_curso = False  # Flag para evitar consultas simultáneas
        self._last_csv = None

        # Facade server manager (puede ser None si no se pudo instanciar)
        self.server_mgr = None

        # Mapa de IP a fila de tabla para actualización en tiempo real
        self.ip_to_row = {}
        self.serials_encontrados = []

        # Conectar señales
        self.ui.tableDispositivos.itemSelectionChanged.connect(
            self.on_dispositivo_seleccionado
        )
        self.ui.lineEditBuscar.textChanged.connect(self.filtrar_dispositivos)
        self.ui.comboBoxFiltro.currentTextChanged.connect(self.aplicar_filtro)
        self.ui.btnActualizar.clicked.connect(self.iniciar_escaneo_completo)
        self.ui.scan_button.clicked.connect(self.iniciar_escaneo_con_rangos)

        # Botones de acciones
        self.ui.btnVerDiagnostico.clicked.connect(self.ver_diagnostico)
        self.ui.btnVerAplicaciones.clicked.connect(self.ver_aplicaciones)
        self.ui.btnVerAlmacenamiento.clicked.connect(self.ver_almacenamiento)
        self.ui.btnVerMemoria.clicked.connect(self.ver_memoria)
        self.ui.btnVerHistorialCambios.clicked.connect(self.ver_historial)

        # Botones de exportación
        self.ui.actionExportarExcel.triggered.connect(self.exportar_xlsx)
        self.ui.actionExportarCSV.triggered.connect(self.exportar_csv)
        
        # Acciones del menú
        self.ui.actionSalir.triggered.connect(self.salir_aplicacion)
        self.ui.actionVerEstadisticas.triggered.connect(self.ver_estadisticas)
        self.ui.actionVerReportes.triggered.connect(self.ver_reportes)
        self.ui.actionConfiguracion.triggered.connect(self.abrir_configuracion)
        self.ui.actionBackupBD.triggered.connect(self.hacer_backup)
        self.ui.actionAcercaDe.triggered.connect(self.acerca_de)
        self.ui.actionManual.triggered.connect(self.abrir_manual)
        self.ui.actiondetener.triggered.connect(self.detener_servidor)
        
        # Botón de escaneo inicial (opcional)
        btn_escanear = getattr(self.ui, "btnEscanear", None)
        if btn_escanear:
            btn_escanear.clicked.connect(self.iniciar_escaneo_completo)
        self.configurar_tabla()

        # Deshabilitar botones hasta seleccionar dispositivo
        self.deshabilitar_botones_detalle()

        # Cargar datos iniciales y verificar si hay datos
        self.cargar_datos_iniciales()

        # Iniciar servidor en segundo plano
        self.iniciar_servidor()

        # Timer para verificación automática de estados cada 20 segundos
        self.timer_estados = QtCore.QTimer(self)
        self.timer_estados.timeout.connect(self.verificar_estados_automatico)
        self.timer_estados.start(20000)  # 20 segundos

        # Timer para consulta diaria de datos de clientes (cada 24 horas)
        self.timer_consulta_diaria = QtCore.QTimer(self)
        self.timer_consulta_diaria.timeout.connect(self.consulta_diaria_clientes)
        self.timer_consulta_diaria.start(86400000)  # 86400000 ms = 24 horas

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
                self.ui.statusbar.showMessage(
                    ">> DB vacía - Iniciando escaneo automático...", 0
                )
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
        self.hilo_servidor.error.connect(self.on_servidor_error)
        self.hilo_servidor.start()
        self.ui.statusbar.showMessage(
            ">> Servidor iniciado - Esperando conexiones de clientes", 3000
        )
        print("Servidor TCP iniciado en puerto 5255")

    def configurar_tabla(self):
        """Configura el ancho de columnas y otros ajustes de la tabla"""
        header = self.ui.tableDispositivos.horizontalHeader()

        # Ajustar ancho de columnas
        self.ui.tableDispositivos.setColumnWidth(0, 80)  # Estado
        self.ui.tableDispositivos.setColumnWidth(1, 60)  # DTI
        self.ui.tableDispositivos.setColumnWidth(2, 90)  # Serial
        self.ui.tableDispositivos.setColumnWidth(3, 120)  # Usuario
        self.ui.tableDispositivos.setColumnWidth(4, 180)  # Modelo
        self.ui.tableDispositivos.setColumnWidth(5, 200)  # Procesador
        self.ui.tableDispositivos.setColumnWidth(6, 80)  # RAM
        self.ui.tableDispositivos.setColumnWidth(7, 150)  # GPU
        self.ui.tableDispositivos.setColumnWidth(8, 85)  # Licencia
        # IP se estira automáticamente

    def cargar_dispositivos(self, verificar_ping=True, filtrar_serials=None):
        """Carga los dispositivos desde la base de datos y opcionalmente verifica estado con ping

        Args:
            verificar_ping (bool): Si False, carga estados desde tabla 'activo' sin hacer ping.
                                   Usar False después de escaneo completo para no sobrescribir estados.
            filtrar_serials (list): Lista de serials a mostrar. Si None, muestra todos.
        """
        # Limpiar tabla
        self.ui.tableDispositivos.setRowCount(0)

        try:
            # Consultar dispositivos desde la DB
            if filtrar_serials:
                placeholders = ",".join("?" * len(filtrar_serials))
                sql_query = (
                    f"SELECT * FROM Dispositivos WHERE serial IN ({placeholders})"
                )
                cursor.execute(sql_query, filtrar_serials)
            else:
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
                (
                    serial,
                    dti,
                    user,
                    mac,
                    model,
                    processor,
                    gpu,
                    ram,
                    disk,
                    license_status,
                    ip,
                    activo,
                ) = dispositivo

                # Guardar mapeo ip -> row
                if ip:
                    self.ip_to_row[ip] = row_position

                # Columna Estado
                estado_item = QtWidgets.QTableWidgetItem()
                if verificar_ping:
                    # Inicialmente "Verificando..." (haremos ping)
                    actualizar_estado_item(estado_item, "verificando")
                else:
                    # Cargar estado desde tabla 'activo' (ya verificado por escaneo completo)
                    try:
                        sql_activo = "SELECT powerOn FROM activo WHERE Dispositivos_serial = ? ORDER BY date DESC LIMIT 1"
                        cursor.execute(sql_activo, (serial,))
                        estado_db = cursor.fetchone()

                        if estado_db:
                            actualizar_estado_item(
                                estado_item, "encendido" if estado_db[0] else "apagado"
                            )
                        else:
                            actualizar_estado_item(estado_item, "sin_ip")
                    except Exception as e:
                        print(f"Error cargando estado para {serial}: {e}")
                        actualizar_estado_item(estado_item, "sin_ip")

                self.ui.tableDispositivos.setItem(row_position, 0, estado_item)

                # Resto de columnas
                self.ui.tableDispositivos.setItem(
                    row_position, 1, QtWidgets.QTableWidgetItem(str(dti or "-"))
                )
                self.ui.tableDispositivos.setItem(
                    row_position, 2, QtWidgets.QTableWidgetItem(serial)
                )
                self.ui.tableDispositivos.setItem(
                    row_position, 3, QtWidgets.QTableWidgetItem(user or "-")
                )
                self.ui.tableDispositivos.setItem(
                    row_position, 4, QtWidgets.QTableWidgetItem(model or "-")
                )
                self.ui.tableDispositivos.setItem(
                    row_position, 5, QtWidgets.QTableWidgetItem(processor or "-")
                )
                self.ui.tableDispositivos.setItem(
                    row_position, 6, QtWidgets.QTableWidgetItem(str(ram or "-"))
                )
                self.ui.tableDispositivos.setItem(
                    row_position, 7, QtWidgets.QTableWidgetItem(gpu or "-")
                )

                # Licencia con color
                lic_item = QtWidgets.QTableWidgetItem(
                    "[OK] Activa" if license_status else "[X] Inactiva"
                )
                if not license_status:
                    lic_item.setForeground(QBrush(QColor("orangered")))
                self.ui.tableDispositivos.setItem(row_position, 8, lic_item)

                # IP con ordenamiento numérico personalizado
                ip_item = IPAddressTableWidgetItem(ip or "-")
                self.ui.tableDispositivos.setItem(row_position, 9, ip_item)

            # Actualizar contador
            self.ui.labelContador.setText(f"Mostrando {len(dispositivos)} dispositivos")

            # Verificar estado de conexión en background SOLO si verificar_ping=True
            if verificar_ping:
                self._verificar_estados_ping(dispositivos, verbose=True)
            else:
                print(
                    f">> Estados cargados desde DB (sin ping) - {len(dispositivos)} dispositivos"
                )

        except Exception as e:
            print(f"Error consultando base de datos: {e}")
            

            print_exc()
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
                    if not ip or ip == "-":
                        return (row, False, "sin_ip")
                    conectado = await ping_host(ip, 0.5)
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
                BATCH_SIZE = 25
                resultados_batch = []
                for i in range (0, len(tareas), BATCH_SIZE):
                    batch = tareas[i:i + BATCH_SIZE]
                    resultados_batch.extend( await gather(*batch, return_exceptions=True))
                    await sleep(0.1)  # Pequeña pausa entre batches
                return resultados_batch 
                # TODO: posible integracion consulta datos

            # Ejecutar verificación asíncrona
            loop = new_event_loop()
            set_event_loop(loop)
            try:
                resultados = loop.run_until_complete(verificar_todos())
                return resultados
            except Exception as e:
                print(f"Error en verificación de estados: {e}")
                loop.close()
                return []
            finally:
                print(">> Verificación de estados finalizada")
                loop.close()

        # Ejecutar en hilo separado
        def callback_estados(resultados):
            print(">> Actualizando estados en UI...")
            # Actualizar UI con resultados (estamos en el thread principal)
            for resultado in resultados:
                if isinstance(resultado, tuple):
                    row, conectado, ip = resultado
                    estado_item = self.ui.tableDispositivos.item(row, 0)

                    if estado_item:
                        if ip == "sin_ip":
                            actualizar_estado_item(estado_item, "sin_ip")
                        elif conectado:
                            actualizar_estado_item(estado_item, "encendido")
                        else:
                            actualizar_estado_item(estado_item, "apagado")

            # Mensaje solo si verbose=True
            if verbose:
                print(f">> Verificación de estados completada")
                # Iniciar consulta de datos de clientes SOLO si no hay una en curso
                try:
                    if not self.consulta_en_curso:
                        self.anunciar_y_esperar_clientes()
                    else:
                        print("[INFO] Consulta omitida - ya hay una en curso")
                except Exception as e:
                    print(f"[WARN] No se pudo iniciar consulta post-ping: {e}")
                
        self.hilo_verificacion = Hilo(verificar_estados)
        self.hilo_verificacion.terminado.connect(callback_estados)
        self.hilo_verificacion.start()

        if verbose:
            print(">> Verificando estado de conexión de dispositivos...")

    def on_consulta_progreso(self, datos):
        """Callback para actualizar estado en tiempo real durante escaneo y consulta de dispositivos"""
        try:
            # Detectar tipo de progreso
            tipo = datos.get("tipo")

            # Progreso del SCANNER (escaneo de red)
            if tipo == "segmento":
                segmento = datos.get("segmento_actual")
                idx = datos.get("segmento_index")
                total_seg = datos.get("segmentos_totales")
                mensaje = datos.get("mensaje", "")
                self.ui.statusbar.showMessage(
                    f"[ESCANEO {idx}/{total_seg}] {mensaje}", 0
                )
                print(f">> {mensaje}")
                return

            elif tipo == "bloque":
                mensaje = datos.get("mensaje", "")
                self.ui.statusbar.showMessage(f"[ESCANEO] {mensaje}", 0)
                return

            elif tipo == "fase":
                fase = datos.get("fase")
                mensaje = datos.get("mensaje", "")
                self.ui.statusbar.showMessage(f"[{fase.upper()}] {mensaje}", 0)
                print(f">> {mensaje}")
                return

            # Progreso de CONSULTA de dispositivos (ping + solicitud de datos)
            ip = datos.get("ip")
            activo = datos.get("activo")
            index = datos.get("index")
            total = datos.get("total")
            serial = datos.get("serial")
            if serial:
                self.serials_encontrados.append(serial)

            # Actualizar barra de estado con progreso de consulta
            if index is not None and total is not None:
                self.ui.statusbar.showMessage(
                    f"[CONSULTA {index}/{total}] Verificando: {ip or '?'}", 0
                )

            # Actualizar tabla si tenemos el mapeo
            if ip and ip in self.ip_to_row:
                row = self.ip_to_row[ip]
                estado_item = self.ui.tableDispositivos.item(row, 0)

                if estado_item:
                    actualizar_estado_item(
                        estado_item, "encendido" if activo else "apagado"
                    )

            # Mostrar progreso en consola (solo cada 10 dispositivos para no saturar)
            if (
                index is not None
                and total is not None
                and (index % 10 == 0 or index == total)
            ):
                print(
                    f">> Consultando dispositivo {index}/{total}: {ip} - {'Encendido' if activo else 'Apagado'}"
                )

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
            self.ui.labelInfoDTIValue.setText("-")
            self.ui.labelInfoMACValue.setText("-")
            self.ui.labelInfoDiscoValue.setText("-")
            return

        # Desempaquetar datos del dispositivo
        # serial, DTI, user, MAC, model, processor, GPU, RAM, disk, license_status, ip, activo
        (
            db_serial,
            dti,
            user,
            mac,
            model,
            processor,
            gpu,
            ram,
            disk,
            license_status,
            ip,
            activo,
        ) = dispositivo

        # Actualizar labels de información
        self.ui.labelInfoSerialValue.setText(serial)
        self.ui.labelInfoDTIValue.setText(str(dti or "-"))
        self.ui.labelInfoMACValue.setText(mac or "-")
        self.ui.labelInfoDiscoValue.setText(disk or "-")

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
            self.ui.textEditUltimoCambio.setPlainText(
                "No hay cambios registrados para este dispositivo."
            )

    def deshabilitar_botones_detalle(self):
        """Deshabilita botones cuando no hay selección"""
        self.ui.btnVerDiagnostico.setEnabled(False)
        self.ui.btnVerAplicaciones.setEnabled(False)
        self.ui.btnVerAlmacenamiento.setEnabled(False)
        self.ui.btnVerMemoria.setEnabled(False)
        self.ui.btnVerHistorialCambios.setEnabled(False)

        # Limpiar info
        self.ui.labelInfoSerialValue.setText("-")
        self.ui.labelInfoDTIValue.setText("-")
        self.ui.labelInfoMACValue.setText("-")
        self.ui.labelInfoDiscoValue.setText("-")
        self.ui.labelUltimoCambioFecha.setText("Fecha: -")
        self.ui.textEditUltimoCambio.setPlainText(
            "Seleccione un dispositivo para ver los cambios..."
        )

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
        visible_count = sum(
            1
            for row in range(self.ui.tableDispositivos.rowCount())
            if not self.ui.tableDispositivos.isRowHidden(row)
        )
        self.ui.labelContador.setText(f"Mostrando {visible_count} dispositivos")

    def aplicar_filtro(self):
        """Aplica filtro basado en el comboBoxFiltro (estado de dispositivos)"""
        filtro = self.ui.comboBoxFiltro.currentText().lower()

        for row in range(self.ui.tableDispositivos.rowCount()):
            estado_item = self.ui.tableDispositivos.item(row, 0)  # Columna Estado
            mostrar = True

            if estado_item:
                estado_texto = estado_item.text().lower()
                if filtro == "encendidos":
                    mostrar = "encendido" in estado_texto
                elif filtro == "apagados":
                    mostrar = "apagado" in estado_texto
                elif filtro == "sin ip":
                    mostrar = "sin ip" in estado_texto or "sin_ip" in estado_texto
                # "todos" muestra todo (mostrar = True)

            self.ui.tableDispositivos.setRowHidden(row, not mostrar)

        # Actualizar contador
        visible_count = sum(
            1
            for row in range(self.ui.tableDispositivos.rowCount())
            if not self.ui.tableDispositivos.isRowHidden(row)
        )
        self.ui.labelContador.setText(f"Mostrando {visible_count} dispositivos")

    def filtrar_por_ips(self, ips_list):
        """Filtra la tabla para mostrar solo dispositivos con IPs en la lista dada"""
        for row in range(self.ui.tableDispositivos.rowCount()):
            ip_item = self.ui.tableDispositivos.item(row, 9)  # Columna IP
            if ip_item:
                ip = ip_item.text()
                mostrar = ip in ips_list
            else:
                mostrar = False
            self.ui.tableDispositivos.setRowHidden(row, not mostrar)

        # Actualizar contador
        visible_count = sum(
            1
            for row in range(self.ui.tableDispositivos.rowCount())
            if not self.ui.tableDispositivos.isRowHidden(row)
        )
        self.ui.labelContador.setText(
            f"Mostrando {visible_count} dispositivos encontrados"
        )

    def procesar_ips_encontradas_async(self, ips_list):
        """Procesa las IPs encontradas en la DB de forma asíncrona para evitar bloquear la UI"""

        # Evitar múltiples procesamientos simultáneos
        if self.procesamiento_en_curso:
            print(">> Ya hay un procesamiento de DB en curso, esperando...")
            return

        self.procesamiento_en_curso = True

        def procesar_en_lotes(ips_list, callback_progreso=None):
            """Procesa las IPs en lotes para mostrar progreso"""
            total = len(ips_list)
            procesadas = 0

            try:
                for i in range(0, total, 10):  # Procesar en lotes de 10
                    lote = ips_list[i:i+10]

                    for ip in lote:
                        # Verificar si ya existe en DB
                        sql, params = abrir_consulta("Dispositivos-select.sql", {"ip": ip})
                        cursor.execute(sql, params)
                        if not cursor.fetchone():
                            # Crear serial temporal único
                            serial_temp = f"TEMP_IP_{ip.replace('.', '_')}"
                            info_basico = (
                                serial_temp, 0, "", "", "", "", "", "", 0, "", ip, 1
                            )
                            setDevice(info_basico)

                        procesadas += 1

                        # Reportar progreso cada 10 IPs
                        if callback_progreso and procesadas % 10 == 0:
                            callback_progreso({
                                'tipo': 'procesamiento_db',
                                'procesadas': procesadas,
                                'total': total,
                                'mensaje': f"Procesando DB: {procesadas}/{total} IPs"
                            })

                    # Pequeña pausa para no bloquear completamente
                    from time import sleep
                    sleep(0.01)

                return total

            except Exception as e:
                print(f"Error procesando lote de IPs: {e}")
                connection.rollback()
                return 0

        # Usar HiloConProgreso para procesar sin bloquear UI
        self.hilo_procesamiento = HiloConProgreso(procesar_en_lotes, ips_list)
        self.hilo_procesamiento.progreso.connect(self.on_procesamiento_progreso)
        self.hilo_procesamiento.terminado.connect(
            lambda resultado: self.on_procesamiento_terminado(resultado, ips_list)
        )
        self.hilo_procesamiento.error.connect(self.on_procesamiento_error)
        self.hilo_procesamiento.start()

        self.ui.statusbar.showMessage("Procesando IPs encontradas en base de datos...", 0)

    def on_procesamiento_progreso(self, datos):
        """Muestra progreso del procesamiento de DB"""
        if datos.get('tipo') == 'procesamiento_db':
            procesadas = datos.get('procesadas', 0)
            total = datos.get('total', 0)
            mensaje = datos.get('mensaje', '')
            self.ui.statusbar.showMessage(mensaje, 0)
            print(f">> {mensaje}")

    def on_procesamiento_terminado(self, resultado, ips_list):
        """Finaliza procesamiento de IPs"""
        self.procesamiento_en_curso = False  # Resetear flag
        
        if resultado > 0:
            print(f">> Procesadas {resultado} IPs en DB")
            self.ui.statusbar.showMessage(f"DB actualizada con {resultado} nuevas IPs", 3000)

            # Recargar tabla con datos actualizados (sin ping para no demorar más)
            self.cargar_dispositivos(verificar_ping=False)

            # Filtrar para mostrar solo las IPs encontradas
            self.filtrar_por_ips(ips_list)
        else:
            self.ui.statusbar.showMessage("Error procesando IPs en DB", 5000)

    def on_procesamiento_error(self, error):
        """Error en procesamiento de DB"""
        self.procesamiento_en_curso = False  # Resetear flag en error también
        
        self.ui.statusbar.showMessage(f"Error procesando DB: {error}", 5000)
        print(f"Error en procesamiento de DB: {error}")

    def ver_diagnostico(self):
        """Abre ventana de diagnóstico completo"""
        selected = self.ui.tableDispositivos.selectedItems()
        if selected:
            serial_item = self.ui.tableDispositivos.item(selected[0].row(), 2)
            if serial_item:
                serial = serial_item.text()

                # Consultar información de diagnóstico
                sql, params = abrir_consulta(
                    "informacion_diagnostico-select.sql",
                    {"Dispositivos_serial": serial},
                )
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
                sql, params = abrir_consulta(
                    "aplicaciones-select.sql", {"Dispositivos_serial": serial}
                )
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
                        table.setItem(
                            i, 0, QtWidgets.QTableWidgetItem(app[1] or "-")
                        )  # name
                        table.setItem(
                            i, 1, QtWidgets.QTableWidgetItem(app[2] or "-")
                        )  # version
                        table.setItem(
                            i, 2, QtWidgets.QTableWidgetItem(app[3] or "-")
                        )  # publisher
                else:
                    table.setRowCount(1)
                    table.setItem(
                        0,
                        0,
                        QtWidgets.QTableWidgetItem("No hay aplicaciones registradas"),
                    )

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
                sql, params = abrir_consulta(
                    "almacenamiento-select.sql", {"Dispositivos_serial": serial}
                )
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
                table.setHorizontalHeaderLabels(
                    ["Unidad", "Tipo", "Capacidad (GB)", "Fecha"]
                )
                table.horizontalHeader().setStretchLastSection(True)

                if discos:
                    table.setRowCount(len(discos))
                    for i, disco in enumerate(discos):
                        # almacenamiento SQL: Dispositivos_serial, nombre, capacidad, tipo, actual, id, fecha_instalacion
                        # Indices:            0,                  1,      2,         3,     4,      5,  6
                        table.setItem(
                            i, 0, QtWidgets.QTableWidgetItem(disco[1] or "-")
                        )  # nombre (unidad)
                        table.setItem(
                            i, 1, QtWidgets.QTableWidgetItem(disco[3] or "-")
                        )  # tipo
                        table.setItem(
                            i, 2, QtWidgets.QTableWidgetItem(str(disco[2] or "-"))
                        )  # capacidad
                        fecha = disco[5][:10] if disco[5] else "-"
                        table.setItem(i, 3, QtWidgets.QTableWidgetItem(fecha))
                else:
                    table.setRowCount(1)
                    table.setItem(
                        0,
                        0,
                        QtWidgets.QTableWidgetItem(
                            "No hay información de almacenamiento"
                        ),
                    )

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
                sql, params = abrir_consulta(
                    "memoria-select.sql", {"Dispositivos_serial": serial}
                )
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
                table.setHorizontalHeaderLabels(
                    [
                        "Módulo",
                        "Fabricante",
                        "Capacidad (GB)",
                        "Velocidad (MHz)",
                        "Número de Serie",
                    ]
                )
                table.horizontalHeader().setStretchLastSection(True)

                if modulos:
                    table.setRowCount(len(modulos))
                    for i, mod in enumerate(modulos):
                        # memoria SQL: Dispositivos_serial, modulo, fabricante, capacidad, velocidad, numero_serie, actual, id, fecha_instalacion
                        # Indices:     0,                  1,      2,          3,          4,         5,             6,      7,  8
                        table.setItem(
                            i, 0, QtWidgets.QTableWidgetItem(mod[1] or "-")
                        )  # modulo
                        table.setItem(
                            i, 1, QtWidgets.QTableWidgetItem(mod[2] or "-")
                        )  # fabricante
                        table.setItem(
                            i, 2, QtWidgets.QTableWidgetItem(str(mod[3] or "-"))
                        )  # capacidad
                        table.setItem(
                            i, 3, QtWidgets.QTableWidgetItem(str(mod[4] or "-"))
                        )  # velocidad
                        table.setItem(
                            i, 4, QtWidgets.QTableWidgetItem(mod[5] or "-")
                        )  # numero_serie
                else:
                    table.setRowCount(1)
                    table.setItem(
                        0,
                        0,
                        QtWidgets.QTableWidgetItem("No hay información de memoria"),
                    )

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
                table.setHorizontalHeaderLabels(
                    [
                        "Fecha",
                        "Usuario",
                        "Procesador",
                        "GPU",
                        "RAM (GB)",
                        "Disco",
                        "Licencia",
                        "IP",
                    ]
                )
                table.horizontalHeader().setStretchLastSection(False)

                if cambios:
                    table.setRowCount(len(cambios))
                    for i, cambio in enumerate(cambios):
                        # user, processor, GPU, RAM, disk, license_status, ip, date
                        user, processor, gpu, ram, disk, lic, ip, fecha = cambio
                        table.setItem(i, 0, QtWidgets.QTableWidgetItem(fecha or "-"))
                        table.setItem(i, 1, QtWidgets.QTableWidgetItem(user or "-"))
                        table.setItem(
                            i, 2, QtWidgets.QTableWidgetItem(processor or "-")
                        )
                        table.setItem(i, 3, QtWidgets.QTableWidgetItem(gpu or "-"))
                        table.setItem(i, 4, QtWidgets.QTableWidgetItem(str(ram or "-")))
                        table.setItem(i, 5, QtWidgets.QTableWidgetItem(disk or "-"))

                        lic_item = QtWidgets.QTableWidgetItem(
                            "Activa" if lic else "Inactiva"
                        )
                        if not lic:
                            lic_item.setForeground(QBrush(QColor("orangered")))
                        table.setItem(i, 6, lic_item)

                        table.setItem(i, 7, QtWidgets.QTableWidgetItem(ip or "-"))
                else:
                    table.setRowCount(1)
                    table.setItem(
                        0,
                        0,
                        QtWidgets.QTableWidgetItem(
                            "No hay cambios registrados para este dispositivo"
                        ),
                    )

                layout.addWidget(table)

                # Botón cerrar
                btn_cerrar = QtWidgets.QPushButton("Cerrar")
                btn_cerrar.clicked.connect(dialog.close)
                layout.addWidget(btn_cerrar)

                dialog.exec()

    def iniciar_escaneo_completo(self):
        """
        Recarga la tabla de dispositivos desde la base de datos.
        El servidor ya no hace escaneos - espera conexiones de clientes.
        """
        self.ui.statusbar.showMessage("Recargando lista de dispositivos...", 0)
        self.ui.btnActualizar.setEnabled(False)

        # Limpiar lista de serials encontrados
        self.serials_encontrados.clear()

        # Detener timer de verificación automática durante la recarga
        if hasattr(self, "timer_estados") and self.timer_estados:
            self.timer_estados.stop()

        # Simplemente recargar la tabla desde DB
        try:
            self.cargar_dispositivos(verificar_ping=False)
            self.ui.statusbar.showMessage("Lista de dispositivos actualizada", 3000)
        except Exception as e:
            self.ui.statusbar.showMessage(f"Error al recargar dispositivos: {e}", 5000)
        finally:
            self.ui.btnActualizar.setEnabled(True)

            # Reiniciar timer de verificación automática
            if hasattr(self, "timer_estados") and self.timer_estados:
                self.timer_estados.start()

    def on_servidor_error(self, error):
        """Error en el hilo del servidor TCP"""
        self.ui.statusbar.showMessage(f"ERROR: Error en servidor TCP: {error}", 5000)
        print(f"[ERROR] Servidor TCP falló: {error}")
        """Error en el hilo del servidor TCP"""
        self.ui.statusbar.showMessage(f"ERROR: Error en servidor TCP: {error}", 5000)
        print(f"[ERROR] Servidor TCP falló: {error}")

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
                inserted = 0
                activos = 0
                total = 0

        # Actualizar status y recargar vista (equivalente a finalizar_escaneo_completo)
        self.ui.statusbar.showMessage(
            f">> Paso 4/4: Escaneo finalizado. Insertados: {inserted}. {activos}/{total} clientes respondieron",
            5000,
        )
        # Recargar tabla SIN verificar ping (estados ya actualizados por escaneo)
        self.cargar_dispositivos(
            verificar_ping=False, filtrar_serials=self.serials_encontrados
        )
        self.ui.btnActualizar.setEnabled(True)

        # Reiniciar timer de verificación automática
        if hasattr(self, "timer_estados") and self.timer_estados:
            self.timer_estados.start(20000)

    def poblar_db_desde_csv(self):
        """Paso 2: Lee CSV y crea registros básicos en DB (solo IP/MAC)"""
        print("\n=== Iniciando poblado de DB desde CSV ===")

        def callback_poblar():
            print(">> Poblando DB...")
            try:
                print("\n=== Poblando DB desde CSV (Scanner.parse_csv_to_db) ===")
                csv_path = getattr(self, "_last_csv", None)
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
                

                print_exc()
                return 0

        self.hilo_poblado = Hilo(callback_poblar)
        self.hilo_poblado.terminado.connect(self.on_poblado_terminado)
        self.hilo_poblado.error.connect(self.on_poblado_error)
        self.hilo_poblado.start()

    def on_poblado_terminado(self, insertados):
        """Callback Paso 2 completado"""
        self.ui.statusbar.showMessage(
            f">> Paso 2/4: DB poblada ({insertados} nuevos) - Anunciando servidor...", 0
        )
        # Paso 3: Anunciar servidor y esperar conexiones
        self.anunciar_y_esperar_clientes()

    def on_poblado_error(self, error):
        """Error en Paso 2"""
        self.ui.statusbar.showMessage(f"ERROR: Error poblando DB: {error}", 5000)
        self.ui.btnActualizar.setEnabled(True)
        
    def consulta_diaria_clientes(self):
        """Ejecuta consulta automática de clientes a las 2 AM diariamente"""
        from datetime import datetime
        
        # Verificar si ya hay una consulta en curso
        if self.consulta_en_curso:
            print("[INFO] Ya hay una consulta en curso, omitiendo consulta diaria")
            return
        
        hora_actual = datetime.now().hour
        
        # Solo ejecutar entre 2 AM y 3 AM (horario de baja carga)
        if hora_actual != 2:
            return  # Esperar al próximo ciclo
        
        print("\n=== Consulta Diaria Automática (2:00 AM) ===")
        print(f">> Iniciando a las {datetime.now().strftime('%H:%M:%S')}")
        
        self.ui.statusbar.showMessage("Ejecutando consulta diaria de clientes...", 0)
        self.anunciar_y_esperar_clientes()

    def anunciar_y_esperar_clientes(self):
        """Paso 3: Consulta cada cliente directamente con actualizaciones en tiempo real (sin broadcasts)"""
        
        # Evitar consultas simultáneas
        if self.consulta_en_curso:
            print("[INFO] Ya hay una consulta en curso - omitiendo")
            return
        
        self.consulta_en_curso = True
        print("[INFO] Iniciando consulta de clientes...")

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
                    activos, total = ls.consultar_dispositivos_desde_csv(
                        callback_progreso=callback_progreso
                    )

                print(
                    f">> Consulta completada: {activos}/{total} dispositivos respondieron"
                )
                return (activos, total)

            except Exception as e:
                print(f">> Error en consulta: {e}")
                

                print_exc()
                return (0, 0)
    def on_consulta_terminada(self, resultado):
        """Callback Paso 3 completado"""
        self.consulta_en_curso = False
        
        activos, total = resultado
        self.ui.statusbar.showMessage(
            f">> Paso 3/4: {activos}/{total} clientes respondieron - Actualizando vista...",
            0,
        )
        # Paso 4: Recargar tabla filtrando solo los encontrados
        self.finalizar_escaneo_completo()
        """Callback Paso 3 completado"""
        activos, total = resultado
        self.ui.statusbar.showMessage(
            f">> Paso 3/4: {activos}/{total} clientes respondieron - Actualizando vista...",
            0,
        )
        # Paso 4: Recargar tabla filtrando solo los encontrados
    def on_consulta_error(self, error):
        """Error en Paso 3"""
        self.consulta_en_curso = False
        
        self.ui.statusbar.showMessage(
            f"ERROR: Error consultando clientes: {error}", 5000
        )
        self.ui.btnActualizar.setEnabled(True)
        self.ui.btnActualizar.setEnabled(True)

    def finalizar_escaneo_completo(self):
        """Paso 4: Recargar tabla con datos actualizados"""
        print("\n=== Finalizando escaneo completo ===")
        self.cargar_dispositivos(
            verificar_ping=False, filtrar_serials=self.serials_encontrados
        )
        self.ui.statusbar.showMessage(
            ">> Escaneo completo finalizado exitosamente", 5000
        )
        self.ui.btnActualizar.setEnabled(True)
        print(">> Proceso completado\n")

        # Reiniciar timer de verificación automática
        if hasattr(self, "timer_estados") and self.timer_estados:
            self.timer_estados.start(10000)

    def iniciar_escaneo_con_rangos(self):
        # Obtener rangos de los campos de entrada
        print("\n=== Iniciando escaneo con rangos personalizados ===")
        start_ip = self.ui.ip_start_input.text().strip()
        end_ip = self.ui.ip_end_input.text().strip()
        print(f">> Rango: {start_ip} - {end_ip}")

        # Crear instancia del scanner
        print(">> Creando instancia de Scanner...")
        scanner = ls.Scanner()
        print(">> Instancia creada.")

        # Usar HiloConProgreso para ejecutar el escaneo sin congelar la UI
        def funcion_escaneo(callback_progreso=None):
            # Aquí pasamos los rangos al scanner
            # Nota: Scanner.run_scan() necesita ser modificado para aceptar rangos (ver paso 3)
            print(">> Ejecutando escaneo con rangos...")
            try:
                return scanner.run_scan_con_rangos(
                    start_ip, end_ip, callback_progreso=callback_progreso
                )
            except Exception as e:
                print(f">> Error en escaneo: {e}")
                

                print_exc()
                return []

        def on_progreso(datos):
            print(f">> Progreso: {datos}")
            # Actualizar UI con progreso (ej: barra de progreso, tabla)
            if "ip" in datos:
                # Ejemplo: Actualizar una tabla o label con el estado de la IP
                print(f"Procesando IP: {datos['ip']} - Activo: {datos['activo']}")
                # Aquí puedes actualizar una QTableWidget o QLabel con el progreso

        def on_terminado(resultado):
            # Manejar resultado final (ej: mostrar mensaje)
            if isinstance(resultado, list):
                num_ips = len(resultado)
                print(
                    f">> Escaneo con rangos completado. Encontradas {num_ips} IPs activas: {resultado[:10]}..."
                )

                if resultado:
                    # Procesar IPs encontradas de forma asíncrona para evitar bloquear UI
                    self.procesar_ips_encontradas_async(resultado)

                else:
                    print("Escaneo Completado", "No se encontraron IPs activas.")
            else:
                print(f">> Escaneo con rangos completado. Resultado: {resultado}")
                print("Escaneo Completado", f"Resultado: {resultado}")

        self.hilo_escaneo_rangos = HiloConProgreso(funcion_escaneo)

        self.hilo_escaneo_rangos.progreso.connect(on_progreso)
        self.hilo_escaneo_rangos.terminado.connect(on_terminado)
        self.hilo_escaneo_rangos.start()
        print(">> Hilo de escaneo iniciado.")

    def exportar_csv(self):
        """Exporta todos los dispositivos de la DB a formato CSV compatible con Excel."""
        try:
            from logica.exportar_datos import exportar_con_estado_actual
            from PySide6.QtWidgets import QMessageBox, QFileDialog
            
            # Preguntar al usuario dónde guardar
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_sugerido = f"inventario_{timestamp}.csv"
            
            ruta_archivo, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar archivo CSV",
                nombre_sugerido,
                "Archivos CSV (*.csv);;Todos los archivos (*.*)"
            )
            
            if not ruta_archivo:
                return  # Usuario canceló
            
            # Exportar usando la conexión de la DB
            self.ui.statusbar.showMessage("Exportando datos a CSV...", 2000)
            
            # Usar la función de exportación con estado actual
            from logica.exportar_datos import exportar_dispositivos_completo
            from sql.ejecutar_sql import connection
            
            # Generar archivo temporal primero
            ruta_temp = exportar_dispositivos_completo(connection, formato="csv", incluir_inactivos=True)
            
            # Mover a la ubicación elegida por el usuario
            import shutil
            shutil.move(ruta_temp, ruta_archivo)
            
            self.ui.statusbar.showMessage(f"Datos exportados exitosamente a: {ruta_archivo}", 5000)
            
            # Mostrar mensaje de confirmación
            QMessageBox.information(
                self,
                "Exportación Exitosa",
                f"Los datos se han exportado correctamente a:\n\n{ruta_archivo}\n\n"
                f"El archivo puede ser abierto directamente en Microsoft Excel."
            )
            
            # Abrir carpeta contenedora
            from pathlib import Path
            import subprocess
            carpeta = Path(ruta_archivo).parent
            subprocess.run(["explorer", str(carpeta)])
            
        except Exception as e:
            print(f"[ERROR] Error al exportar CSV: {e}")
            from traceback import print_exc
            print_exc()
            
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error de Exportación",
                f"No se pudo exportar los datos:\n\n{str(e)}"
            )

    def exportar_xlsx(self):
        """Exporta todos los dispositivos de la DB a formato XLSX (Excel nativo)."""
        try:
            from logica.exportar_datos import exportar_dispositivos_completo
            from PySide6.QtWidgets import QMessageBox, QFileDialog
            from sql.ejecutar_sql import connection
            
            # Verificar que openpyxl esté instalado
            try:
                import openpyxl
            except ImportError:
                QMessageBox.warning(
                    self,
                    "Paquete Faltante",
                    "Para exportar a formato XLSX se requiere el paquete 'openpyxl'.\n\n"
                    "Instálelo ejecutando:\n"
                    "pip install openpyxl\n\n"
                    "Mientras tanto, puede usar la opción 'Exportar a CSV' que no requiere paquetes adicionales."
                )
                return
            
            # Preguntar al usuario dónde guardar
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_sugerido = f"inventario_{timestamp}.xlsx"
            
            ruta_archivo, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar archivo Excel",
                nombre_sugerido,
                "Archivos Excel (*.xlsx);;Todos los archivos (*.*)"
            )
            
            if not ruta_archivo:
                return  # Usuario canceló
            
            # Exportar
            self.ui.statusbar.showMessage("Exportando datos a Excel (XLSX)...", 2000)
            
            # Generar archivo temporal primero
            ruta_temp = exportar_dispositivos_completo(connection, formato="xlsx", incluir_inactivos=True)
            
            # Mover a la ubicación elegida por el usuario
            import shutil
            shutil.move(ruta_temp, ruta_archivo)
            
            self.ui.statusbar.showMessage(f"Datos exportados exitosamente a: {ruta_archivo}", 5000)
            
            # Mostrar mensaje de confirmación
            QMessageBox.information(
                self,
                "Exportación Exitosa",
                f"Los datos se han exportado correctamente a:\n\n{ruta_archivo}\n\n"
                f"El archivo Excel incluye formato enriquecido y está listo para usar."
            )
            
            # Abrir carpeta contenedora
            from pathlib import Path
            import subprocess
            carpeta = Path(ruta_archivo).parent
            subprocess.run(["explorer", str(carpeta)])
            
        except Exception as e:
            print(f"[ERROR] Error al exportar XLSX: {e}")
            from traceback import print_exc
            print_exc()
            
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error de Exportación",
                f"No se pudo exportar los datos:\n\n{str(e)}"
            )

    def salir_aplicacion(self):
        """Cierra la aplicación de forma segura."""
        from PySide6.QtWidgets import QMessageBox
        
        respuesta = QMessageBox.question(
            self,
            "Confirmar Salida",
            "¿Está seguro que desea salir de la aplicación?\n\n" 
            "El servidor TCP se detendrá y no recibirá datos de clientes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            print("[INFO] Cerrando aplicación...")
            self.close()

    def ver_estadisticas(self):
        """Muestra estadísticas del inventario."""
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem
            
            # Consultar estadísticas
            stats = {}
            
            # Total de dispositivos
            cursor.execute("SELECT COUNT(*) FROM Dispositivos")
            stats['total'] = cursor.fetchone()[0]
            
            # Dispositivos activos
            cursor.execute("SELECT COUNT(*) FROM Dispositivos WHERE activo = 1")
            stats['activos'] = cursor.fetchone()[0]
            
            # Dispositivos encendidos (último estado)
            cursor.execute("""
                SELECT COUNT(DISTINCT Dispositivos_serial) 
                FROM activo 
                WHERE powerOn = 1 
                AND (Dispositivos_serial, date) IN (
                    SELECT Dispositivos_serial, MAX(date) 
                    FROM activo 
                    GROUP BY Dispositivos_serial
                )
            """)
            stats['encendidos'] = cursor.fetchone()[0]
            
            # Sin licencia
            cursor.execute("SELECT COUNT(*) FROM Dispositivos WHERE license_status = 0")
            stats['sin_licencia'] = cursor.fetchone()[0]
            
            # RAM promedio
            cursor.execute("SELECT AVG(RAM) FROM Dispositivos WHERE RAM > 0")
            ram_avg = cursor.fetchone()[0]
            stats['ram_promedio'] = round(ram_avg, 2) if ram_avg else 0
            
            # Fabricantes de RAM más comunes
            cursor.execute("""
                SELECT fabricante, COUNT(*) as cant 
                FROM memoria 
                WHERE actual = 1 AND fabricante IS NOT NULL AND fabricante != ''
                GROUP BY fabricante 
                ORDER BY cant DESC 
                LIMIT 3
            """)
            fabricantes = cursor.fetchall()
            
            # Crear diálogo
            dialog = QDialog(self)
            dialog.setWindowTitle("Estadísticas del Inventario")
            dialog.resize(500, 400)
            
            layout = QVBoxLayout(dialog)
            
            # Título
            titulo = QLabel("<h2>Resumen del Inventario</h2>")
            layout.addWidget(titulo)
            
            # Estadísticas generales
            texto_stats = f"""
            <p><b>Total de Dispositivos:</b> {stats['total']}</p>
            <p><b>Dispositivos Activos:</b> {stats['activos']} ({stats['activos']/stats['total']*100:.1f}%)</p>
            <p><b>Encendidos Actualmente:</b> {stats['encendidos']}</p>
            <p><b>Sin Licencia:</b> {stats['sin_licencia']}</p>
            <p><b>RAM Promedio:</b> {stats['ram_promedio']} GB</p>
            """
            
            label_stats = QLabel(texto_stats)
            layout.addWidget(label_stats)
            
            # Fabricantes de RAM
            if fabricantes:
                label_fab = QLabel("<h3>Fabricantes de RAM Más Comunes</h3>")
                layout.addWidget(label_fab)
                
                for fab, cant in fabricantes:
                    label = QLabel(f"• {fab}: {cant} módulos")
                    layout.addWidget(label)
            
            # Botón cerrar
            btn_cerrar = QPushButton("Cerrar")
            btn_cerrar.clicked.connect(dialog.close)
            layout.addWidget(btn_cerrar)
            
            dialog.exec()
            
        except Exception as e:
            print(f"[ERROR] Error mostrando estadísticas: {e}")
            from traceback import print_exc
            print_exc()

    def ver_reportes(self):
        """Genera y muestra reportes del sistema."""
        from PySide6.QtWidgets import QMessageBox
        
        QMessageBox.information(
            self,
            "Reportes",
            "Funcionalidad de reportes en desarrollo.\n\n"
            "Por ahora puede usar las opciones de exportación para generar reportes en Excel."
        )

    def abrir_configuracion(self):
        """Abre el diálogo de configuración."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFormLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Configuración del Servidor")
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Título
        titulo = QLabel("<h2>Configuración</h2>")
        layout.addWidget(titulo)
        
        # Formulario
        form_layout = QFormLayout()
        
        # Puerto del servidor
        puerto_input = QLineEdit("5255")
        puerto_input.setEnabled(False)  # Solo lectura por ahora
        form_layout.addRow("Puerto TCP:", puerto_input)
        
        # Intervalo de verificación
        intervalo_input = QLineEdit("20")
        form_layout.addRow("Intervalo verificación (s):", intervalo_input)
        
        layout.addLayout(form_layout)
        
        # Nota
        nota = QLabel("<i>Nota: Los cambios requieren reiniciar el servidor</i>")
        layout.addWidget(nota)
        
        # Botones
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(dialog.close)
        layout.addWidget(btn_cerrar)
        
        dialog.exec()

    def hacer_backup(self):
        """Realiza un backup de la base de datos."""
        try:
            from PySide6.QtWidgets import QMessageBox, QFileDialog
            import shutil
            from pathlib import Path
            
            # Obtener ruta de la base de datos actual
            if hasattr(sys, "_MEIPASS"):
                db_actual = Path("specs.db")
            else:
                db_actual = Path(__file__).parent.parent.parent / "data" / "specs.db"
            
            if not db_actual.exists():
                QMessageBox.warning(
                    self,
                    "Error de Backup",
                    "No se encontró la base de datos para hacer backup."
                )
                return
            
            # Preguntar dónde guardar el backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_sugerido = f"specs_backup_{timestamp}.db"
            
            ruta_backup, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Backup de Base de Datos",
                nombre_sugerido,
                "Base de Datos SQLite (*.db);;Todos los archivos (*.*)"
            )
            
            if not ruta_backup:
                return  # Usuario canceló
            
            # Cerrar conexión temporalmente para hacer backup seguro
            connection.commit()
            
            # Copiar archivo
            shutil.copy2(db_actual, ruta_backup)
            
            self.ui.statusbar.showMessage(f"Backup guardado: {ruta_backup}", 5000)
            
            QMessageBox.information(
                self,
                "Backup Exitoso",
                f"La base de datos se ha respaldado correctamente en:\n\n{ruta_backup}"
            )
            
        except Exception as e:
            print(f"[ERROR] Error al hacer backup: {e}")
            from traceback import print_exc
            print_exc()
            
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error de Backup",
                f"No se pudo realizar el backup:\n\n{str(e)}"
            )

    def acerca_de(self):
        """Muestra información sobre la aplicación."""
        from PySide6.QtWidgets import QMessageBox
        
        QMessageBox.about(
            self,
            "Acerca de SpecsNet",
            "<h2>SpecsNet - Sistema de Inventario</h2>"
            "<p><b>Versión:</b> 1.0.0</p>"
            "<p><b>Descripción:</b> Sistema de inventario de hardware en red</p>"
            "<p>Arquitectura cliente-servidor TCP con base de datos SQLite</p>"
            "<br>"
            "<p><b>Características:</b></p>"
            "<ul>"
            "<li>Recopilación automática de especificaciones</li>"
            "<li>Monitoreo de estado en tiempo real</li>"
            "<li>Detección de cambios de hardware</li>"
            "<li>Exportación a Excel (CSV/XLSX)</li>"
            "</ul>"
            "<br>"
            "<p><i>© 2025 - Área de Informática</i></p>"
        )

    def abrir_manual(self):
        """Abre el manual de usuario."""
        from PySide6.QtWidgets import QMessageBox
        from pathlib import Path
        import subprocess
        
        # Buscar archivo de documentación
        docs_dir = Path(__file__).parent.parent.parent / "docs"
        readme = docs_dir / "README.md"
        exportacion = docs_dir / "EXPORTACION.md"
        
        if exportacion.exists():
            # Abrir con el editor predeterminado
            try:
                subprocess.run(["notepad", str(exportacion)])
            except:
                QMessageBox.information(
                    self,
                    "Manual",
                    f"Manual de exportación disponible en:\n\n{exportacion}"
                )
        else:
            QMessageBox.information(
                self,
                "Manual",
                "<h3>Guía Rápida de SpecsNet</h3>"
                "<p><b>1. Escaneo de Red:</b> Use 'Iniciar Escaneo' para buscar dispositivos</p>"
                "<p><b>2. Verificación:</b> El sistema verifica automáticamente cada 20s</p>"
                "<p><b>3. Detalles:</b> Seleccione un dispositivo para ver información completa</p>"
                "<p><b>4. Exportación:</b> Use Archivo > Exportar para generar reportes Excel</p>"
                "<br>"
                "<p><i>Para más información, consulte la documentación en docs/</i></p>"
                "<p><i>O revise el repositorio en GitHub:</i></p>"
                "<p><a href=\"https://github.com/Th3GaM3RCaT/SpecsNet\">https://github.com/Th3GaM3RCaT/SpecsNet</a></p>"
            )

    def detener_servidor(self):
        """Detiene el servidor TCP."""
        from PySide6.QtWidgets import QMessageBox
        
        respuesta = QMessageBox.question(
            self,
            "Detener Servidor",
            "¿Desea detener el servidor TCP?\n\n"
            "No se recibirán datos de clientes hasta reiniciar.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            if self.server_mgr:
                try:
                    self.server_mgr.stop_tcp_server()
                    self.ui.statusbar.showMessage("Servidor TCP detenido", 5000)
                    print("[INFO] Servidor TCP detenido por usuario")
                except:
                    pass
            
            QMessageBox.information(
                self,
                "Servidor Detenido",
                "El servidor TCP ha sido detenido.\n\n"
                "Para reiniciarlo, cierre y vuelva a abrir la aplicación."
            )

def main():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(argv)

    window = InventarioWindow()
    window.show()
    import sys
    sys.exit(app.exec())
if __name__ == "__main__":
    main()