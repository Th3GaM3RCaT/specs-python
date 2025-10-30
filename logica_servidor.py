from glob import glob
from json import JSONDecodeError, dump, load, loads, dumps
from socket import AF_INET, SO_BROADCAST, SOCK_DGRAM, SOCK_STREAM, SOL_SOCKET, socket
from sys import argv
from threading import Thread
from datetime import datetime
import csv
import re

from PySide6.QtWidgets import QApplication
from logica_Hilo import Hilo
from sql_specs import consultas_sql as sql

import socket as sckt
HOST = sckt.gethostbyname(sckt.gethostname())
PORT = 5255

app = QApplication.instance()
if app is None:
    app = QApplication(argv)
    
    
    
# tengo un array de archivos json y tengo que migrarlo a la DB cambiando consultar_informacion y abrir_json para que usen la DB en vez de los archivos
archivos_json = glob("*.json")
clientes = []


def parsear_datos_dispositivo(json_data):
    """
    Parsea los datos recibidos del cliente y extrae la información para la tabla Dispositivos.
    
    Retorna una tupla con los campos:
    (serial, DTI, user, MAC, model, processor, GPU, RAM, disk, license_status, ip, activo)
    """
    # Extraer datos del JSON
    serial = json_data.get("SerialNumber", "")
    dti = None  # DTI no viene en el JSON, se asigna manualmente o se calcula
    user = json_data.get("Name", "")
    mac = json_data.get("MAC Address", "")
    model = json_data.get("Model", "")
    license_status = "con licencia" in json_data.get("License status", "").lower()
    ip = json_data.get("client_ip", "")
    activo = True  # Si envía datos, está activo
    
    # Parsear datos de DirectX si existe
    processor = ""
    gpu = ""
    disk = ""
    
    dxdiag_txt = json_data.get("dxdiag_output_txt", "")
    if dxdiag_txt:
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
        
        # (Dispositivos_serial, modulo, fabricante, capacidad, velocidad, numero_serie, actual, fecha_instalacion)
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
    """Recibe información del cliente y la almacena en la base de datos."""
    print(f"conectando por {addr}")
    buffer = b""
    
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            buffer += data
            
            # Intentar decodificar y parsear cuando tengamos datos completos
            try:
                json_data = loads(buffer.decode("utf-8"))
                
                # Validar que tenga campos mínimos
                if "SerialNumber" not in json_data or "MAC Address" not in json_data:
                    print("JSON incompleto - faltan campos requeridos")
                    break
                
                print(f"Procesando datos del dispositivo: {json_data.get('SerialNumber')}")
                
                # Parsear datos para tabla Dispositivos
                datos_dispositivo = parsear_datos_dispositivo(json_data)
                
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
                print(f"✓ Datos del dispositivo {serial} guardados exitosamente")
                
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
        print(f"desconectado: {addr}")


def main():
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"servidor escuchando en puerto {HOST}: {PORT}")
    while True:
        conn, addr = server_socket.accept()
        clientes.append(conn)
        hilo = Thread(target=consultar_informacion, args=(conn, addr))
        hilo.start()


def anunciar_ip():
    global clientes
    broadcast = socket(AF_INET, SOCK_DGRAM)
    broadcast.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    broadcast.sendto(b"servidor specs", ("255.255.255.255", 37020))


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
        # Buscar el CSV más reciente
        csvs = glob("optimized_scan_*.csv")
        if not csvs:
            print("No se encontraron archivos CSV de escaneo")
            return []
        archivo_csv = max(csvs)  # El más reciente por nombre
        print(f"Usando archivo CSV: {archivo_csv}")
    
    ips_macs = []
    try:
        with open(archivo_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ip = row.get('ip', '').strip()
                mac = row.get('mac', '').strip()
                
                # Validar IP
                if ip and mac and '.' in ip:
                    # Filtrar IPs incompletas o inválidas
                    partes = ip.split('.')
                    if len(partes) == 4 and all(p.isdigit() for p in partes):
                        ips_macs.append((ip, mac))
        
        print(f"Cargadas {len(ips_macs)} IPs desde {archivo_csv}")
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
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
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


def consultar_dispositivos_desde_csv(archivo_csv=None, callback_progreso=None):
    """
    Consulta todos los dispositivos del CSV y solicita sus datos.
    
    Args:
        archivo_csv: Ruta al CSV. Si es None, usa el más reciente.
        callback_progreso: Función callback(ip, total, current) para reportar progreso
    
    Returns:
        Tupla (activos, total)
    """
    ips_macs = cargar_ips_desde_csv(archivo_csv)
    total = len(ips_macs)
    activos = 0
    
    print(f"\n=== Consultando {total} dispositivos ===")
    
    for i, (ip, mac) in enumerate(ips_macs, 1):
        if callback_progreso:
            callback_progreso(ip, total, i)
        
        print(f"[{i}/{total}] Consultando {ip} ({mac})...")
        
        if solicitar_datos_a_cliente(ip):
            activos += 1
            # Actualizar estado en DB si existe el dispositivo
            try:
                # Buscar dispositivo por MAC
                sql_query, params = sql.abrir_consulta("Dispositivos-select.sql", {"MAC": mac})
                sql.cursor.execute(sql_query, params)
                dispositivo = sql.cursor.fetchone()
                
                if dispositivo:
                    serial = dispositivo[0]
                    sql.setActive((serial, True, datetime.now().isoformat()))
                    sql.connection.commit()
            except Exception as e:
                print(f"    Error actualizando estado: {e}")
        else:
            # Marcar como inactivo si existe
            try:
                sql_query, params = sql.abrir_consulta("Dispositivos-select.sql", {"MAC": mac})
                sql.cursor.execute(sql_query, params)
                dispositivo = sql.cursor.fetchone()
                
                if dispositivo:
                    serial = dispositivo[0]
                    sql.setActive((serial, False, datetime.now().isoformat()))
                    sql.connection.commit()
            except:
                pass
    
    print(f"\n=== Consulta finalizada: {activos}/{total} dispositivos activos ===\n")
    return activos, total


def buscar_dispositivo():
    """Inicia el servidor y anuncia presencia para que clientes se conecten."""
    hilo = Hilo(anunciar_ip)
    hilo.start()


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
    
    # Anunciar servidor para que clientes se conecten
    anunciar_ip()
    
    # Consultar dispositivos
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
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    
                    esta_activo = ping_result.returncode == 0
                    
                    # Actualizar estado en DB
                    sql.setActive((serial, esta_activo, datetime.now().isoformat()))
                    
                    if esta_activo:
                        activos += 1
                        print(f"  ✓ {ip} ({serial}): Activo")
                    else:
                        print(f"  ✗ {ip} ({serial}): Inactivo")
                    
                except Exception as e:
                    print(f"  ⚠ {ip} ({serial}): Error - {e}")
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
            time.sleep(60)  # Esperar 1 minuto antes de reintentar


# compilar usando:
# pyinstaller --onedir --noconsole servidor.py --add-data "sql_specs/statement*.sql;sql_specs/statement"