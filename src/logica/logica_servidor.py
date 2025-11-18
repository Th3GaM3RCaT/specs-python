from glob import glob
from json import JSONDecodeError, dump, load, loads, dumps
from socket import AF_INET, SOCK_STREAM, SOL_SOCKET, socket
from sys import argv
from threading import Thread, Event
from pathlib import Path
from datetime import datetime
import csv
import re
import asyncio

from PySide6.QtWidgets import QApplication
from logica.logica_Hilo import Hilo
from sql import ejecutar_sql as sql
from logica import optimized_block_scanner as scan
from logica.ping_utils import ping_host
from logica.async_utils import run_async

# Importar configuración de seguridad
from typing import Callable, Optional

# Declarar como variables opcionales que pueden ser None o funciones
verify_auth_token: Optional[Callable] = None  # type: ignore[assignment]
is_ip_allowed: Optional[Callable] = None  # type: ignore[assignment]
sanitize_field: Optional[Callable] = None  # type: ignore[assignment]

try:
    import sys
    from pathlib import Path
    # Agregar directorio config al path
    config_dir = Path(__file__).parent.parent.parent / "config"
    sys.path.insert(0, str(config_dir))
    
    from security_config import (  # type: ignore[import]
        verify_auth_token, is_ip_allowed, sanitize_field,
        MAX_BUFFER_SIZE, CONNECTION_TIMEOUT, MAX_CONNECTIONS_PER_IP
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

import socket as sckt
# Obtener IP local
LOCAL_IP = sckt.gethostbyname(sckt.gethostname())
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

# Almacenamiento de archivos JSON legacy (deprecado, SQLite es fuente de verdad)
archivos_json = glob("*.json")
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
            server_socket = socket(AF_INET, SOCK_STREAM)
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            print(f"[ServerManager] Servidor TCP escuchando en {self.host}:{self.port}")

            # Loop de aceptación (bloqueante)
            while True:
                conn, addr = server_socket.accept()
                clientes.append(conn)
                hilo = Thread(target=consultar_informacion, args=(conn, addr), daemon=True)
                hilo.start()
        except Exception as e:
            print(f"[ServerManager] Error al iniciar servidor TCP: {e}")
            raise

    def run_full_scan(self, start: int = 100, end: int = 119, use_broadcast_probe: bool = True, callback_progreso=None):
        """Ejecuta el flujo completo de escaneo → poblar DB → consultar.

        Args:
            start,end: parámetros para el scanner (bloque de subnets)
            use_broadcast_probe: pasar al scanner si corresponde
            callback_progreso: función opcional que será llamada con diccionarios
                de progreso durante el escaneo Y la consulta de dispositivos.

        Retorna:
            Tupla (inserted, activos, total, csv_path)
        """
        inserted = 0
        activos = 0
        total = 0
        csv_path = None

        try:
            # Paso 1: escanear red (con progreso)
            scanner = Scanner()
            csv_path = scanner.run_scan(callback_progreso=callback_progreso)

            # Paso 2: poblar DB desde CSV
            inserted = scanner.parse_csv_to_db(csv_path)

            # Paso 3: consultar dispositivos desde CSV (Monitor) usando callback_progreso
            monitor = Monitor()
            activos, total = monitor.query_all_from_csv(csv_path, callback_progreso)

        except Exception as e:
            print(f"[ServerManager] Error en run_full_scan: {e}")
            import traceback
            traceback.print_exc()

        return (inserted, activos, total, csv_path)


class Monitor:
    """Encapsula funciones de verificación/consulta de dispositivos.

    Implementa métodos ligeros que reutilizan las funciones async ya existentes
    (consultar_dispositivos_desde_csv). La UI puede instanciar esta clase y pasar callbacks.
    """
    def __init__(self, ping_batch_size: Optional[int] = None):
        self.ping_batch_size = ping_batch_size

    def query_all_from_csv(self, archivo_csv: Optional[str] = None, callback_progreso=None):
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
        scan.main(callback_progreso=callback_progreso)
        # Determinar CSV generado
        project_root = Path(__file__).parent.parent.parent
        output_dir = project_root / 'output'
        csv_path = output_dir / 'discovered_devices.csv'
        if csv_path.exists():
            return str(csv_path)

        # Buscar en raíz
        csv_root = project_root / 'discovered_devices.csv'
        if csv_root.exists():
            return str(csv_root)
        print("[Scanner] discovered_devices.csv no encontrado después del escaneo")
        raise FileNotFoundError('discovered_devices.csv no encontrado después del escaneo')

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
                    cur.execute("SELECT serial, MAC FROM Dispositivos WHERE ip = ?", (ip,))
                    existe = cur.fetchone()

                    if not existe:
                        serial = f"TEMP_{mac.replace(':','').replace('-','')}" if mac else f"TEMP_{ip.replace('.','')}"
                        datos_basicos = ( serial, "", "", mac, "Pendiente escaneo", "", "", 0, "", False, ip, False,)
                        sql.setDevice(datos_basicos, conn=conn)  # Pasar conexión thread-safe
                        inserted += 1
                    else:
                        serial_existente = existe[0]
                        mac_existente = existe[1]
                        if mac and not mac_existente:
                            cur.execute("UPDATE Dispositivos SET ip = ?, MAC = ? WHERE serial = ?", (ip, mac, serial_existente))
                            updated += 1
                        else:
                            cur.execute("UPDATE Dispositivos SET ip = ? WHERE serial = ?", (ip, serial_existente))
                            updated += 1
                except Exception as e:
                    print(f"[parse_csv_to_db] Error poblando DB para IP={ip}, MAC={mac}: {e}")
                    skipped += 1

            conn.commit()
            conn.close()
            
            print(f"[parse_csv_to_db] Resultados: {inserted} insertados, {updated} actualizados, {skipped} errores")
            
        except Exception as e:
            print(f"[parse_csv_to_db] Error con conexión DB: {e}")
            import traceback
            traceback.print_exc()

        return inserted

    def run_scan_con_rangos(self, start_ip, end_ip, callback_progreso=None):
        """Ejecuta el escaneo con rangos específicos de IP."""
        # Importar el módulo del escáner
        import logica.optimized_block_scanner as scan
        
        # Simular argumentos para el escáner (ya que usa argparse)
        # Necesitas modificar optimized_block_scanner.py para aceptar rangos directamente
        # Por ahora, puedes llamar scan.main() con argumentos simulados
        import sys
        from io import StringIO
        
        # Guardar sys.argv original
        original_argv = sys.argv
        
        # Simular argumentos para --ranges
        sys.argv = ['optimized_block_scanner.py', '--ranges', f'{start_ip}-{end_ip}']
        print(f"[Scanner] Ejecutando escaneo para rangos {start_ip} - {end_ip}")
        try:
            # Capturar salida si es necesario, o modificar scan.main para devolver resultados
            scan.main(callback_progreso=callback_progreso)
            # Determinar CSV generado (igual que en run_scan)
            # ...
            return "Escaneo completado"  # O devolver el CSV path
        finally:
            sys.argv = original_argv  # Restaurar

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
            dxdiag_txt = dxdiag_txt[:1024 * 100]
        
        # Buscar Processor
        proc_match = re.search(r"Processor:\s*(.+)", dxdiag_txt)
        if proc_match:
            processor = proc_match.group(1).strip()
        
        # Buscar GPU (Card name)
        gpu_match = re.search(r"Card name:\s*(.+)", dxdiag_txt)
        if gpu_match:
            gpu = gpu_match.group(1).strip()
        
        # Buscar información de disco (Drive, Model, Total Space)
        drive_match = re.search(r"Drive:\s*(\w+):", dxdiag_txt)
        model_match = re.search(r"Model:\s*(.+)", dxdiag_txt)
        space_match = re.search(r"Total Space:\s*([\d.]+\s*[A-Z]+)", dxdiag_txt)
        
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
                match = re.search(r"([\d.]+)\s*GB", str(value))
                if match:
                    ram_gb = int(float(match.group(1)))
                    break
    
    return (serial, dti, user, mac, model, processor, gpu, int(ram_gb), disk, license_status, ip, activo)


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
        modulos.append((
            serial,
            etiqueta,
            fabricante,
            int(capacidad) if capacidad else 0,
            int(velocidad) if velocidad else 0,
            numero_serie,
            True,  # actual
            datetime.now().isoformat()
        ))
        
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
            size_match = re.search(r"([\d.]+)\s*([A-Z]+)", total_size)
            capacidad_gb = 0
            if size_match:
                num = float(size_match.group(1))
                unit = size_match.group(2)
                if unit == "TB":
                    capacidad_gb = int(num * 1024)
                elif unit == "GB":
                    capacidad_gb = int(num)
            
            # (Dispositivos_serial, nombre, capacidad, tipo, actual, fecha_instalacion)
            discos.append((
                serial,
                device,
                capacidad_gb,
                fstype,
                True,  # actual
                datetime.now().isoformat()
            ))
    
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
            aplicaciones.append((
                serial,
                nombre,
                version,
                publisher
            ))
    
    return aplicaciones


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
            print(f"[SECURITY] Demasiadas conexiones desde {client_ip} ({current_connections})")
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
                print(f"[SECURITY] Buffer excedido desde {client_ip} ({len(buffer)} bytes)")
                break
            
            # Intentar decodificar y parsear cuando tengamos datos completos
            try:
                json_data = loads(buffer.decode("utf-8"))
                
                # SECURITY: Validar autenticación
                if SECURITY_ENABLED:
                    token = json_data.get("auth_token")
                    if not token:
                        print(f"[SECURITY] Token de autenticacion faltante desde {client_ip}")
                        break
                    
                    if not verify_auth_token(token):
                        print(f"[SECURITY] Token de autenticacion invalido desde {client_ip}")
                        break
                    
                    print(f"[OK] Token valido desde {client_ip}")
                
                # Validar que tenga campos mínimos
                if "SerialNumber" not in json_data or "MAC Address" not in json_data:
                    print("JSON incompleto - faltan campos requeridos")
                    break
                
                print(f"Procesando datos del dispositivo: {json_data.get('SerialNumber')}")
                
                # Parsear datos para tabla Dispositivos
                datos_dispositivo = parsear_datos_dispositivo(json_data)
                serial = datos_dispositivo[0]
                mac = datos_dispositivo[3]
                ip = datos_dispositivo[10]
                
                # Si el serial viene vacío del cliente, generar uno temporal basado en MAC
                if not serial or serial.strip() == "":
                    if mac:
                        serial = f"TEMP_{mac.replace(':', '').replace('-', '')}"
                        print(f"[WARN] Cliente sin serial, usando temporal: {serial}")
                    else:
                        serial = "TEMP_UNKNOWN"
                        print("[WARN] Cliente sin serial ni MAC, usando TEMP_UNKNOWN")
                    # Actualizar tupla con el serial temporal
                    datos_dispositivo = (serial,) + datos_dispositivo[1:]
                
                # Si el serial NO es temporal y hay MAC, verificar si existe dispositivo para actualizar
                elif not serial.startswith("TEMP"):
                    dispositivo_existente = None
                    
                    # 1. Buscar por MAC si existe
                    if mac:
                        # Buscar serial temporal basado en MAC
                        if sql.actualizar_serial_temporal(serial, mac):
                            print(f"[OK] Serial temporal (por MAC) actualizado a {serial}")
                            dispositivo_existente = serial
                        else:
                            # Buscar cualquier dispositivo con esa MAC
                            sql.cursor.execute("SELECT serial FROM Dispositivos WHERE MAC = ?", (mac,))
                            resultado = sql.cursor.fetchone()
                            if resultado:
                                dispositivo_existente = resultado[0]
                                print(f"[INFO] Dispositivo encontrado por MAC: {dispositivo_existente}")
                    
                    # 2. Si no encontró por MAC, buscar por IP
                    if not dispositivo_existente and ip:
                        sql.cursor.execute("SELECT serial, MAC FROM Dispositivos WHERE ip = ?", (ip,))
                        resultado = sql.cursor.fetchone()
                        if resultado:
                            serial_anterior = resultado[0]
                            mac_anterior = resultado[1]
                            
                            # Si el dispositivo no tenía MAC, actualizarlo
                            if not mac_anterior or mac_anterior.strip() == "":
                                print(f"[UPDATE] Dispositivo encontrado por IP sin MAC: {serial_anterior}")
                                print(f"[UPDATE] Actualizando de {serial_anterior} a {serial} y agregando MAC {mac}")
                                
                                # Actualizar serial en todas las tablas
                                sql.cursor.execute("UPDATE Dispositivos SET serial = ? WHERE serial = ?", 
                                             (serial, serial_anterior))
                                sql.cursor.execute("UPDATE activo SET Dispositivos_serial = ? WHERE Dispositivos_serial = ?",
                                             (serial, serial_anterior))
                                sql.cursor.execute("UPDATE registro_cambios SET Dispositivos_serial = ? WHERE Dispositivos_serial = ?",
                                             (serial, serial_anterior))
                                sql.cursor.execute("UPDATE almacenamiento SET Dispositivos_serial = ? WHERE Dispositivos_serial = ?",
                                             (serial, serial_anterior))
                                sql.cursor.execute("UPDATE memoria SET Dispositivos_serial = ? WHERE Dispositivos_serial = ?",
                                             (serial, serial_anterior))
                                sql.cursor.execute("UPDATE aplicaciones SET Dispositivos_serial = ? WHERE Dispositivos_serial = ?",
                                             (serial, serial_anterior))
                                sql.cursor.execute("UPDATE informacion_diagnostico SET Dispositivos_serial = ? WHERE Dispositivos_serial = ?",
                                             (serial, serial_anterior))
                                sql.connection.commit()
                                
                                dispositivo_existente = serial
                
                # Insertar/actualizar dispositivo
                sql.setDevice(datos_dispositivo)
                print(f"Dispositivo {datos_dispositivo[0]} guardado en DB")
                
                # Actualizar estado activo
                serial = datos_dispositivo[0]
                sql.setActive((serial, True, datetime.now().isoformat()))
                
                # Guardar módulos RAM
                modulos_ram = parsear_modulos_ram(json_data)
                for i, modulo in enumerate(modulos_ram, 1):
                    sql.setMemoria(modulo, i)
                print(f"Guardados {len(modulos_ram)} módulos de RAM")
                
                # Guardar almacenamiento
                discos = parsear_almacenamiento(json_data)
                for i, disco in enumerate(discos, 1):
                    sql.setAlmacenamiento(disco, i)
                print(f"Guardados {len(discos)} dispositivos de almacenamiento")
                
                # Guardar aplicaciones
                aplicaciones = parsear_aplicaciones(json_data)
                for app in aplicaciones:
                    try:
                        sql.setaplication(app)
                    except:
                        pass  # Algunas apps pueden dar error, continuar
                print(f"Guardadas {len(aplicaciones)} aplicaciones")
                
                # Guardar informe diagnóstico completo
                dxdiag_txt = json_data.get("dxdiag_output_txt", "")
                json_str = dumps(json_data, indent=2)
                sql.setInformeDiagnostico((
                    serial,
                    json_str,
                    dxdiag_txt,
                    datetime.now().isoformat()
                ))
                
                # Commit cambios
                sql.connection.commit()
                print(f"[OK] Datos del dispositivo {serial} guardados exitosamente")
                
                # Opcional: guardar backup en JSON para debug
                try:
                    with open(f"{datos_dispositivo[2]}_{datos_dispositivo[3]}.json", "w", encoding="utf-8") as f:
                        dump(json_data, f, indent=4)
                except:
                    pass
                
                break
                
            except JSONDecodeError:
                # JSON incompleto, seguir recibiendo
                continue
            except Exception as e:
                print(f"Error procesando datos: {e}")
                import traceback
                traceback.print_exc()
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
            hilo = Thread(target=consultar_informacion, args=(conn, addr))
            hilo.start()
    except KeyboardInterrupt:
        print("\n[OK] Servidor detenido por usuario")
        server_socket.close()
    except Exception as e:
        print(f"[ERROR] Error en servidor: {e}")
        server_socket.close()


# FUNCIONES DE BROADCAST ELIMINADAS
# El servidor ahora solicita datos directamente a los clientes vía TCP
# sin usar broadcasts/discovery UDP


def abrir_json(position=0):
    if archivos_json:
        nombre_archivo = archivos_json[position]
        try:
            # Abre y lee el archivo JSON
            with open(nombre_archivo, "r", encoding="utf-8") as f:
                # Carga el contenido JSON en una estructura de Python
                datos = load(f)
                return datos
        except FileNotFoundError:
            print(f"Error: El archivo {nombre_archivo} no se encontró.")
        except JSONDecodeError:
            print(f"Error: El archivo {nombre_archivo} no es un JSON válido.")



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
        
        archivo_csv = max(csvs, key=lambda p: p.stat().st_mtime)  # El más reciente por fecha
        print(f"Usando archivo CSV: {archivo_csv}")
    
    ips_macs = []
    invalidas = 0
    try:
        with open(archivo_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ip = row.get('ip', '').strip()
                mac = row.get('mac', '').strip()
                
                # Validar IP completa
                if ip:
                    # Filtrar IPs incompletas o inválidas
                    partes = ip.split('.')
                    if len(partes) != 4:
                        print(f"   IP descartada (octetos incorrectos): {ip}")
                        invalidas += 1
                        continue
                    
                    # Verificar que sean números y rango válido
                    if all(p.isdigit() and 0 <= int(p) <= 255 for p in partes):
                        #if ':' in mac:  # Validar MAC también
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


def solicitar_datos_a_cliente(ip, timeout_seg=5):
    """
    Solicita datos a un cliente específico por IP.
    
    Args:
        ip: IP del cliente
        timeout_seg: Timeout en segundos
    
    Returns:
        True si el cliente respondió, False si no
    """
    try:
        # Primero hacer ping para verificar si está activo
        import subprocess
        ping_result = subprocess.run(
            ['ping', '-n', '1', '-w', '1000', ip],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if ping_result.returncode != 0:
            print(f"  {ip}: No responde a ping")
            return False
        
        # Enviar broadcast dirigido (el cliente debe estar escuchando puerto 37020)
        # Nota: El cliente debe estar en modo --tarea para responder
        print(f"  {ip}: Activo, solicitando datos...")
        
        # Aquí podríamos implementar un protocolo más sofisticado
        # Por ahora, el servidor anuncia y espera que los clientes se conecten
        
        return True
        
    except Exception as e:
        print(f"  {ip}: Error - {e}")
        return False


async def solicitar_datos_cliente(client_ip, client_port=5256, timeout=30):
    """Solicita especificaciones a un cliente específico mediante GET_SPECS (ASÍNCRONO).
    
    Args:
        client_ip: IP del cliente
        client_port: Puerto del daemon del cliente (default 5256)
        timeout: Timeout TOTAL en segundos (default 30 para dar tiempo a recopilación de datos)
    
    Returns:
        True si se recibieron datos correctamente, False en caso contrario
    """
    import json
    
    try:
        # Conectar de forma asíncrona (timeout 10s para la conexión)
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(client_ip, client_port),
            timeout=10.0
        )
        
        # Enviar comando GET_SPECS
        writer.write(b"GET_SPECS")
        await writer.drain()
        
        # Recibir respuesta con timeout más largo
        # El cliente puede tardar 10-30 segundos en recopilar datos
        buffer = b""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            try:
                # Calcular tiempo restante
                elapsed = asyncio.get_event_loop().time() - start_time
                remaining = timeout - elapsed
                
                if remaining <= 0:
                    break
                
                # Leer con timeout dinámico
                chunk = await asyncio.wait_for(
                    reader.read(4096),
                    timeout=min(remaining, 15.0)  # Máximo 15s por chunk
                )
                
                if not chunk:
                    break
                    
                buffer += chunk
                
                # Si recibimos JSON completo
                if buffer.endswith(b'}'):
                    break
                    
            except asyncio.TimeoutError:
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
        json_data = json.loads(buffer.decode('utf-8'))
        
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
                sql.setDevice_threadsafe(datos_dispositivo, thread_conn)
                print(f"        -> Dispositivo guardado: {datos_dispositivo}")
                
                # Actualizar estado activo
                sql.setActive_threadsafe((serial, True, datetime.now().isoformat()), thread_conn)
                print(f"        -> Estado activo guardado")
                
                # Guardar módulos RAM
                modulos_ram = parsear_modulos_ram(json_data)
                print(f"        -> RAM: {len(modulos_ram)} modulos")
                for i, modulo in enumerate(modulos_ram, 1):
                    sql.setMemoria_threadsafe(modulo, i, thread_conn)
                
                # Guardar almacenamiento
                discos = parsear_almacenamiento(json_data)
                print(f"        -> Almacenamiento: {len(discos)} discos")
                for i, disco in enumerate(discos, 1):
                    sql.setAlmacenamiento_threadsafe(disco, i, thread_conn)
                
                # Guardar aplicaciones
                aplicaciones = parsear_aplicaciones(json_data)
                print(f"        -> Aplicaciones: {len(aplicaciones)} apps")
                for app in aplicaciones:
                    try:
                        sql.setaplication_threadsafe(app, thread_conn)
                    except:
                        pass  # Continuar si alguna falla
                
                # Guardar informe diagnóstico completo
                dxdiag_txt = json_data.get("dxdiag_output_txt", "")
                json_str = dumps(json_data, indent=2)
                sql.setInformeDiagnostico_threadsafe(
                    (serial, json_str, dxdiag_txt, datetime.now().isoformat()),
                    thread_conn
                )
                print(f"        -> Informe diagnostico guardado")
                
                # Commit cambios
                thread_conn.commit()
                print(f"        -> COMMIT exitoso")
                
                print(f"        -> Guardado: {name} | Serial: {serial} | IP: {client_ip}")
                return True
                
            finally:
                # Siempre cerrar la conexión
                thread_conn.close()
            
        except Exception as e:
            print(f"        -> Error guardando datos: {e}")
            return False
        
    except asyncio.TimeoutError:
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
    import asyncio
    
    ips_macs = cargar_ips_desde_csv(archivo_csv)
    total = len(ips_macs)
    
    print(f"\n=== Consultando {total} dispositivos en paralelo ===")
    
    # Crear un diccionario para mapear IP -> índice en la tabla
    ip_to_row = {}
    
    async def ping_y_actualizar_dispositivo(ip, mac, index):
        """Hace ping, y si está activo solicita datos completos (GET_SPECS)"""
        try:
            # Usar utilitario centralizado de ping (timeout 1s)
            activo = await ping_host(ip, 1.0)
            
            serial = None
            
            # Si está activo, solicitar datos completos
            if activo:
                print(f"\n  [{index}/{total}] {ip} ACTIVO - Solicitando datos completos...")
                try:
                    resultado = await solicitar_datos_cliente(ip)
                    if resultado:
                        print(f"  [{index}/{total}] {ip} - [OK] Datos obtenidos y guardados")
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
                    sql_query, params = sql.abrir_consulta("Dispositivos-select.sql", {"MAC": mac})
                else:
                    sql_query = "SELECT * FROM Dispositivos WHERE ip = ?"
                    params = (ip,)
                
                thread_cursor.execute(sql_query, params)
                dispositivo = thread_cursor.fetchone()
                
                if dispositivo:
                    serial = dispositivo[0]
                    # Eliminar estado anterior si existe, luego insertar el nuevo
                    thread_cursor.execute(
                        "DELETE FROM activo WHERE Dispositivos_serial = ?",
                        (serial,)
                    )
                    thread_cursor.execute(
                        "INSERT INTO activo (Dispositivos_serial, powerOn, date) VALUES (?, ?, ?)",
                        (serial, activo, datetime.now().isoformat())
                    )
                    thread_conn.commit()
                
                thread_conn.close()
            except Exception as e:
                pass  # Silenciar errores de DB para no saturar el log
            
            # Emitir progreso en tiempo real
            if callback_progreso:
                callback_progreso({
                    'ip': ip,
                    'mac': mac,
                    'activo': activo,
                    'serial': serial,
                    'index': index,
                    'total': total
                })
            
            status = "ACTIVO" if activo else "Desconectado"
            print(f"  [{index}/{total}] {ip}: {status}")
            
            return activo
            
        except Exception as e:
            # Emitir error también
            if callback_progreso:
                callback_progreso({
                    'ip': ip,
                    'mac': mac,
                    'activo': False,
                    'serial': None,
                    'index': index,
                    'total': total,
                    'error': str(e)
                })
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
            batch = tareas[i:i+batch_size]
            batch_num = i//batch_size + 1
            total_batches = (len(tareas)-1)//batch_size + 1
            print(f"\n>> Procesando lote {batch_num}/{total_batches} ({len(batch)} dispositivos)...")
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            resultados.extend(batch_results)
        
        return resultados
    
    # Ejecutar consulta asíncrona
    resultados = run_async(consultar_todos)
    activos = sum(1 for r in resultados if r is True)
    
    print(f"\n=== Consulta finalizada: {activos}/{total} dispositivos activos ===\n")
    return activos, total


def buscar_dispositivo():
    """DEPRECATED - Función legacy que usaba broadcasts (ya no necesaria)."""
    print("[WARN] buscar_dispositivo() deprecated - broadcasts eliminados")
    pass


def iniciar_escaneo_y_consulta(archivo_csv=None):
    """
    Función principal que ejecuta el escaneo de red y consulta dispositivos.
    Se puede llamar desde la UI.
    """
    # Primero cargar IPs
    ips_macs = cargar_ips_desde_csv(archivo_csv)
    
    if not ips_macs:
        print("No hay IPs para consultar")
        return
    
    # Consultar dispositivos directamente (sin broadcasts)
    consultar_dispositivos_desde_csv(archivo_csv)


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


def monitorear_dispositivos_periodicamente(intervalo_minutos=15, callback_progreso=None):
    """
    Monitorea dispositivos periódicamente para actualizar su estado activo.
    
    Args:
        intervalo_minutos: Intervalo entre consultas en minutos
        callback_progreso: Función callback para reportar progreso
    
    Returns:
        Esta función corre indefinidamente hasta ser interrumpida
    """
    import time
    
    print(f"\n=== Iniciando monitoreo periódico (cada {intervalo_minutos} min) ===\n")
    
    while True:
        try:
            # Obtener dispositivos de la DB
            dispositivos = obtener_dispositivos_db()
            
            if not dispositivos:
                print("No hay dispositivos para monitorear")
                time.sleep(intervalo_minutos * 60)
                continue
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Monitoreando {len(dispositivos)} dispositivos...")
            
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
                    import subprocess
                    ping_result = subprocess.run(
                        ['ping', '-n', '1', '-w', '1000', ip],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    
                    esta_activo = ping_result.returncode == 0
                    
                    # Actualizar estado en DB
                    sql.setActive((serial, esta_activo, datetime.now().isoformat()))
                    
                    if esta_activo:
                        activos += 1
                        print(f"  [OK] {ip} ({serial}): Activo")
                    else:
                        print(f"  [X] {ip} ({serial}): Inactivo")
                    
                except Exception as e:
                    print(f"  {ip} ({serial}): Error - {e}")
                    sql.setActive((serial, False, datetime.now().isoformat()))
            
            # Commit cambios
            sql.connection.commit()
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Monitoreo completado: {activos}/{len(dispositivos)} activos\n")
            
            # Esperar antes de la próxima ronda
            time.sleep(intervalo_minutos * 60)
            
        except KeyboardInterrupt:
            print("\n=== Monitoreo detenido por usuario ===")
            break
        except Exception as e:
            print(f"Error en monitoreo: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(10) 


# compilar usando:
# pyinstaller --onedir --noconsole servidor.py --add-data "sql_specs/statement*.sql;sql_specs/statement"