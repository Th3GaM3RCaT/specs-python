# logica_specs.py
from datetime import datetime
from json import dump, dumps
from locale import getpreferredencoding
from os import environ, name, path
from re import IGNORECASE, search
from socket import AF_INET, SOCK_DGRAM, SOCK_STREAM, socket, timeout
from subprocess import CREATE_NO_WINDOW, run
import sys

import psutil
from getmac import get_mac_address as gma
from PySide6.QtWidgets import QPushButton
from windows_tools.installed_software import get_installed_software
from wmi import WMI

nombre_tarea = "informe_de_dispositivo"
run_button = QPushButton()
send_button = QPushButton()
new = {}
hilo = None

def get_size(bytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def informe():

    run_button.setEnabled(False)
    my_system = WMI().Win32_ComputerSystem()[0]

    from datos.serialNumber import get_serial
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


    from datos.get_ram import get_ram_info

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
    new["Total read"] = f"{get_size(disk_io.read_bytes)}"  # type: ignore
    new["Total write"] = f" {get_size(disk_io.write_bytes)}"  # type: ignore

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


def get_license_status(a=0):
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

def enviar_a_servidor():
    PORT = 5255
    txt_data = ""
    s = socket(AF_INET, SOCK_DGRAM)
    s.settimeout(5)
    s.bind(("", PORT))
    

    try:
        # Descubrir servidor vía UDP
        addr = s.recvfrom(1024)
        HOST = addr[0]
        
        print("Servidor encontrado:", HOST)

        # Guardar info del servidor localmente
        with open("servidor.json", "w", encoding="utf-8") as f:
            dump(addr, f, indent=4)

        with open("dxdiag_output.txt", "r", encoding="utf-8") as f:
            txt_data = f.read()
        # Incluir el TXT dentro del JSON
        new["dxdiag_output_txt"] = txt_data

        # Conectar vía TCP y enviar todo
        cliente = socket(AF_INET, SOCK_STREAM)
        cliente.connect((HOST, PORT))
        cliente.sendall(dumps(new).encode("utf-8"))
        cliente.close()
        print("Datos enviados correctamente")

    except timeout:
        print("No se encontró el servidor")


def configurar_tarea(valor=1):
    accion = ["add", "query", "delete"]
    modo = '\\"C:\\Python39\\python.exe\\" '
    if getattr(sys, "frozen", False):
        modo = ""
    agregar = '/d "{modo}\\"{script_path}\\" --tarea" /f'
    if valor == 1:
        agregar = ""
    if valor == 2:
        agregar = "/f"
    comando = f'reg {accion[valor]} "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v {nombre_tarea} {agregar} '
    run(comando, shell=True, creationflags=CREATE_NO_WINDOW)