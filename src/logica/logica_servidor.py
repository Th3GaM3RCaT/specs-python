from concurrent.futures import thread
from glob import glob
from json import JSONDecodeError, dump, load, loads, dumps
from socket import AF_INET, SOCK_STREAM, socket
import ssl
from sys import argv
from threading import Thread
from pathlib import Path
from datetime import datetime
from csv import DictReader
from re import search
from asyncio import wait_for, open_connection, get_event_loop, TimeoutError


from PySide6.QtWidgets import QApplication
from sql import ejecutar_sql as sql
from logica.ping_utils import ping_host
from logica.async_utils import run_async

# Importar configuración de seguridad
from typing import Callable, Optional

# Declarar como variables opcionales que pueden ser None o funciones
verify_auth_token: Optional[Callable] = None  # type: ignore[assignment]
is_ip_allowed: Optional[Callable] = None  # type: ignore[assignment]
sanitize_field: Optional[Callable] = None  # type: ignore[assignment]

try:
    from sys import path
    from pathlib import Path

    # Agregar directorio config al path
    config_dir = Path(__file__).parent.parent.parent / "config"
    path.insert(0, str(config_dir))

    from security_config import (  # type: ignore[import]
        verify_auth_token,
        is_ip_allowed,
        sanitize_field,
        MAX_BUFFER_SIZE,
        CONNECTION_TIMEOUT,
        MAX_CONNECTIONS_PER_IP,
    )

    SECURITY_ENABLED = True
except ImportError:
    print("[WARN] WARNING: security_config.py no encontrado. Seguridad DESHABILITADA.")
    print("   Crear security_config.py para habilitar autenticacion y rate limiting.")
    SECURITY_ENABLED = False
    MAX_BUFFER_SIZE = 10 * 1024 * 1024
    CONNECTION_TIMEOUT = 30
    MAX_CONNECTIONS_PER_IP = 3

    # Funciones dummy cuando security_config no existe
    def verify_auth_token(token):
        return True  # Aceptar cualquier token

    def is_ip_allowed(ip):
        return True  # Aceptar cualquier IP

    def sanitize_field(value, max_length=1024):
        return str(value)[:max_length] if value else ""


from socket import gethostbyname, gethostname

# Obtener IP local
LOCAL_IP = gethostbyname(gethostname())
# Servidor escucha en la IP local (no en 0.0.0.0 para evitar problemas de firewall)
HOST = LOCAL_IP
# Puerto TCP del servidor (cargar desde .env)
try:
    from config.security_config import SERVER_PORT

    PORT = SERVER_PORT
except ImportError:
    PORT = 5255  # Fallback si no hay security_config

app = QApplication.instance()
if app is None:
    app = QApplication(argv)

# Lista de conexiones activas de clientes
clientes = []
# Contador de conexiones por IP (rate limiting)
connections_per_ip = {}


class ServerManager:
    """Facade para manejar el servidor TCP (sin broadcasts/discovery).

    Esta clase maneja el servidor TCP que recibe datos de clientes.
    Ya NO usa broadcasts UDP - los clientes escuchan en puerto 5256.
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        self.host = host or HOST
        self.port = port or PORT

    def start_tcp_server(self):
        """Inicia el servidor TCP (bloqueante) que recibe datos de clientes.

        Los clientes NO se descubren via broadcast. En su lugar:
        - Servidor tiene lista de IPs (CSV/DB)
        - Servidor solicita datos activamente conectándose a cliente:5256
        """
        try:
            # Cargar configuración TLS
            try:
                from config.security_config import USE_TLS, TLS_CERT_PATH, TLS_KEY_PATH
            except ImportError:
                USE_TLS = True
                TLS_CERT_PATH = "config/server.crt"
                TLS_KEY_PATH = "config/server.key"
            
            server_socket = socket(AF_INET, SOCK_STREAM)
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            
            context = None
            if USE_TLS:
                from pathlib import Path
                cert_path = Path(TLS_CERT_PATH)
                key_path = Path(TLS_KEY_PATH)
                
                if not cert_path.exists():
                    cert_path = Path(__file__).parent.parent.parent / TLS_CERT_PATH
                    key_path = Path(__file__).parent.parent.parent / TLS_KEY_PATH
                
                if not cert_path.exists() or not key_path.exists():
                    print(f"[ERROR] Certificados TLS no encontrados!")
                    print(f"  Certificado: {cert_path}")
                    print(f"  Clave: {key_path}")
                    print(f"  Ejecuta: python config/generar_certificado.py")
                    print(f"  O desactiva TLS con USE_TLS=false en .env")
                    return
                
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.load_cert_chain(str(cert_path), str(key_path))
                print(f"[ServerManager] Servidor TCP+TLS escuchando en {self.host}:{self.port}")
            else:
                print(f"[ServerManager] Servidor TCP escuchando en {self.host}:{self.port}")
                print(f"[WARN] TLS DESACTIVADO - conexiones sin cifrar")

            # Loop de aceptación (bloqueante)
            while True:
                conn, addr = server_socket.accept()
                
                if USE_TLS and context:
                    try:
                        conn_ssl = context.wrap_socket(conn, server_side=True)
                        clientes.append(conn_ssl)
                        hilo = Thread(target=consultar_informacion, args=(conn_ssl, addr), daemon=True)
                        hilo.start()
                    except ssl.SSLError as e:
                        print(f"[ERROR] SSL desde {addr[0]}: {e}")
                        conn.close()
                else:
                    clientes.append(conn)
                    hilo = Thread(target=consultar_informacion, args=(conn, addr), daemon=True)
                    hilo.start()
        except Exception as e:
            print(f"[ServerManager] Error al iniciar servidor TCP: {e}")
            raise

class Monitor:
    """Encapsula funciones de verificación/consulta de dispositivos.

    Implementa métodos ligeros que reutilizan las funciones async ya existentes
    (consultar_dispositivos_desde_csv). La UI puede instanciar esta clase y pasar callbacks.
    """

    def __init__(self, ping_batch_size: Optional[int] = None):
        self.ping_batch_size = ping_batch_size

    def query_all_from_csv(
        self, archivo_csv: Optional[str] = None, callback_progreso=None
    ):
        """Consulta todos los dispositivos listados en el CSV y retorna (activos, total).

        Simple wrapper alrededor de `consultar_dispositivos_desde_csv`.
        """
        return consultar_dispositivos_desde_csv(archivo_csv, callback_progreso)


class Scanner:
    """Responsable de ejecutar el escaneo de red y poblar DB desde CSV."""

    print(">> Creando instancia de Scanner...")

    def run_scan(self, callback_progreso=None):
        """Ejecuta el escaneo externo y devuelve la ruta al CSV generado.

        Args:
            callback_progreso: Función opcional que recibe diccionarios con progreso del escaneo.

        Nota: esta función importa el escaneo y asume que genera
        `discovered_devices.csv` en la raíz o en `output/`.
        """
        print("=== Iniciando escaneo de red ===")
        #scan.main(callback_progreso=callback_progreso)
        # Determinar CSV generado
        project_root = Path(__file__).parent.parent.parent
        output_dir = project_root / "output"
        csv_path = output_dir / "discovered_devices.csv"
        if csv_path.exists():
            return str(csv_path)

        # Buscar en raíz
        csv_root = project_root / "discovered_devices.csv"
        if csv_root.exists():
            return str(csv_root)
        print("[Scanner] discovered_devices.csv no encontrado después del escaneo")
        raise FileNotFoundError(
            "discovered_devices.csv no encontrado después del escaneo"
        )

    def parse_csv_to_db(self, csv_path: Optional[str]):
        """Pobla la base de datos con entradas mínimas desde el CSV (IP/MAC).

        Implementación mínima: si existe una función en `sql` para insertar, usarla.
        """
        # Obtener lista de IPs desde CSV
        ips = cargar_ips_desde_csv(csv_path)
        if not ips:
            print("[parse_csv_to_db] No se cargaron IPs desde CSV")
            return 0

        print(f"[parse_csv_to_db] Procesando {len(ips)} IPs desde CSV...")
        inserted = 0
        updated = 0
        skipped = 0

        # Usar conexión thread-safe para esta operación
        try:
            conn = sql.get_thread_safe_connection()
            cur = conn.cursor()

            for ip, mac in ips:
                try:
                    cur.execute(
                        "SELECT serial, MAC FROM Dispositivos WHERE ip = ?", (ip,)
                    )
                    existe = cur.fetchone()

                    if not existe:
                        serial = (
                            f"TEMP_{mac.replace(':','').replace('-','')}"
                            if mac
                            else f"TEMP_{ip.replace('.','')}"
                        )
                        datos_basicos = (
                            serial,
                            "",
                            "",
                            mac,
                            "Pendiente escaneo",
                            "",
                            "",
                            0,
                            "",
                            False,
                            ip,
                            False,
                        )
                        sql.setDevice(
                            datos_basicos, conn
                        )  # Pasar conexión thread-safe
                        inserted += 1
                    else:
                        serial_existente = existe[0]
                        mac_existente = existe[1]
                        if mac and not mac_existente:
                            cur.execute(
                                "UPDATE Dispositivos SET ip = ?, MAC = ? WHERE serial = ?",
                                (ip, mac, serial_existente),
                            )
                            updated += 1
                        else:
                            cur.execute(
                                "UPDATE Dispositivos SET ip = ? WHERE serial = ?",
                                (ip, serial_existente),
                            )
                            updated += 1
                except Exception as e:
                    print(
                        f"[parse_csv_to_db] Error poblando DB para IP={ip}, MAC={mac}: {e}"
                    )
                    skipped += 1

            conn.commit()
            conn.close()

            print(
                f"[parse_csv_to_db] Resultados: {inserted} insertados, {updated} actualizados, {skipped} errores"
            )

        except Exception as e:
            print(f"[parse_csv_to_db] Error con conexión DB: {e}")
            from traceback import print_exc

            print_exc()

        return inserted

    def run_scan_con_rangos(self, start_ip, end_ip, callback_progreso=None):
        """Ejecuta el escaneo con rangos específicos de IP."""
        # Importar el módulo del escáner
        from . import optimized_block_scanner as scan

        # Construir lista de rangos en formato esperado
        rango = f"{start_ip}-{end_ip}"
        print(f"[Scanner] Ejecutando escaneo para rangos {rango}")
        
        try:
            # Llamar a main pasando los rangos directamente
            print("[Scanner] Llamando a scan.main...")
            alive = scan.main(callback_progreso=callback_progreso, ranges=[rango])
            print(f"[Scanner] Escaneo completado, alive: {len(alive) if alive else 0}")
            return alive  # Devolver la lista de IPs vivas
        except Exception as e:
            print(f"[Scanner] Error durante escaneo: {e}")
            from traceback import print_exc
            print_exc()
            return []


def parsear_datos_dispositivo(json_data):
    """
    Parsea los datos recibidos del cliente y extrae la información para la tabla Dispositivos.

    Retorna una tupla con los campos:
    (serial, DTI, user, MAC, model, processor, GPU, RAM, disk, license_status, ip, activo)

    Security:
        - Sanitiza todos los campos de texto para prevenir inyecciones
        - Limita longitud de campos a MAX_FIELD_LENGTH
    """
    # Extraer datos del JSON con sanitización
    serial = sanitize_field(json_data.get("SerialNumber", ""))
    dti = None  # DTI no viene en el JSON, se asigna manualmente o se calcula
    user = sanitize_field(json_data.get("Name", ""))
    mac = sanitize_field(json_data.get("MAC Address", ""))
    model = sanitize_field(json_data.get("Model", ""))
    license_status = "con licencia" in json_data.get("License status", "").lower()
    ip = sanitize_field(json_data.get("client_ip", ""))
    activo = True  # Si envía datos, está activo

    # Parsear datos de DirectX si existe
    processor = ""
    gpu = ""
    disk = ""

    dxdiag_txt = json_data.get("dxdiag_output_txt", "")
    if dxdiag_txt:
        # SECURITY: Limitar tamaño del campo dxdiag (puede ser MB de texto)
        if len(dxdiag_txt) > 1024 * 100:  # Máximo 100 KB
            print(f"[WARN] dxdiag_output_txt truncado ({len(dxdiag_txt)} bytes)")
            dxdiag_txt = dxdiag_txt[: 1024 * 100]

        # Buscar Processor
        proc_match = search(r"Processor:\s*(.+)", dxdiag_txt)
        if proc_match:
            processor = proc_match.group(1).strip()

        # Buscar GPU (Card name)
        gpu_match = search(r"Card name:\s*(.+)", dxdiag_txt)
        if gpu_match:
            gpu = gpu_match.group(1).strip()

        # Buscar información de disco (Drive, Model, Total Space)
        drive_match = search(r"Drive:\s*(\w+):", dxdiag_txt)
        model_match = search(r"Model:\s*(.+)", dxdiag_txt)
        space_match = search(r"Total Space:\s*([\d.]+\s*[A-Z]+)", dxdiag_txt)

        disk_parts = []
        if drive_match:
            disk_parts.append(f"Drive {drive_match.group(1)}")
        if model_match:
            disk_parts.append(model_match.group(1).strip())
        if space_match:
            disk_parts.append(space_match.group(1).strip())
        disk = " - ".join(disk_parts) if disk_parts else ""

    # Si no hay datos de DirectX, intentar sacar del JSON
    if not processor:
        # Buscar en claves del JSON que contengan "Processor" o similar
        for key, value in json_data.items():
            if "processor" in key.lower() or "cpu" in key.lower():
                processor = str(value)
                break

    # Extraer RAM (total en GB)
    ram_gb = 0
    for key, value in json_data.items():
        if "--- Módulo RAM" in key:
            # Contar módulos
            capacidad_key = "Capacidad_GB"
            if capacidad_key in json_data:
                try:
                    ram_gb += float(json_data[capacidad_key])
                except:
                    pass

    # Si no se encontró por módulos, buscar "Total virtual memory" o similar
    if ram_gb == 0:
        for key, value in json_data.items():
            if "total virtual memory" in key.lower() or "total memory" in key.lower():
                # Extraer número
                match = search(r"([\d.]+)\s*GB", str(value))
                if match:
                    ram_gb = int(float(match.group(1)))
                    break

    return (
        serial,
        dti,
        user,
        mac,
        model,
        processor,
        gpu,
        int(ram_gb),
        disk,
        license_status,
        ip,
        activo,
    )


def parsear_modulos_ram(json_data):
    """
    Extrae información de los módulos RAM del JSON.
    Retorna lista de tuplas para insertar en tabla memoria.
    """
    modulos = []
    serial = json_data.get("SerialNumber", "")

    i = 1
    while True:
        key_prefix = f"--- Módulo RAM {i} ---"
        if key_prefix not in json_data:
            break

        # Buscar datos del módulo
        fabricante = json_data.get("Fabricante", "")
        numero_serie = json_data.get("Número_de_Serie", "")
        capacidad = json_data.get("Capacidad_GB", 0)
        velocidad = json_data.get("Velocidad_MHz", 0)
        etiqueta = json_data.get("Etiqueta", f"Módulo {i}")

        # Schema memoria: (Dispositivos_serial, modulo, fabricante, capacidad, velocidad, numero_serie, actual, fecha_instalacion)
        modulos.append(
            (
                serial,
                etiqueta,
                fabricante,
                int(capacidad) if capacidad else 0,
                int(velocidad) if velocidad else 0,
                numero_serie,
                True,  # actual
                datetime.now().isoformat(),
            )
        )

        i += 1

    return modulos


def parsear_almacenamiento(json_data):
    """
    Extrae información de almacenamiento del JSON.
    Retorna lista de tuplas para insertar en tabla almacenamiento.
    """
    discos = []
    serial = json_data.get("SerialNumber", "")

    # Buscar información en el JSON
    for key, value in json_data.items():
        if "Device" in key and ":" in str(value):
            # Encontrado un dispositivo
            device = str(value).strip()
            total_size = json_data.get("  Total Size", "0GB")
            fstype = json_data.get("  File system type", "")

            # Parsear tamaño
            size_match = search(r"([\d.]+)\s*([A-Z]+)", total_size)
            capacidad_gb = 0
            if size_match:
                num = float(size_match.group(1))
                unit = size_match.group(2)
                if unit == "TB":
                    capacidad_gb = int(num * 1024)
                elif unit == "GB":
                    capacidad_gb = int(num)

            # (Dispositivos_serial, nombre, capacidad, tipo, actual, fecha_instalacion)
            discos.append(
                (
                    serial,
                    device,
                    capacidad_gb,
                    fstype,
                    True,  # actual
                    datetime.now().isoformat(),
                )
            )

    return discos


def parsear_aplicaciones(json_data):
    """
    Extrae aplicaciones instaladas del JSON.
    Retorna lista de tuplas para insertar en tabla aplicaciones.
    """
    aplicaciones = []
    serial = json_data.get("SerialNumber", "")

    # Las aplicaciones están como {nombre: (version, publisher)}
    for key, value in json_data.items():
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            nombre = key
            version = value[0] if value[0] else ""
            publisher = value[1] if len(value) > 1 and value[1] else ""

            # (Dispositivos_serial, name, version, publisher)
            aplicaciones.append((serial, nombre, version, publisher))

    return aplicaciones


def detectar_cambios_hardware(serial, json_data, thread_conn):
    """Detecta si el hardware ha cambiado comparando con el estado anterior.

    Args:
        serial (str): Serial del dispositivo
        json_data (dict): Datos nuevos del cliente
        thread_conn (sqlite3.Connection): Conexión thread-safe

    Returns:
        bool: True si hay cambios, False si es igual al estado anterior

    Note:
        - Registra el cambio en registro_cambios si se detectan diferencias
        - Compara: processor, GPU, RAM total, disco total, license_status, ip, usuario
        - Se ejecuta ANTES de actualizar los datos
    """
    from datetime import datetime
    
    cur = thread_conn.cursor()
    
    # Obtener datos actuales del dispositivo
    cur.execute(
        """SELECT processor, GPU, RAM, disk, license_status, ip, user 
           FROM Dispositivos WHERE serial = ?""",
        (serial,)
    )
    datos_actuales = cur.fetchone()
    
    if not datos_actuales:
        # Nuevo dispositivo, no hay cambios previos
        return False
    
    # Extraer datos nuevos del JSON
    processor_nuevo = json_data.get("Processor", "")
    gpu_nuevo = json_data.get("Display Adapter", "")
    ram_nuevo = json_data.get("RAM", "")  # Ej: "16GB"
    disk_nuevo = json_data.get("Total Disk Size", "")  # Ej: "953GB"
    license_nuevo = json_data.get("license_status", False)
    ip_nuevo = json_data.get("client_ip", "")
    user_nuevo = json_data.get("User", "")
    
    # Comparar con datos anteriores
    (processor_ant, gpu_ant, ram_ant, disk_ant, license_ant, ip_ant, user_ant) = datos_actuales
    
    # Detectar cambios (ignorar espacios y mayúsculas)
    cambios = [
        processor_nuevo.strip() != (processor_ant or "").strip(),
        gpu_nuevo.strip() != (gpu_ant or "").strip(),
        ram_nuevo.strip() != (ram_ant or "").strip(),
        disk_nuevo.strip() != (disk_ant or "").strip(),
        license_nuevo != license_ant,
        ip_nuevo != ip_ant,
        user_nuevo != user_ant,
    ]
    
    if any(cambios):
        print(f"[CAMBIO DETECTADO] Dispositivo {serial}:")
        if cambios[0]:
            print(f"  Procesador: {processor_ant} -> {processor_nuevo}")
        if cambios[1]:
            print(f"  GPU: {gpu_ant} -> {gpu_nuevo}")
        if cambios[2]:
            print(f"  RAM: {ram_ant} -> {ram_nuevo}")
        if cambios[3]:
            print(f"  Disco: {disk_ant} -> {disk_nuevo}")
        if cambios[4]:
            print(f"  Licencia: {license_ant} -> {license_nuevo}")
        if cambios[5]:
            print(f"  IP: {ip_ant} -> {ip_nuevo}")
        if cambios[6]:
            print(f"  Usuario: {user_ant} -> {user_nuevo}")
        
        # Registrar el cambio en la BD
        sql.registrar_cambio_hardware(
            serial, user_nuevo, processor_nuevo, gpu_nuevo, ram_nuevo, 
            disk_nuevo, license_nuevo, ip_nuevo, thread_conn
        )
        
        return True
    
    return False


def consultar_informacion(conn, addr):
    """Recibe información del cliente y la almacena en la base de datos.

    Security:
        - Valida IP contra whitelist de subnets permitidas
        - Verifica token de autenticación
        - Limita tamaño de buffer a MAX_BUFFER_SIZE
        - Aplica timeout de CONNECTION_TIMEOUT segundos
    """
    client_ip = addr[0]
    print(f"conectando por {addr}")

    # SECURITY: Rate limiting - verificar conexiones por IP
    if SECURITY_ENABLED:
        global connections_per_ip

        # Validar IP permitida
        if not is_ip_allowed(client_ip):
            print(f"[SECURITY] IP bloqueada (no esta en whitelist): {client_ip}")
            conn.close()
            return

        # Limitar conexiones por IP
        current_connections = connections_per_ip.get(client_ip, 0)
        if current_connections >= MAX_CONNECTIONS_PER_IP:
            print(
                f"[SECURITY] Demasiadas conexiones desde {client_ip} ({current_connections})"
            )
            conn.close()
            return

        connections_per_ip[client_ip] = current_connections + 1

    buffer = b""

    try:
        # SECURITY: Establecer timeout de conexión
        conn.settimeout(CONNECTION_TIMEOUT)

        while True:
            data = conn.recv(4096)
            if not data:
                break

            buffer += data

            # SECURITY: Verificar tamaño de buffer
            if len(buffer) > MAX_BUFFER_SIZE:
                print(
                    f"[SECURITY] Buffer excedido desde {client_ip} ({len(buffer)} bytes)"
                )
                break

            # Intentar decodificar y parsear cuando tengamos datos completos
            try:
                json_data = loads(buffer.decode("utf-8"))
                
                thread_conn = sql.get_thread_safe_connection()
                # SECURITY: Validar autenticación
                if SECURITY_ENABLED:
                    token = json_data.get("auth_token")
                    if not token:
                        print(
                            f"[SECURITY] Token de autenticacion faltante desde {client_ip}"
                        )
                        break

                    if not verify_auth_token(token):
                        print(
                            f"[SECURITY] Token de autenticacion invalido desde {client_ip}"
                        )
                        break

                    print(f"[OK] Token valido desde {client_ip}")

                # Validar que tenga campos mínimos
                if "SerialNumber" not in json_data or "MAC Address" not in json_data:
                    print("JSON incompleto - faltan campos requeridos")
                    break

                print(
                    f"Procesando datos del dispositivo: {json_data.get('SerialNumber')}"
                )

                # Parsear datos para tabla Dispositivos
                datos_dispositivo = parsear_datos_dispositivo(json_data)
                serial_cliente = datos_dispositivo[0]
                mac = datos_dispositivo[3]
                ip = datos_dispositivo[10]

                # SIEMPRE buscar primero si existe un dispositivo con esta IP
                serial_a_usar = serial_cliente
                sql.cursor.execute(
                    "SELECT serial, MAC FROM Dispositivos WHERE ip = ?", (ip,)
                )
                dispositivo_existente = sql.cursor.fetchone()

                if dispositivo_existente:
                    serial_db = dispositivo_existente[0]
                    mac_db = dispositivo_existente[1]
                    
                    print(f"[INFO] Dispositivo encontrado en DB: serial={serial_db}, MAC={mac_db}")
                    
                    # Usar el serial de la DB para actualizar (mantener identidad del registro)
                    serial_a_usar = serial_db
                    
                    # Si el serial del cliente es real (no temporal) y difiere del de la DB, actualizar
                    if serial_cliente and not serial_cliente.startswith("TEMP") and serial_cliente != serial_db:
                        print(f"[UPDATE] Actualizando serial de {serial_db} a {serial_cliente}")
                        
                        # Actualizar serial en todas las tablas relacionadas
                        sql.cursor.execute(
                            "UPDATE Dispositivos SET serial = ? WHERE serial = ?",
                            (serial_cliente, serial_db),
                        )
                        sql.cursor.execute(
                            "UPDATE activo SET Dispositivos_serial = ? WHERE Dispositivos_serial = ?",
                            (serial_cliente, serial_db),
                        )
                        sql.cursor.execute(
                            "UPDATE registro_cambios SET Dispositivos_serial = ? WHERE Dispositivos_serial = ?",
                            (serial_cliente, serial_db),
                        )
                        sql.cursor.execute(
                            "UPDATE almacenamiento SET Dispositivos_serial = ? WHERE Dispositivos_serial = ?",
                            (serial_cliente, serial_db),
                        )
                        sql.cursor.execute(
                            "UPDATE memoria SET Dispositivos_serial = ? WHERE Dispositivos_serial = ?",
                            (serial_cliente, serial_db),
                        )
                        sql.cursor.execute(
                            "UPDATE aplicaciones SET Dispositivos_serial = ? WHERE Dispositivos_serial = ?",
                            (serial_cliente, serial_db),
                        )
                        sql.cursor.execute(
                            "UPDATE informacion_diagnostico SET Dispositivos_serial = ? WHERE Dispositivos_serial = ?",
                            (serial_cliente, serial_db),
                        )
                        sql.connection.commit()
                        
                        # Ahora usar el serial actualizado
                        serial_a_usar = serial_cliente
                else:
                    # No existe dispositivo con esta IP
                    if not serial_cliente or serial_cliente.strip() == "":
                        # Generar serial temporal
                        if mac:
                            serial_a_usar = f"TEMP_{mac.replace(':', '').replace('-', '')}"
                            print(f"[WARN] Cliente sin serial, usando temporal: {serial_a_usar}")
                        else:
                            serial_a_usar = f"TEMP_{ip.replace('.', '')}"
                            print(f"[WARN] Cliente sin serial ni MAC, usando temporal basado en IP: {serial_a_usar}")

                # Reconstruir tupla con el serial correcto
                datos_dispositivo = (serial_a_usar,) + datos_dispositivo[1:]
                
                # Insertar/actualizar dispositivo (UPSERT por serial)
                sql.setDevice(datos_dispositivo, thread_conn)
                print(f"Dispositivo {serial_a_usar} guardado en DB")
                
                # Detectar cambios de hardware vs estado anterior
                detectar_cambios_hardware(serial_a_usar, json_data, thread_conn)

                # Actualizar estado activo
                sql.setActive((serial_a_usar, True, datetime.now().isoformat()), thread_conn)
                # Guardar módulos RAM
                modulos_ram = parsear_modulos_ram(json_data)
                for i, modulo in enumerate(modulos_ram, 1):
                    sql.setMemoria(modulo, i, thread_conn)
                print(f"Guardados {len(modulos_ram)} módulos de RAM")

                # Guardar almacenamiento
                discos = parsear_almacenamiento(json_data)
                for i, disco in enumerate(discos, 1):
                    sql.setAlmacenamiento(disco, i, thread_conn)
                print(f"Guardados {len(discos)} dispositivos de almacenamiento")

                # Guardar aplicaciones
                aplicaciones = parsear_aplicaciones(json_data)
                for app in aplicaciones:
                    try:
                        sql.setaplication(app, thread_conn)
                    except:
                        pass  # Algunas apps pueden dar error, continuar
                print(f"Guardadas {len(aplicaciones)} aplicaciones")

                # Guardar informe diagnóstico completo
                dxdiag_txt = json_data.get("dxdiag_output_txt", "")
                json_str = dumps(json_data, indent=2)
                sql.setInformeDiagnostico(
                    (serial_a_usar, json_str, dxdiag_txt, datetime.now().isoformat()), thread_conn
                )

                # Commit cambios
                thread_conn.commit()
                print(f"[OK] Datos del dispositivo {serial_a_usar} guardados exitosamente")

                # Opcional: guardar backup en JSON para debug
                try:
                    with open(
                        f"{datos_dispositivo[2]}_{datos_dispositivo[3]}.json",
                        "w",
                        encoding="utf-8",
                    ) as f:
                        dump(json_data, f, indent=4)
                except:
                    pass

                break

            except JSONDecodeError:
                # JSON incompleto, seguir recibiendo
                continue
            except Exception as e:
                print(f"Error procesando datos: {e}")
                from traceback import print_exc

                print_exc()
                break

    except ConnectionResetError:
        print(f"Conexión cerrada abruptamente por {addr}")
    except Exception as e:
        print(f"Error en conexión con {addr}: {e}")
    finally:
        print("cerrando conexion")
        conn.close()
        if conn in clientes:
            clientes.remove(conn)

        # SECURITY: Decrementar contador de conexiones
        if SECURITY_ENABLED and client_ip in connections_per_ip:
            connections_per_ip[client_ip] -= 1
            if connections_per_ip[client_ip] <= 0:
                del connections_per_ip[client_ip]

        print(f"desconectado: {addr}")


def main():
    """Inicia el servidor TCP (sin broadcasts/discovery).

    Ejecuta un servidor TCP en puerto 5255 que recibe datos de clientes.
    Ya NO usa broadcasts UDP - el servidor solicita datos activamente.
    """
    # Servidor TCP principal
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"[OK] Servidor TCP escuchando en {HOST}:{PORT}")
    print(f"[OK] Sistema listo - Esperando clientes...\n")

    try:
        while True:
            conn, addr = server_socket.accept()
            clientes.append(conn)
            hilo = Thread(target=consultar_informacion, args=(conn, addr), daemon=True)
            hilo.start()
    except KeyboardInterrupt:
        print("\n[OK] Servidor detenido por usuario")
        server_socket.close()
    except Exception as e:
        print(f"[ERROR] Error en servidor: {e}")
        server_socket.close()

def cargar_ips_desde_csv(archivo_csv=None):
    """
    Carga lista de IPs desde archivo CSV generado por optimized_block_scanner.py

    Args:
        archivo_csv: Ruta al archivo CSV. Si es None, busca el más reciente.

    Returns:
        Lista de tuplas (ip, mac)
    """
    if archivo_csv is None:
        # Buscar el CSV en output/ o en raíz
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent  # Desde src/logica/ a raíz

        # Buscar en output/ primero
        output_dir = project_root / "output"
        csvs = []
        if output_dir.exists():
            csvs = list(output_dir.glob("discovered_devices.csv"))

        # Si no hay en output/, buscar en raíz
        if not csvs:
            csvs = list(project_root.glob("discovered_devices.csv"))

        if not csvs:
            print("No se encontraron archivos CSV de escaneo")
            print(f"  Buscado en: {output_dir}")
            print(f"  Buscado en: {project_root}")
            return []

        archivo_csv = max(
            csvs, key=lambda p: p.stat().st_mtime
        )  # El más reciente por fecha
        print(f"Usando archivo CSV: {archivo_csv}")

    ips_macs = []
    invalidas = 0
    try:
        with open(archivo_csv, "r", encoding="utf-8") as f:
            reader = DictReader(f)
            for row in reader:
                ip = row.get("ip", "").strip()
                mac = row.get("mac", "").strip()

                # Validar IP completa
                if ip:
                    # Filtrar IPs incompletas o inválidas
                    partes = ip.split(".")
                    if len(partes) != 4:
                        print(f"   IP descartada (octetos incorrectos): {ip}")
                        invalidas += 1
                        continue

                    # Verificar que sean números y rango válido
                    if all(p.isdigit() and 0 <= int(p) <= 255 for p in partes):
                        # if ':' in mac:  # Validar MAC también
                        ips_macs.append((ip, mac))

                    else:
                        print(f"  [WARN] IP descartada (formato invalido): {ip}")
                        invalidas += 1

        print(f"[OK] Cargadas {len(ips_macs)} IPs validas desde {archivo_csv}")
        if invalidas > 0:
            print(f"  [WARN] Se descartaron {invalidas} entradas invalidas del CSV")
        return ips_macs
    except Exception as e:
        print(f"Error leyendo CSV: {e}")
        return []

async def solicitar_datos_cliente(client_ip, client_port=5256, timeout=30):
    """Solicita especificaciones a un cliente específico mediante GET_SPECS (ASÍNCRONO).

    Args:
        client_ip: IP del cliente
        client_port: Puerto del daemon del cliente (default 5256)
        timeout: Timeout TOTAL en segundos (default 30 para dar tiempo a recopilación de datos)

    Returns:
        True si se recibieron datos correctamente, False en caso contrario
    """
    from json import loads

    try:
        # Conectar de forma asíncrona (timeout 10s para la conexión)
        reader, writer = await wait_for(
            open_connection(client_ip, client_port), timeout=10.0
        )
        writer.write(b"GET_SPECS")
        await writer.drain()

        # Recibir respuesta con timeout más largo
        # El cliente puede tardar 10-30 segundos en recopilar datos
        buffer = b""
        start_time = get_event_loop().time()

        while True:
            try:
                # Calcular tiempo restante
                elapsed = get_event_loop().time() - start_time
                remaining = timeout - elapsed

                if remaining <= 0:
                    break

                # Leer con timeout dinámico
                chunk = await wait_for(
                    reader.read(4096),
                    timeout=min(remaining, 15.0),  # Máximo 15s por chunk
                )

                if not chunk:
                    break

                buffer += chunk

                # Si recibimos JSON completo
                if buffer.endswith(b"}"):
                    break

            except TimeoutError:
                # Si ya tenemos datos, salir del loop
                if buffer:
                    break
                # Si no tenemos datos, continuar esperando
                continue

        writer.close()
        await writer.wait_closed()

        print(f"        -> Recibidos {len(buffer)} bytes, procesando...")

        if not buffer:
            return False

        # Decodificar JSON
        json_data = loads(buffer.decode("utf-8"))

        # Validar que tenga campos mínimos
        if "SerialNumber" not in json_data or "MAC Address" not in json_data:
            return False

        # Procesar y guardar TODOS los datos usando funciones de ejecutar_sql.py
        try:
            # Crear conexión thread-safe para esta coroutine
            thread_conn = sql.get_thread_safe_connection()

            try:
                # Parsear datos para tabla Dispositivos
                datos_dispositivo = parsear_datos_dispositivo(json_data)
                serial = datos_dispositivo[0]
                mac = datos_dispositivo[3]
                name = datos_dispositivo[2]

                print(f"        -> Parseado: Serial={serial}, MAC={mac}, Name={name}")

                # Si el serial viene vacío, generar uno temporal basado en MAC
                if not serial or serial.strip() == "":
                    if mac:
                        serial = f"TEMP_{mac.replace(':', '').replace('-', '')}"
                    else:
                        serial = "TEMP_UNKNOWN"
                    datos_dispositivo = (serial,) + datos_dispositivo[1:]
                    print(f"        -> Serial temporal generado: {serial}")

                # Limpiar datos anteriores del dispositivo
                sql.limpiar_datos_dispositivo_threadsafe(serial, thread_conn)
                print(f"        -> Datos anteriores limpiados")

                # Insertar/actualizar dispositivo
                sql.setDevice(datos_dispositivo, thread_conn)
                print(f"        -> Dispositivo guardado: {datos_dispositivo}")

                # Actualizar estado activo
                sql.setActive(
                    (serial, True, datetime.now().isoformat()), thread_conn
                )
                print(f"        -> Estado activo guardado")

                # Guardar módulos RAM
                modulos_ram = parsear_modulos_ram(json_data)
                print(f"        -> RAM: {len(modulos_ram)} modulos")
                for i, modulo in enumerate(modulos_ram, 1):
                    sql.setMemoria(modulo, i, thread_conn)

                # Guardar almacenamiento
                discos = parsear_almacenamiento(json_data)
                print(f"        -> Almacenamiento: {len(discos)} discos")
                for i, disco in enumerate(discos, 1):
                    sql.setAlmacenamiento(disco, i, thread_conn)

                # Guardar aplicaciones
                aplicaciones = parsear_aplicaciones(json_data)
                print(f"        -> Aplicaciones: {len(aplicaciones)} apps")
                for app in aplicaciones:
                    try:
                        sql.setaplication(app, thread_conn)
                    except:
                        pass  # Continuar si alguna falla

                # Guardar informe diagnóstico completo
                dxdiag_txt = json_data.get("dxdiag_output_txt", "")
                json_str = dumps(json_data, indent=2)
                sql.setInformeDiagnostico(
                    (serial, json_str, dxdiag_txt, datetime.now().isoformat()),
                    thread_conn,
                )
                print(f"        -> Informe diagnostico guardado")

                # Commit cambios
                thread_conn.commit()
                print(f"        -> COMMIT exitoso")

                print(
                    f"        -> Guardado: {name} | Serial: {serial} | IP: {client_ip}"
                )
                return True

            finally:
                # Siempre cerrar la conexión
                thread_conn.close()

        except Exception as e:
            print(f"        -> Error guardando datos: {e}")
            return False

    except TimeoutError:
        print(f"        -> Timeout conectando a {client_ip}")
        return False
    except Exception as e:
        print(f"        -> Error: {e}")
        return False


def consultar_dispositivos_desde_csv(archivo_csv=None, callback_progreso=None):
    """
    Consulta todos los dispositivos del CSV y solicita sus datos EN PARALELO.
    Emite progreso en tiempo real a través de callback_progreso.

    Args:
        archivo_csv: Ruta al CSV. Si es None, usa el más reciente.
        callback_progreso: Función callback(datos) donde datos={'ip', 'mac', 'activo', 'serial', 'index', 'total'}

    Returns:
        Tupla (activos, total)
    """
    from asyncio import gather

    ips_macs = cargar_ips_desde_csv(archivo_csv)
    total = len(ips_macs)

    print(f"\n=== Consultando {total} dispositivos en paralelo ===")

    # Crear un diccionario para mapear IP -> índice en la tabla
    ip_to_row = {}

    async def ping_y_actualizar_dispositivo(ip, mac, index):
        """Hace ping, y si está activo solicita datos completos"""
        try:
            # Usar utilitario centralizado de ping (timeout 1s)
            activo = await ping_host(ip, 1.0)

            serial = None

            # Si está activo, solicitar datos completos
            if activo:
                print(
                    f"\n  [{index}/{total}] {ip} ACTIVO - Solicitando datos completos..."
                )
                try:
                    resultado = await solicitar_datos_cliente(ip)
                    if resultado:
                        print(
                            f"  [{index}/{total}] {ip} - [OK] Datos obtenidos y guardados"
                        )
                    else:
                        print(f"  [{index}/{total}] {ip} - [WARN] Cliente no respondió")
                except Exception as e:
                    print(f"  [{index}/{total}] {ip} - [ERROR] {e}")

            # Actualizar estado en DB
            try:
                thread_conn = sql.get_thread_safe_connection()
                thread_cursor = thread_conn.cursor()

                # Buscar dispositivo por MAC o IP
                if mac:
                    sql_query, params = sql.abrir_consulta(
                        "Dispositivos-select.sql", {"MAC": mac}
                    )
                else:
                    sql_query = "SELECT * FROM Dispositivos WHERE ip = ?"
                    params = (ip,)

                thread_cursor.execute(sql_query, params)
                dispositivo = thread_cursor.fetchone()

                if dispositivo:
                    serial = dispositivo[0]
                    # Eliminar estado anterior si existe, luego insertar el nuevo
                    thread_cursor.execute(
                        "DELETE FROM activo WHERE Dispositivos_serial = ?", (serial,)
                    )
                    thread_cursor.execute(
                        "INSERT INTO activo (Dispositivos_serial, powerOn, date) VALUES (?, ?, ?)",
                        (serial, activo, datetime.now().isoformat()),
                    )
                    thread_conn.commit()

                thread_conn.close()
            except Exception as e:
                pass  # Silenciar errores de DB para no saturar el log

            # Emitir progreso en tiempo real
            if callback_progreso:
                callback_progreso(
                    {
                        "ip": ip,
                        "mac": mac,
                        "activo": activo,
                        "serial": serial,
                        "index": index,
                        "total": total,
                    }
                )

            status = "ACTIVO" if activo else "Desconectado"
            print(f"  [{index}/{total}] {ip}: {status}")

            return activo

        except Exception as e:
            # Emitir error también
            if callback_progreso:
                callback_progreso(
                    {
                        "ip": ip,
                        "mac": mac,
                        "activo": False,
                        "serial": None,
                        "index": index,
                        "total": total,
                        "error": str(e),
                    }
                )
            return False

    async def consultar_todos():
        # Crear tareas para todos los dispositivos
        tareas = []
        for idx, (ip, mac) in enumerate(ips_macs, 1):
            tareas.append(ping_y_actualizar_dispositivo(ip, mac, idx))

        # Cargar batch_size desde .env
        try:
            from config.security_config import PING_BATCH_SIZE

            batch_size = PING_BATCH_SIZE
        except ImportError:
            batch_size = 50  # Fallback

        # Ejecutar en lotes para no saturar la red
        resultados = []
        for i in range(0, len(tareas), batch_size):
            batch = tareas[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(tareas) - 1) // batch_size + 1
            print(
                f"\n>> Procesando lote {batch_num}/{total_batches} ({len(batch)} dispositivos)..."
            )
            batch_results = await gather(*batch, return_exceptions=True)
            resultados.extend(batch_results)

        return resultados

    # Ejecutar consulta asíncrona
    resultados = run_async(consultar_todos)
    activos = sum(1 for r in resultados if r is True)

    print(f"\n=== Consulta finalizada: {activos}/{total} dispositivos activos ===\n")
    return activos, total

def obtener_dispositivos_db():
    """
    Obtiene todos los dispositivos de la base de datos.

    Returns:
        Lista de tuplas con datos de dispositivos
    """
    try:
        sql_query, params = sql.abrir_consulta("Dispositivos-select.sql")
        sql.cursor.execute(sql_query, params)
        return sql.cursor.fetchall()
    except Exception as e:
        print(f"Error obteniendo dispositivos: {e}")
        return []


def monitorear_dispositivos_periodicamente(
    intervalo_minutos=0.15, callback_progreso=None
):
    """
    Monitorea dispositivos periódicamente para actualizar su estado activo.

    Args:
        intervalo_minutos: Intervalo entre consultas en minutos
        callback_progreso: Función callback para reportar progreso

    Returns:
        Esta función corre indefinidamente hasta ser interrumpida
    """
    from time import sleep

    print(f"\n=== Iniciando monitoreo periódico (cada {intervalo_minutos} min) ===\n")

    while True:
        try:
            # Obtener dispositivos de la DB
            dispositivos = obtener_dispositivos_db()

            if not dispositivos:
                print("No hay dispositivos para monitorear")
                sleep(intervalo_minutos * 60)
                continue

            print(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Monitoreando {len(dispositivos)} dispositivos..."
            )

            activos = 0
            for i, dispositivo in enumerate(dispositivos, 1):
                serial = dispositivo[0]
                ip = dispositivo[10]

                if not ip:
                    continue

                if callback_progreso:
                    callback_progreso(ip, len(dispositivos), i)

                # Hacer ping al dispositivo
                try:
                    from subprocess import run, CREATE_NO_WINDOW
                    thread_conn = sql.get_thread_safe_connection()
                    ping_result = run(
                        ["ping", "-n", "1", "-w", "1000", ip],
                        capture_output=True,
                        creationflags=CREATE_NO_WINDOW,
                    )
                    print(f"  [PING] {ip}: {ping_result.stdout.decode('utf-8').strip()}")

                    esta_activo = ping_result.returncode == 0

                    # Actualizar estado en DB
                    sql.setActive((serial, esta_activo, datetime.now().isoformat()),thread_conn)
                    thread_conn.commit()
                    thread_conn.close()

                    if esta_activo:
                        activos += 1
                        print(f"  [OK] {ip} ({serial}): Activo")
                    else:
                        print(f"  [X] {ip} ({serial}): Inactivo")

                except Exception as e:
                    print(f"  {ip} ({serial}): Error - {e}")
                    thread_conn = sql.get_thread_safe_connection()
                    sql.setActive((serial, False, datetime.now().isoformat()), thread_conn)
                    thread_conn.commit()
                    thread_conn.close()

            # Commit cambios
            sql.connection.commit()

            print(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Monitoreo completado: {activos}/{len(dispositivos)} activos\n"
            )

            # Esperar antes de la próxima ronda
            sleep(intervalo_minutos * 60)

        except KeyboardInterrupt:
            print("\n=== Monitoreo detenido por usuario ===")
            break
        except Exception as e:
            print(f"Error en monitoreo: {e}")
            from traceback import print_exc

            print_exc()
            sleep(10)
