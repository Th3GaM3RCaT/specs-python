#!/usr/bin/env python3
"""
optimized_block_scanner.py

Escaneo optimizado por bloques dentro de rangos personalizados de IPs.
Usa probes broadcast/multicast (SSDP/mDNS) por bloque y fallback a ping-sweep chunked
si no hay respuestas. Luego asocia MACs leyendo la tabla ARP.

Ejemplo:
  python3 optimized_block_scanner.py --ranges 10.100.10.50-10.100.10.58 10.101.0.1 --use-broadcast-probe

"""

import argparse
import asyncio
import ipaddress
import csv
import os
import platform
import subprocess
import sys
from socket import socket as sckt, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST, SO_REUSEADDR, IPPROTO_UDP, IPPROTO_IP, IP_MULTICAST_TTL
from select import select as select_func
from pathlib import Path
from itertools import islice
from logica.ping_utils import ping_host
from logica.arp_utils import parse_arp_table
from concurrent.futures import ThreadPoolExecutor, as_completed as futures_as_completed
import ipaddress
import time

# ------------------ SUBPROCESS HELPER (Windows-safe) ------------------
def _run_hidden(cmd, **kwargs):
    """
    Ejecuta subprocess_run() ocultando ventanas CMD en Windows.
    
    Args:
        cmd: Lista de comandos (ej: ["ping", "-n", "1", "8.8.8.8"])
        **kwargs: Argumentos adicionales para subprocess_run()
    
    Returns:
        CompletedProcess
    """
    if platform.system() == "Windows":
        # CREATE_NO_WINDOW = 0x08000000
        kwargs.setdefault('creationflags', 0x08000000)
    
    return subprocess.run(cmd, **kwargs)

# ------------------ DEFAULTS ------------------
DEFAULT_START = 100
DEFAULT_END = 119
DEFAULT_CHUNK = 255
try:
    from config.security_config import (
        SCAN_PER_HOST_TIMEOUT,
        SCAN_PER_SUBNET_TIMEOUT,
        SCAN_PROBE_TIMEOUT,
        OUTPUT_DIR as ENV_OUTPUT_DIR
    )
    PER_HOST_TIMEOUT = SCAN_PER_HOST_TIMEOUT
    PER_SUBNET_TIMEOUT = SCAN_PER_SUBNET_TIMEOUT
    PROBE_TIMEOUT = SCAN_PROBE_TIMEOUT
    output_dir_str = ENV_OUTPUT_DIR
except ImportError:
    # Fallbacks si no hay .env
    PER_HOST_TIMEOUT = 0.8
    PER_SUBNET_TIMEOUT = 8.0
    PROBE_TIMEOUT = 0.9
    output_dir_str = "output"

DEFAULT_PER_HOST_TIMEOUT = 0.8
DEFAULT_PER_SUBNET_TIMEOUT = 8.0
DEFAULT_CONCURRENCY = 300
DEFAULT_PROBE_TIMEOUT = 0.9
CSV_PREFIX = "optimized_scan"
project_root = Path(__file__).parent.parent.parent
OUTPUT_DIR = project_root / output_dir_str
OUTPUT_DIR.mkdir(exist_ok=True)
CSV_FILENAME = OUTPUT_DIR / "discovered_devices.csv"

SSDP_MSEARCH = '\r\n'.join([
    'M-SEARCH * HTTP/1.1',
    'HOST:239.255.255.250:1900',
    'MAN:"ssdp:discover"',
    'MX:2',
    'ST:ssdp:all',
    '', ''
]).encode('utf-8')

MDNS_SIMPLE = b"\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00"

# ------------------ NETWORK HELPERS ------------------
def get_private_supernets():
    return [
        ipaddress.ip_network("10.0.0.0/8"),
    ]

def get_local_ip():
    s = sckt(AF_INET, SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

def get_local_supernet():
    local = ipaddress.ip_address(get_local_ip())
    for n in get_private_supernets():
        if local in n:
            return n
    raise RuntimeError("IP local no pertenece a 10.0.0.0/8. Ejecuta desde la red objetivo.")

# ------------------ BROADCAST / MULTICAST PROBES ------------------
def probe_ssdp(segment_network, iface_ip=None, timeout=1.0, use_broadcast=True):
    """Síncrono: envía M-SEARCH a multicast y directed broadcast (si está permitido). Devuelve set IPs."""
    results = set()
    sock_list = []
    try:
        msock = sckt(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        msock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        try:
            msock.setsockopt(IPPROTO_IP, IP_MULTICAST_TTL, 1)
        except Exception:
            pass
        if iface_ip:
            try:
                msock.bind((iface_ip, 0))
            except Exception:
                pass
        msock.setblocking(False)
        sock_list.append(msock)
        try:
            msock.sendto(SSDP_MSEARCH, ("239.255.255.250", 1900))
        except Exception:
            pass

        bsock = None
        if use_broadcast:
            try:
                baddr = str(segment_network.broadcast_address)
                bsock = sckt(AF_INET, SOCK_DGRAM)
                bsock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
                try:
                    bsock.bind((iface_ip, 0))
                except Exception:
                    pass
                try:
                    bsock.sendto(SSDP_MSEARCH, (baddr, 1900))
                except Exception:
                    pass
                bsock.setblocking(False)
                sock_list.append(bsock)
            except Exception:
                bsock = None

        start = time.time()
        while True:
            remaining = start + timeout - time.time()
            if remaining <= 0:
                break
            rlist, _, _ = select_func(sock_list, [], [], remaining)
            if not rlist:
                continue
            for s in rlist:
                try:
                    data, addr = s.recvfrom(65535)
                except Exception:
                    continue
                results.add(addr[0])
    finally:
        for s in sock_list:
            try:
                s.close()
            except Exception:
                pass
    return results

def probe_mdns(segment_network, iface_ip=None, timeout=1.0):
    """Síncrono: pequeño probe mDNS. Devuelve set IPs."""
    results = set()
    try:
        msock = sckt(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        msock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        try:
            msock.setsockopt(IPPROTO_IP, IP_MULTICAST_TTL, 1)
        except Exception:
            pass
        if iface_ip:
            try:
                msock.bind((iface_ip, 0))
            except Exception:
                pass
        msock.setblocking(False)
        try:
            msock.sendto(MDNS_SIMPLE, ("224.0.0.251", 5353))
        except Exception:
            pass
        start = time.time()
        while True:
            remaining = start + timeout - time.time()
            if remaining <= 0:
                break
            rlist, _, _ = select_func([msock], [], [], remaining)
            if not rlist:
                continue
            for s in rlist:
                try:
                    data, addr = s.recvfrom(65535)
                except Exception:
                    continue
                results.add(addr[0])
    finally:
        try:
            msock.close() # type: ignore
        except Exception:
            pass
    return results

# ------------------ PING CHUNKED (async) ------------------
# Reutilizamos las implementaciones centralizadas en `logica.ping_utils`
# `ping_one_cmd` y `ping_host` ya están importadas desde ese módulo.

def chunked_iterable(iterable, size):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk

async def ping_sweep_chunked(network, chunk_size, per_host_timeout, per_subnet_timeout, concurrency):
    sem = asyncio.Semaphore(concurrency)
    alive = []
    hosts = list(network.hosts())
    total = len(hosts)
    start_time = time.time()

    async def worker(ip):
        async with sem:
            ok = await ping_host(str(ip), per_host_timeout=per_host_timeout)
            return str(ip) if ok else None

    processed = 0
    for chunk in chunked_iterable(hosts, chunk_size):
        elapsed = time.time() - start_time
        if elapsed >= per_subnet_timeout:
            break
        tasks = [asyncio.create_task(worker(ip)) for ip in chunk]
        try:
            timeout_remaining = max(0.1, per_subnet_timeout - (time.time() - start_time))
            for fut in asyncio.as_completed(tasks, timeout=timeout_remaining):
                try:
                    res = await fut
                    if res:
                        alive.append(res)
                except asyncio.TimeoutError:
                    pass
                except Exception:
                    pass
        except asyncio.TimeoutError:
            for t in tasks:
                if not t.done():
                    t.cancel()
            break
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()
        processed += len(chunk)
    return sorted(set(alive), key=lambda s: tuple(int(x) for x in s.split(".")))

# ------------------ BLOCK PATTERNS ------------------
# Blocks are tuples (start_ip_inclusive, end_ip_inclusive) defined inside each /16.
# We'll create ipaddress.ip_network objects for each block



# ------------------ SMALL HELPERS ------------------
def probe_block(segment_net, iface_ip, timeout, use_broadcast):
    ssdp = probe_ssdp(segment_net, iface_ip=iface_ip, timeout=timeout, use_broadcast=use_broadcast)
    if ssdp:
        return set(ssdp)
    mdns = probe_mdns(segment_net, iface_ip=iface_ip, timeout=timeout)
    return set(mdns)

# ------------------ MAIN FLOW ------------------
async def scan_blocks(ranges, chunk_size, per_host_timeout, per_subnet_timeout, concurrency, probe_timeout, use_broadcast_probe, callback_progreso=None):
    local_super = get_local_supernet()
    all_alive = set()
    loop = asyncio.get_event_loop()

    total_ranges = len(ranges)

    for idx, range_str in enumerate(ranges, start=1):
        print(f"\n--- Rango {idx}/{total_ranges}: {range_str} ---")
        
        # Parsear rango: start-end o solo start
        if '-' in range_str:
            start_ip, end_ip = range_str.split('-', 1)
        else:
            start_ip = end_ip = range_str
        
        # Generar red
        try:
            from logica.scan_rangos_ip import calculate_ip_range
            subnet1, subnet2 = calculate_ip_range(start_ip, end_ip) # type: ignore
            subnets = [subnet1]
            if subnet2:
                subnets.append(subnet2)
        except ValueError as e:
            print(f"  [ERROR] Rango inválido {range_str}: {e}")
            continue
            
        for sub_idx, network in enumerate(subnets):
            print(f"  -> Subred {sub_idx+1}: {network}")
            # Emitir progreso al callback si existe
            if callback_progreso:
                try:
                    callback_progreso({
                        'tipo': 'rango',
                        'rango_actual': range_str,
                        'rango_index': idx,
                        'rangos_totales': total_ranges,
                        'mensaje': f"Escaneando rango {idx}/{total_ranges}: {range_str} -> {network}"
                    })
                except Exception as e:
                    print(f"[WARN] Error emitiendo progreso: {e}")
            
            # Probe by broadcast/multicast first (cheap)
            found_ips = set()
            if use_broadcast_probe:
                try:
                    found_ips = await loop.run_in_executor(None, probe_block, network, None, probe_timeout, True)
                except Exception:
                    found_ips = set()
                if found_ips:
                    print(f"     probe found {len(found_ips)} hosts (examples: {list(found_ips)[:6]})")
                    all_alive.update(found_ips)
            
            # Hacer ping sweep en la red (complementa los probes)
            num_hosts = network.num_addresses - 2
            if num_hosts <= 0:
                continue
            # Saltar si el bloque es muy grande
            if num_hosts > 4096:
                print(f"     skipping sweep of {network} (too large: {num_hosts} hosts)")
                continue
            print(f"     doing chunked sweep of {network} ({num_hosts} hosts)")
            alive = await ping_sweep_chunked(network, chunk_size=chunk_size, per_host_timeout=per_host_timeout,
                                            per_subnet_timeout=per_subnet_timeout, concurrency=concurrency)
            if alive:
                print(f"     => {len(alive)} alive in network (examples: {alive[:6]})")
                all_alive.update(alive)
            else:
                print("     => 0 alive in network")

    return sorted(all_alive, key=lambda s: tuple(int(x) for x in s.split(".")))

def merge_with_arp(alive_ips):
    """
    Asocia IPs con MACs de la tabla ARP.
    Filtra IPs de equipos de red (routers, switches, APs) dejando solo computadoras.
    """
    arp = parse_arp_table()
    arp_map = dict(arp)
    out = []
    for ip in sorted(alive_ips, key=lambda s: tuple(int(x) for x in s.split("."))):
        mac = arp_map.get(ip)
        
        # Filtrar equipos de red: solo incluir si es computadora o si no tiene MAC
        if mac and not is_computer_mac(mac):
            continue  # Salta routers, switches, APs
        
        out.append((ip, mac))
    return out

def parse_args():
    p = argparse.ArgumentParser(description="Optimized block scanner for custom IP ranges.")
    p.add_argument("--ranges", nargs='+', help="Rangos de IPs a escanear (formato: start-end o solo start). Ej: --ranges 10.100.10.50-10.100.10.58 10.101.0.1")
    p.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK)
    p.add_argument("--per-host-timeout", type=float, default=DEFAULT_PER_HOST_TIMEOUT)
    p.add_argument("--per-subnet-timeout", type=float, default=DEFAULT_PER_SUBNET_TIMEOUT)
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    p.add_argument("--probe-timeout", type=float, default=DEFAULT_PROBE_TIMEOUT)
    p.add_argument("--use-broadcast-probe", action="store_true", help="use SSDP/mDNS probe before sweeping blocks")
    p.add_argument("--csv", action="store_true", help="save CSV (default: yes)")
    return p.parse_args()

def is_computer_mac(mac):
    """Determina si una MAC pertenece a un dispositivo tipo computadora."""
    if not mac:
        return False
    
    # Extraer OUI (primeros 3 octetos)
    oui = mac[:8].upper()  # Formato: XX:XX:XX
    
    # OUIs de fabricantes de COMPUTADORAS (PCs, laptops, tablets)
    computer_vendors = {
        # Dell
        '00:14:22', '00:1E:C9', '18:03:73', '74:86:7A', 'D4:AE:52', 
        'B8:CA:3A', 'D4:BE:D9', '98:90:96', '10:98:36', '84:7B:EB',
        # HP/Compaq
        '00:17:C8', '00:17:A4', '00:1F:29', '00:21:5A', '00:23:7D',
        '00:25:B3', '3C:D9:2B', '70:5A:B6', 'A0:48:1C', '00:26:55',
        # Lenovo/IBM
        '00:1A:6B', '54:42:49', 'B0:5A:DA', 'C8:1F:66', '00:23:54',
        'F0:DE:F1', '50:65:F3', '00:21:CC', '34:02:86',
        # Acer
        '00:03:0D', '00:24:21', 'E0:B9:A5', '00:26:B6', '60:EB:69',
        # Asus
        '00:1E:8C', '00:22:15', '04:D4:C4', '08:60:6E', '10:C3:7B',
        # Toshiba
        '00:00:39', '00:60:67', '00:A0:B0', '00:C0:D0', '28:E3:47',
        # Apple (Mac)
        '00:03:93', '00:0A:95', '00:17:F2', '00:1C:B3', '00:23:12',
        '00:25:00', '28:CF:E9', '3C:07:54', '68:5B:35', 'A8:20:66',
        # Samsung
        '00:12:47', '00:13:77', '00:15:B9', '00:1E:7D', '00:23:39',
        # MSI
        '00:23:54', '00:27:0E', '00:30:67', 'E0:94:67',
        # Microsoft Surface
        '00:15:5D', '00:50:F2', '28:18:78', 'A0:A4:C5',
        # Gigabyte
        '00:24:1D', 'E0:3F:49',
        # Intel (NUCs, laptops)
        '00:15:00', '00:1B:21', '5C:51:4F', '94:C6:91',
        # Realtek (NICs comunes en PCs)
        '00:E0:4C', '52:54:00', 'E0:D5:5E',
        # Broadcom (NICs comunes en laptops)
        '00:10:18', '00:90:4B',
        # TP-Link (algunos adaptadores USB WiFi, no routers)
        '50:C7:BF', 'A0:F3:C1', 'C4:6E:1F',
    }
    
    # OUIs de ROUTERS, SWITCHES y EQUIPOS DE RED (a descartar)
    network_equipment = {
        # Cisco
        '00:00:0C', '00:01:42', '00:01:63', '00:01:64', '00:01:96',
        '00:01:97', '00:02:17', '00:02:3D', '00:02:4A', '00:02:4B',
        '00:02:7D', '00:02:7E', '00:02:B9', '00:02:BA', '00:02:FC',
        # Ubiquiti (APs, routers)
        '00:15:6D', '00:27:22', '04:18:D6', '24:A4:3C', '68:D7:9A',
        '70:A7:41', '74:83:C2', '80:2A:A8', 'B4:FB:E4', 'DC:9F:DB',
        # MikroTik
        '00:0C:42', '4C:5E:0C', '6C:3B:6B', '74:4D:28', 'D4:CA:6D',
        # Huawei (routers)
        '00:46:4B', '00:66:4B', '00:E0:FC', '04:C0:6F', '70:72:3C',
        # ZTE (routers)
        '00:19:CB', '24:1F:A0', '48:3B:38', '6C:59:40', 'F8:E7:1E',
        # D-Link (switches, routers)
        '00:01:C0', '00:05:5D', '00:0D:88', '00:11:95', '00:13:46',
        # Netgear (routers)
        '00:09:5B', '00:14:6C', '00:1B:2F', '00:1E:2A', '00:26:F2',
        # Linksys
        '00:06:25', '00:0C:41', '00:0E:08', '00:12:17', '00:13:10',
        # Aruba Networks (APs)
        '00:0B:86', '00:1A:1E', '20:4C:03', '24:DE:C6', '70:3A:0E',
        # Juniper Networks
        '00:05:85', '00:12:1E', '00:19:E2', '00:1F:12', '00:21:59',
        # HPE/Aruba switches
        'E0:50:8B', 'A0:B3:CC', '94:B4:0F',
        # Fortinet (firewalls)
        '00:09:0F', '08:5B:0E', '70:4C:A5', '90:6C:AC',
        # Sophos (firewalls)
        '00:1A:8C', '7C:5A:1C', '00:30:BD',
        # SonicWall (firewalls)
        '00:06:B1', '00:17:C5', '00:1D:6A', 'C0:EA:E4',
    }
    
    # Primero verificar si es equipo de red (excluir)
    if oui in network_equipment:
        return False
    
    # Verificar si es computadora conocida
    if oui in computer_vendors:
        return True
    
    # Si no está en ninguna lista, aplicar heurística:
    # - Routers típicamente tienen MACs en rangos reservados o multicast
    # - MACs que terminan en patrones específicos de red
    
    # Descartar MACs multicast o broadcast
    first_octet = int(mac[:2], 16)
    if first_octet & 0x01:  # Bit multicast activado
        return False
    
    # Por defecto, si no sabemos, asumimos que SÍ es computadora
    # (esto incluirá PCs genéricas/clones con NICs no identificados)
    return True

def update_csv_with_macs(
    input_csv_path,
    output_csv_path=None,
    ping_missing=True,
    ping_timeout=0.8,
    workers=50,
    overwrite=True
):
    """
    Lee CSV de entrada con IPs, intenta poblar MACs usando tabla ARP.
    Opcionalmente hace ping a IPs sin MAC para poblar la tabla ARP.
    
    Args:
        input_csv_path (str): Path al CSV de entrada.
        output_csv_path (str|None): Path de salida. Si None, crea "<input>_with_macs.csv" 
                                     o sobrescribe si overwrite=True.
        ping_missing (bool): Si True, hace ping a IPs sin MAC antes de leer ARP.
        ping_timeout (float): Timeout por ping en segundos.
        workers (int): Concurrencia para pings.
        overwrite (bool): Si True y output_csv_path es None, sobrescribe input file.
    
    Returns:
        dict: {'input': path, 'output': path, 'total_rows': n, 'mac_found': m, 'mac_missing': k}
    """
    if not os.path.isfile(input_csv_path):
        raise FileNotFoundError(f"Input CSV not found: {input_csv_path}")
    
    # 1) Leer CSV y detectar columnas
    rows = []
    with open(input_csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        lower_fields = [h.lower() for h in fields]
        
        for r in reader:
            row = {k: (v.strip() if v is not None else "") for k, v in r.items()}
            
            # Buscar columna IP
            ip = None
            for candidate in ("ip", "address", "host"):
                if candidate in lower_fields:
                    ip = row[fields[lower_fields.index(candidate)]]
                    break
            if ip is None and len(fields) >= 2:
                ip = row[fields[1]]
            
            # Buscar columna MAC
            mac = None
            for candidate in ("mac", "ether", "hwaddr"):
                if candidate in lower_fields:
                    mac = row[fields[lower_fields.index(candidate)]]
                    break
            if mac is None and len(fields) >= 3:
                mac = row[fields[2]]
            
            rows.append({"raw": row, "ip": ip, "mac": (mac or "").strip()})
    
    total = len(rows)
    
    # 2) Identificar IPs sin MAC
    missing_ips = [r["ip"] for r in rows if r["ip"] and (not r["mac"])]
    missing_ips = list(dict.fromkeys(missing_ips))  # Dedupe preserve order
    print(f"CSV rows: {total}, IPs missing MAC: {len(missing_ips)}")
    ping_missing = False
    # 3) Opcional: ping masivo concurrente para poblar ARP
    if ping_missing and missing_ips:
        print(f"Pinging {len(missing_ips)} IPs (timeout={ping_timeout}s, workers={workers}) to populate ARP...")
        with ThreadPoolExecutor(max_workers=min(workers, len(missing_ips))) as ex:
            futures = {ex.submit(_ping_ip_sync, ip, ping_timeout): ip for ip in missing_ips}
            for fut in futures_as_completed(futures):
                ip = futures[fut]
                try:
                    ok = fut.result()
                except Exception:
                    ok = False
        # Pequeña espera para que la tabla ARP se actualice
        time.sleep(0.5)
    
    # 4) Re-parsear tabla ARP
    try:
        arp_entries = parse_arp_table()
    except Exception as e:
        print(f"Warning: parse_arp_table() falló: {e}")
        arp_entries = []
    
    arp_map = {ip: mac.lower() for ip, mac in arp_entries if mac}
    
    # 5) Actualizar filas con MACs si están ahora en arp_map
    updated = 0
    still_missing = 0
    for r in rows:
        ip = r["ip"]
        if not ip:
            continue
        if r["mac"]:
            continue  # Ya tenía MAC
        mac = arp_map.get(ip)
        if mac:
            r["mac"] = mac
            updated += 1
        else:
            still_missing += 1
    
    print(f"MACs found by ARP: {updated}, still missing: {still_missing}")
    
    # 6) Escribir CSV de salida
    if output_csv_path is None:
        if overwrite:
            output_csv_path = input_csv_path
        else:
            base, ext = os.path.splitext(input_csv_path)
            output_csv_path = f"{base}_with_macs{ext}"
    
    # Construir header: conservar campos originales, asegurar columna 'mac'
    orig_fieldnames: list[str] = list(fields) if fields else ["ip", "mac"]
    low = [h.lower() for h in orig_fieldnames]
    if "mac" not in low:
        orig_fieldnames.append("mac")

    with open(output_csv_path, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=orig_fieldnames)
        writer.writeheader()
        for r in rows:
            outrow = {}
            # Llenar valores originales
            for h in orig_fieldnames:
                if h in r["raw"]:
                    outrow[h] = r["raw"].get(h, "")
                else:
                    # Match case-insensitive
                    for k in r["raw"]:
                        if k.lower() == h.lower():
                            outrow[h] = r["raw"].get(k, "")
                            break
                    else:
                        outrow[h] = ""
            
            # Asegurar campo 'mac' actualizado
            for idx, name in enumerate(orig_fieldnames):
                if name.lower() == "mac":
                    outrow[name] = r.get("mac") or ""
                    break
            
            writer.writerow(outrow)
    
    return {
        "input": input_csv_path,
        "output": output_csv_path,
        "total_rows": total,
        "mac_found": updated,
        "mac_missing": still_missing
    }

def _ping_ip_sync(ip: str, timeout: float = 1.0) -> bool:
    """
    Ping síncrono para uso en ThreadPoolExecutor.
    Retorna True si el host responde.
    
    IMPORTANTE: Oculta ventanas CMD en Windows usando _run_hidden().
    
    Args:
        ip: Dirección IP a hacer ping
        timeout: Timeout en segundos (acepta float)
    
    Returns:
        True si el host responde, False en caso contrario
    """
    system = platform.system()
    if system == "Windows":
        cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), ip]
    elif system == "Darwin":
        cmd = ["ping", "-c", "1", "-t", "1", ip]
    else:
        cmd = ["ping", "-c", "1", "-W", str(int(max(1, timeout))), ip]
    
    try:
        proc = _run_hidden(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )
        return proc.returncode == 0
    except Exception:
        return False

# ------------------ ENTRYPOINT ------------------
def main(callback_progreso=None):
    """
    Entry point principal del scanner.
    
    Args:
        callback_progreso: Función opcional que recibe diccionarios con información de progreso.
                          Ejemplo: {'tipo': 'rango', 'rango_actual': '10.100.10.50-10.100.10.58', 'mensaje': '...'}
    """
    args = parse_args()
    if not args.ranges:
        print("ERROR: Debes proporcionar al menos un rango con --ranges")
        #sys.exit(1)
    
    try:
        local_super = get_local_supernet()
    except Exception as e:
        print("ERROR:", e)
        #sys.exit(1)

    print(f"Scanning custom ranges: {args.ranges} (use-broadcast={args.use_broadcast_probe})")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        alive = loop.run_until_complete(scan_blocks(args.ranges,
                                                    chunk_size=args.chunk_size,
                                                    per_host_timeout=args.per_host_timeout,
                                                    per_subnet_timeout=args.per_subnet_timeout,
                                                    concurrency=args.concurrency,
                                                    probe_timeout=args.probe_timeout,
                                                    use_broadcast_probe=args.use_broadcast_probe,
                                                    callback_progreso=callback_progreso))
    finally:
        loop.close()

    print(f"\nTotal alive IPs found: {len(alive)} (examples: {alive[:20]})")
    
    # Notificar finalización de escaneo
    if callback_progreso:
        try:
            callback_progreso({
                'tipo': 'fase',
                'fase': 'escaneo_completado',
                'mensaje': f"Escaneo completado: {len(alive)} IPs activas encontradas"
            })
        except Exception:
            pass
    
    merged = merge_with_arp(alive)
    
    # Estadísticas de filtrado
    filtered_count = len(alive) - len(merged)
    if filtered_count > 0:
        print(f"[FILTRADO] Excluidas {filtered_count} IPs de equipos de red (routers, switches, APs)")
        print(f"[RESULTADO] {len(merged)} IPs de computadoras para CSV")
    
    # Notificar filtrado
    if callback_progreso:
        try:
            callback_progreso({
                'tipo': 'fase',
                'fase': 'filtrado_completado',
                'mensaje': f"Filtrado: {len(merged)} computadoras ({filtered_count} equipos de red excluidos)"
            })
        except Exception:
            pass
    
    # --- Guardar IPs descubiertas en CSV temporal (sin MACs todavía) ---
    temp_csv = "temp_scan.csv"
    
    # 1. Leer dispositivos existentes del CSV (preservar lista histórica)
    existing_devices = {}
    if os.path.exists(CSV_FILENAME):
        try:
            with open(CSV_FILENAME, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header == ['ip', 'mac']:
                    for row in reader:
                        if len(row) == 2:
                            existing_devices[row[0]] = row[1] if row[1] else ""
        except Exception as e:
            print(f"Advertencia: No se pudo leer CSV existente: {e}")

    # 2. Agregar nuevas IPs del escaneo FILTRADAS (solo computadoras)
    for ip, mac in merged:
        if ip not in existing_devices:
            existing_devices[ip] = mac or ""

    # 3. Ordenar por IP (numéricamente)
    sorted_devices = sorted(existing_devices.items(), 
                           key=lambda item: tuple(map(int, item[0].split('.'))))

    # 4. Escribir CSV temporal con todas las IPs
    if callback_progreso:
        try:
            callback_progreso({
                'tipo': 'fase',
                'fase': 'guardando_csv',
                'mensaje': f"Guardando CSV con {len(sorted_devices)} dispositivos..."
            })
        except Exception:
            pass
    
    with open(temp_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ip", "mac"])
        for ip, mac in sorted_devices:
            writer.writerow([ip, mac])
    
    print(f"\n>> Poblando MACs con get_mac.py (rapido: ~3.6s)...")
    
    if callback_progreso:
        try:
            callback_progreso({
                'tipo': 'fase',
                'fase': 'poblando_macs',
                'mensaje': "Poblando direcciones MAC desde tabla ARP..."
            })
        except Exception:
            pass
    
    # 5. Usar update_csv_with_macs para poblar MACs eficientemente
    try:
        result = update_csv_with_macs(
            input_csv_path=temp_csv,
            output_csv_path=CSV_FILENAME,
            ping_missing=True,
            ping_timeout=0.8,
            workers=50,
            overwrite=False
        )
        
        print(f"[OK] CSV actualizado: '{CSV_FILENAME}'")
        print(f"   - Total dispositivos: {result['total_rows']}")
        print(f"   - MACs encontradas: {result['mac_found']}")
        print(f"   - Sin MAC: {result['mac_missing']}")
        print(f"   - Nuevas computadoras en este escaneo: {len(merged)}")
        
    except Exception as e:
        print(f"Error poblando MACs: {e}")
        # Fallback: copiar temp_csv como resultado
        import shutil
        shutil.copy(temp_csv, CSV_FILENAME)
    finally:
        # Limpiar archivo temporal
        if os.path.exists(temp_csv):
            os.remove(temp_csv)
    
    return alive

if __name__ == "__main__":
    
    # Inicio del contador lo más arriba posible
    start_time = time.time()
    
    main()
    
    # Fin del contador al final del script
    end_time = time.time()
    print(f"Tiempo total de ejecución: {end_time - start_time:.6f} segundos")