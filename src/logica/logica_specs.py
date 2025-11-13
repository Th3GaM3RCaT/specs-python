# logica_specs.py
from datetime import datetime
from json import dump, dumps, load
from os import environ, name, path
from pathlib import Path
from socket import AF_INET, SOCK_DGRAM, SOCK_STREAM, socket
from subprocess import CREATE_NO_WINDOW, run
import sys

# Imports pesados - cargar lazy (solo cuando se usan)
# psutil, wmi, windows_tools se importan dentro de informe()

# Constantes globales justificadas
nombre_tarea = "informe_de_dispositivo"  # Usado por configurar_tarea()
new = {}  # Diccionario compartido para datos del sistema (patrón establecido)

# Callback opcional para mensajes de estado (usado por GUI)
_status_callback = None

def set_status_callback(callback):
    """Configura callback para mensajes de estado.
    
    Args:
        callback (callable): Función que recibe (mensaje: str) para actualizar UI
        
    Example:
        set_status_callback(lambda msg: statusbar.showMessage(msg))
    """
    global _status_callback
    _status_callback = callback

def _print_status(mensaje):
    """Imprime mensaje y opcionalmente lo envía al callback de UI.
    
    Args:
        mensaje (str): Mensaje a mostrar
    """
    print(mensaje)
    if _status_callback:
        try:
            _status_callback(mensaje)
        except Exception as e:
            print(f"Error en callback de estado: {e}")


def get_size(bytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def informe():
    """Recopila especificaciones completas del sistema (hardware/software).
    
    Recolecta información de:
    - Fabricante, modelo, serial, MAC
    - CPU (cores, frecuencias, uso)
    - RAM (módulos individuales, capacidad)
    - Discos (particiones, uso)
    - Red (interfaces, IPs, MACs)
    - Licencia Windows (estado, expiración)
    - Software instalado (nombre, versión, publisher)
    
    Returns:
        dict: Diccionario con todas las especificaciones (almacenado en global `new`)
    
    Note:
        Modifica el diccionario global `new`. UI debe deshabilitar botón antes de llamar.
    """
    # Lazy imports - cargar solo cuando se ejecuta informe()
    import psutil
    from getmac import get_mac_address as gma
    from windows_tools.installed_software import get_installed_software
    from wmi import WMI
    
    my_system = WMI().Win32_ComputerSystem()[0]

    # Import con fallback para PyInstaller
    try:
        from datos.serialNumber import get_serial
    except ImportError:
        from ..datos.serialNumber import get_serial
    
    new["SerialNumber"] = get_serial()
    new["Manufacturer"] = my_system.Manufacturer
    new["Model"] = my_system.Model
    new["Name"] = my_system.Name
    new["NumberOfProcessors"] = my_system.NumberOfProcessors
    new["SystemType"] = my_system.SystemType
    new["SystemFamily"] = my_system.SystemFamily
    new["MAC Address"] = gma()

    boot_time_timestamp = psutil.boot_time()
    bt = datetime.fromtimestamp(boot_time_timestamp)
    new["Boot Time"] = (
        f" {bt.year}/{bt.month}/{bt.day} {bt.hour}:{bt.minute}:{bt.second}"
    )

    new["Physical cores"] = psutil.cpu_count(logical=False)
    new["Total cores"] = psutil.cpu_count(logical=True)

    cpufreq = psutil.cpu_freq()
    new[f"Max Frequency"] = f" {cpufreq.max:.2f}Mhz"
    new[f"Min Frequency"] = f"{cpufreq.min:.2f}Mhz"
    new[f"Current Frequency"] = f"{cpufreq.current:.2f}Mhz"

    for i, percentage in enumerate(psutil.cpu_percent(percpu=True, interval=1)):
        new[f"Core {i}"] = f"{percentage}%"
    new[f"Total CPU Usage"] = f"{psutil.cpu_percent()}%"

    svmem = psutil.virtual_memory()
    new[f"Total virtual memory"] = f"{get_size(svmem.total)}"
    new[f"Available virtual memory"] = f"{get_size(svmem.available)}"
    new[f"Used virtual memory"] = f" {get_size(svmem.used)}"
    new[f"Percentage virtual memory"] = f" {svmem.percent}%"

    # Import con fallback para PyInstaller
    try:
        from datos.get_ram import get_ram_info
    except ImportError:
        from ..datos.get_ram import get_ram_info

    for i, ram in enumerate(get_ram_info(), 1):
        new[f"--- Módulo RAM {i} ---"] = ""
        for k, v in ram.items():
            new[f"{k}"] = v

    swap = psutil.swap_memory()

    new[f"Total swap memory"] = f" {get_size(swap.total)}"
    new[f"Free swap memory"] = f" {get_size(swap.free)}"
    new[f"Used swap memory"] = f" {get_size(swap.used)}"
    new[f"Percentage swap memory"] = f" {swap.percent}%"

    partitions = psutil.disk_partitions()
    for partition in partitions:
        new["Device"] = f" {partition.device}"
        new["  Mountpoint"] = f" {partition.mountpoint}"
        new["  File system type"] = f" {partition.fstype}"
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
        except PermissionError:
            continue
        new["  Total Size"] = f" {get_size(partition_usage.total)}"
        new["  Used"] = f" {get_size(partition_usage.used)}"
        new["  Free"] = f" {get_size(partition_usage.free)}"
        new["  Percentage"] = f" {partition_usage.percent}%"

    disk_io = psutil.disk_io_counters()
    if disk_io:
        new["Total read"] = f"{get_size(disk_io.read_bytes)}"
        new["Total write"] = f" {get_size(disk_io.write_bytes)}"

    if_addrs = psutil.net_if_addrs()
    for interface_name, interface_addresses in if_addrs.items():
        for address in interface_addresses:
            new["Interface"] = f" {interface_name}"
            if str(address.family) == "AddressFamily.AF_INET":
                new["  IP Address"] = f"{address.address}"
                new["  Netmask"] = f" {address.netmask}"
                new["  Broadcast IP"] = f"{address.broadcast}"
            elif str(address.family) == "AddressFamily.AF_PACKET":
                new["  MAC Address"] = f" {address.address}"
                new["  Netmask"] = f" {address.netmask}"
                new["  Broadcast MAC"] = f" {address.broadcast}"

    net_io = psutil.net_io_counters()
    new["Total Bytes Sent"] = f"{get_size(net_io.bytes_sent)}"
    new["Total Bytes Received"] = f" {get_size(net_io.bytes_recv)}"
    new["License status"] = f"{get_license_status()}"
    new["Expiration time"] = f"{get_license_status(1)}"

    for software in get_installed_software():
        new[software["name"]] = (software["version"], software["publisher"])
    return new


def preparar_datos_completos():
    """Prepara datos completos del sistema incluyendo informe base + DirectX.
    
    Reutiliza lógica de informe() y agrega dxdiag_output.txt si existe.
    Usado tanto por modo daemon (GET_SPECS) como modo manual (enviar_a_servidor).
    
    Returns:
        dict: Diccionario global `new` con todas las especificaciones
    
    Note:
        Modifica el diccionario global `new`.
        Si dxdiag_output.txt no existe, continúa sin error (advertencia en consola).
    """
    # Recopilar especificaciones base
    informe()
    
    # Agregar informe DirectX si existe
    try:
        output_dir = Path(__file__).parent.parent.parent / "output"
        dxdiag_file = output_dir / "dxdiag_output.txt"
        
        if dxdiag_file.exists():
            with open(dxdiag_file, "r", encoding="cp1252") as f:
                new["dxdiag_output_txt"] = f.read()
            _print_status("[OK] Informe DirectX incluido")
        else:
            _print_status("[WARN] No se encontro dxdiag_output.txt")
            _print_status("[INFO] Ejecuta datos/informeDirectX.py para generarlo")
    except Exception as e:
        _print_status(f"[ERROR] Error leyendo DirectX: {e}")
    
    return new


def get_license_status(a=0):
    """Obtiene estado o fecha de expiración de licencia Windows via slmgr.vbs.
    
    Args:
        a (int): 0 para estado de licencia, 1 para fecha de expiración
    
    Returns:
        str: Estado o fecha de licencia, o None si no se encuentra
    
    Raises:
        OSError: Si no se ejecuta en Windows NT
        FileNotFoundError: Si no se encuentra slmgr.vbs
    """
    # Lazy imports
    from locale import getpreferredencoding
    from re import IGNORECASE, search
    
    if name != "nt":
        raise OSError("solo en windows nt")
    type = r""
    line = r""
    if a != 0:
        type = "/xpr"
        line = r"\s*[::]\s*(.+)"
    else:
        type = "/dli"
        line = r"Estado de la licencia\s*[::]\s*(.+)"
    system_root = environ.get("SystemRoot", r"C:\Windows")
    slmgr_path = path.join(system_root, "System32", "slmgr.vbs")
    if not path.exists(slmgr_path):
        raise FileNotFoundError("no se encontró slmgr.vbs")
    cmd = ["cscript", "//NoLogo", slmgr_path, type]
    proc = run(cmd, capture_output=True, creationflags=CREATE_NO_WINDOW)
    raw_bytes = proc.stdout + proc.stderr
    enc = getpreferredencoding(False) or "utf-8"
    raw = raw_bytes.decode(enc, errors="replace")
    match = search(line, raw, IGNORECASE)
    if match:
        return match.group(1).strip()
    else:
        return None

def enviar_a_servidor(server_ip=None):
    """Envía especificaciones al servidor vía TCP (solo modo manual, sin discovery).
    
    Args:
        server_ip (str, optional): IP del servidor. Si es None, lee desde config.
    
    Proceso:
    1. Carga IP del servidor desde config/server_config.json o parámetro
    2. Lee dxdiag_output.txt y lo incluye en el JSON
    3. Detecta IP local del cliente
    4. Genera token de autenticación (si security_config disponible)
    5. Envía JSON completo vía TCP al servidor puerto 5255
    
    Returns:
        None
    
    Raises:
        ConnectionError: Si no se puede conectar al servidor
    
    Note:
        Modifica el diccionario global `new` agregando dxdiag_output_txt y client_ip.
        
        Configuración requerida en config/server_config.json:
        {"server_ip": "192.168.1.100", "server_port": 5255}
    
    Security:
        Genera token de autenticación basado en timestamp y secreto compartido.
    """
    # Importar seguridad si está disponible
    generate_auth_token = None
    security_available = False
    
    try:
        from sys import path
        # Agregar directorio config al path
        config_dir = Path(__file__).parent.parent.parent / "config"
        path.insert(0, str(config_dir))
        
        from security_config import generate_auth_token  # type: ignore[import]
        security_available = True
    except ImportError:
        security_available = False
        _print_status("[WARN] security_config no disponible, enviando sin autenticacion")
    
    # Cargar puerto desde config
    try:
        from config.security_config import SERVER_PORT
        tcp_port = SERVER_PORT
    except ImportError:
        tcp_port = 5255  # Fallback puerto TCP servidor
    
    txt_data = ""
    HOST = server_ip  # Usar IP proporcionada si existe
    
    # Intentar cargar configuración manual
    config_path = Path(__file__).parent.parent.parent / "config" / "server_config.json"
    
    if HOST is None:
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = load(f)
                    HOST = config.get("server_ip")
                    tcp_port = config.get("server_port", 5255)
                    _print_status(f"[CONFIG] Servidor configurado: {HOST}:{tcp_port}")
            except Exception as e:
                _print_status(f"[ERROR] Error al leer configuracion: {e}")
                raise
        else:
            _print_status(f"[ERROR] No se especificó IP del servidor")
            _print_status(f"[SOLUCION] Crea config/server_config.json con:")
            _print_status(f'   {{"server_ip": "192.168.1.X", "server_port": 5255}}')
            raise ValueError("IP del servidor no especificada")
    
    # Verificar que tenemos IP del servidor (por cualquier método)
    if HOST is None:
        _print_status("[ERROR] No se pudo determinar IP del servidor")
        return

    # Directorio para archivos de salida
    output_dir = Path(__file__).parent.parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Guardar info del servidor localmente
    with open(output_dir / "servidor.json", "w", encoding="utf-8") as f:
        dump({"server_ip": HOST, "server_port": tcp_port}, f, indent=4)

    # Preparar datos completos (informe + DirectX)
    preparar_datos_completos()
    
    # Agregar IP del cliente
    try:
        # Obtener IP local conectando al servidor
        temp_sock = socket(AF_INET, SOCK_DGRAM)
        temp_sock.connect((HOST, tcp_port))
        new["client_ip"] = temp_sock.getsockname()[0]
        temp_sock.close()
    except:
        new["client_ip"] = "unknown"
    
    # SECURITY: Agregar token de autenticación
    if security_available and generate_auth_token:
        try:
            new["auth_token"] = generate_auth_token()
            _print_status("[OK] Token de autenticacion agregado")
        except ValueError as e:
            _print_status(f"[WARN] ERROR generando token: {e}")
            _print_status("   Configurar SHARED_SECRET en security_config.py")
            return  # No enviar sin autenticación si está habilitada
    
    # Conectar vía TCP y enviar todo
    _print_status(f"[CONNECT] Conectando al servidor {HOST}:{tcp_port}...")
    try:
        cliente = socket(AF_INET, SOCK_STREAM)
        cliente.connect((HOST, tcp_port))
        cliente.sendall(dumps(new).encode("utf-8"))
        cliente.close()
        _print_status("[OK] Datos enviados correctamente al servidor")
    except Exception as e:
        _print_status(f"[ERROR] Error al enviar datos: {e}")


def configurar_tarea(valor=1):
    """Configura auto-start de specs.py en registro de Windows.
    
    Args:
        valor (int): 0=agregar tarea, 1=consultar tarea, 2=eliminar tarea
    
    Returns:
        None
    
    Note:
        Usa registro HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
        para ejecutar specs.py --tarea al iniciar Windows.
        
    Security:
        Usa subprocess con lista de argumentos (NO shell=True) para prevenir inyección.
    """
    from re import match
    from pathlib import Path
    
    # Validar nombre_tarea contra caracteres peligrosos
    if not match(r'^[a-zA-Z0-9_-]+$', nombre_tarea):
        raise ValueError(f"Nombre de tarea inválido: {nombre_tarea}. Solo se permiten letras, números, guiones y guiones bajos.")
    
    accion = ["add", "query", "delete"]
    reg_key = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
    
    # Construir argumentos como lista (NO string)
    cmd_args = ["reg", accion[valor], reg_key, "/v", nombre_tarea]
    
    if valor == 0:  # Agregar tarea
        # Obtener path del script actual
        if getattr(sys, "frozen", False):
            # Ejecutable empaquetado
            script_path = sys.executable
        else:
            # Script Python
            script_path = str(Path(__file__).parent / "specs.py")
        
        # Agregar parámetros de valor
        cmd_args.extend(["/d", f'"{script_path}" --tarea', "/f"])
    elif valor == 2:  # Eliminar tarea
        cmd_args.append("/f")
    # valor == 1 (query) no necesita parámetros adicionales
    
    # Ejecutar sin shell (seguro)
    run(cmd_args, creationflags=CREATE_NO_WINDOW, check=False)
    
    # si la consulta dice que se encontró la tarea, returna True
    if valor == 1:        
        # Leer salida de consulta
        result = run(cmd_args, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
        output = result.stdout + result.stderr
        if "No se encuentra el valor especificado" in output:
            return False
        else:
            return True