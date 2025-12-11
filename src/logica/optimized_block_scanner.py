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
from socket import (
    socket as sckt,
    AF_INET,
    SOCK_DGRAM,
    SOL_SOCKET,
    SO_BROADCAST,
    SO_REUSEADDR,
    IPPROTO_UDP,
    IPPROTO_IP,
    IP_MULTICAST_TTL,
)
from select import select as select_func
from pathlib import Path
from itertools import islice
from logica.ping_utils import ping_host
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
        kwargs.setdefault("creationflags", 0x08000000)

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
        OUTPUT_DIR as ENV_OUTPUT_DIR,
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
DEFAULT_CONCURRENCY = 50  # Reducido de 300 para evitar sobrecarga del sistema con rangos grandes
DEFAULT_PROBE_TIMEOUT = 0.9
CSV_PREFIX = "optimized_scan"
project_root = Path(__file__).parent.parent.parent
OUTPUT_DIR = project_root / output_dir_str
OUTPUT_DIR.mkdir(exist_ok=True)
CSV_FILENAME = OUTPUT_DIR / "discovered_devices.csv"

SSDP_MSEARCH = "\r\n".join(
    [
        "M-SEARCH * HTTP/1.1",
        "HOST:239.255.255.250:1900",
        'MAN:"ssdp:discover"',
        "MX:2",
        "ST:ssdp:all",
        "",
        "",
    ]
).encode("utf-8")

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
    raise RuntimeError(
        "IP local no pertenece a 10.0.0.0/8. Ejecuta desde la red objetivo."
    )


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
            msock.close()  # type: ignore
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


async def ping_sweep_chunked(
    network, chunk_size, per_host_timeout, per_subnet_timeout, concurrency
):
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
            timeout_remaining = max(
                0.1, per_subnet_timeout - (time.time() - start_time)
            )
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
    ssdp = probe_ssdp(
        segment_net, iface_ip=iface_ip, timeout=timeout, use_broadcast=use_broadcast
    )
    if ssdp:
        return set(ssdp)
    mdns = probe_mdns(segment_net, iface_ip=iface_ip, timeout=timeout)
    return set(mdns)


# ------------------ MAIN FLOW ------------------
async def scan_blocks(
    ranges,
    chunk_size,
    per_host_timeout,
    per_subnet_timeout,
    concurrency,
    probe_timeout,
    use_broadcast_probe,
    callback_progreso=None,
):
    get_local_supernet()
    all_alive = set()
    loop = asyncio.get_event_loop()

    total_ranges = len(ranges)

    # Calcular tamaño total del escaneo para ajustar concurrencia dinámicamente
    total_ips = 0
    for range_str in ranges:
        try:
            if "-" in range_str:
                start_ip, end_ip = range_str.split("-", 1)
            else:
                start_ip = end_ip = range_str
            from logica.scan_rangos_ip import calculate_ip_range
            subnet1, subnet2 = calculate_ip_range(start_ip, end_ip) # type: ignore
            total_ips += subnet1.num_addresses
            if subnet2:
                total_ips += subnet2.num_addresses
        except:
            pass  # Ignorar errores de cálculo para este propósito

    # Ajustar concurrencia basada en tamaño del rango para evitar sobrecarga
    if total_ips > 500:  # Rangos muy grandes
        adjusted_concurrency = min(concurrency, 25)  # Máximo 25 para rangos grandes
        print(f"[OPTIMIZACION] Rango grande detectado ({total_ips} IPs). Concurrencia ajustada: {concurrency} -> {adjusted_concurrency}")
        concurrency = adjusted_concurrency
    elif total_ips > 100:  # Rangos medianos
        adjusted_concurrency = min(concurrency, 50)  # Máximo 50 para rangos medianos
        if adjusted_concurrency != concurrency:
            print(f"[OPTIMIZACION] Rango mediano detectado ({total_ips} IPs). Concurrencia ajustada: {concurrency} -> {adjusted_concurrency}")
            concurrency = adjusted_concurrency

    print(f"[CONFIG] Concurrencia final: {concurrency} operaciones simultáneas")

    for idx, range_str in enumerate(ranges, start=1):
        print(f"\n--- Rango {idx}/{total_ranges}: {range_str} ---")

        # Parsear rango: start-end o solo start
        if "-" in range_str:
            start_ip, end_ip = range_str.split("-", 1)
        else:
            start_ip = end_ip = range_str

        # Generar red
        try:
            from logica.scan_rangos_ip import calculate_ip_range
            subnet1, subnet2 = calculate_ip_range(start_ip, end_ip)  # type: ignore
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
                    callback_progreso(
                        {
                            "tipo": "rango",
                            "rango_actual": range_str,
                            "rango_index": idx,
                            "rangos_totales": total_ranges,
                            "mensaje": f"Escaneando rango {idx}/{total_ranges}: {range_str} -> {network}",
                        }
                    )
                except Exception as e:
                    print(f"[WARN] Error emitiendo progreso: {e}")

            # Probe by broadcast/multicast first (cheap)
            found_ips = set()
            if use_broadcast_probe:
                try:
                    found_ips = await loop.run_in_executor(
                        None, probe_block, network, None, probe_timeout, True
                    )
                except Exception:
                    found_ips = set()
                if found_ips:
                    print(
                        f"     probe found {len(found_ips)} hosts (examples: {list(found_ips)[:6]})"
                    )
                    all_alive.update(found_ips)

            # Hacer ping sweep en la red (complementa los probes)
            num_hosts = network.num_addresses - 2
            if num_hosts <= 0:
                continue
            # Saltar si el bloque es muy grande
            if num_hosts > 4096:
                print(
                    f"     skipping sweep of {network} (too large: {num_hosts} hosts)"
                )
                continue
            print(f"     doing chunked sweep of {network} ({num_hosts} hosts)")
            alive = await ping_sweep_chunked(
                network,
                chunk_size=chunk_size,
                per_host_timeout=per_host_timeout,
                per_subnet_timeout=per_subnet_timeout,
                concurrency=concurrency,
            )
            if alive:
                print(f"     => {len(alive)} alive in network (examples: {alive[:6]})")
                all_alive.update(alive)
            else:
                print("     => 0 alive in network")

    return sorted(all_alive, key=lambda s: tuple(int(x) for x in s.split(".")))


def parse_args():
    p = argparse.ArgumentParser(
        description="Optimized block scanner for custom IP ranges."
    )
    p.add_argument(
        "--ranges",
        nargs="+",
        help="Rangos de IPs a escanear (formato: start-end o solo start). Ej: --ranges 10.100.10.50-10.100.10.58 10.101.0.1",
    )
    p.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK)
    p.add_argument("--per-host-timeout", type=float, default=DEFAULT_PER_HOST_TIMEOUT)
    p.add_argument(
        "--per-subnet-timeout", type=float, default=DEFAULT_PER_SUBNET_TIMEOUT
    )
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    p.add_argument("--probe-timeout", type=float, default=DEFAULT_PROBE_TIMEOUT)
    p.add_argument(
        "--use-broadcast-probe",
        action="store_true",
        help="use SSDP/mDNS probe before sweeping blocks",
    )
    p.add_argument("--csv", action="store_true", help="save CSV (default: yes)")
    return p.parse_args()


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
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
        )
        return proc.returncode == 0
    except Exception:
        return False


# ------------------ ENTRYPOINT ------------------
def main(callback_progreso=None, ranges=None):
    """
    Entry point principal del scanner.

    Args:
        callback_progreso: Función opcional que recibe diccionarios con información de progreso.
                          Ejemplo: {'tipo': 'rango', 'rango_actual': '10.100.10.50-10.100.10.58', 'mensaje': '...'}
        ranges: Lista de rangos en formato ['10.100.2.1-10.100.2.254']. Si es None, usa argparse.
    """
    # Si se pasan rangos directamente, usarlos; si no, parsear argumentos
    if ranges:
        from types import SimpleNamespace
        args = SimpleNamespace(
            ranges=ranges,
            chunk_size=256,
            per_host_timeout=1.0,
            per_subnet_timeout=5.0,
            concurrency=100,
            probe_timeout=0.5,
            use_broadcast_probe=False
        )
    else:
        args = parse_args()
        if not args.ranges:
            print("ERROR: Debes proporcionar al menos un rango con --ranges")
            return []

    try:
        get_local_supernet()
    except Exception as e:
        print("ERROR:", e)

    print(
        f"Scanning custom ranges: {args.ranges} (use-broadcast={args.use_broadcast_probe})"
    )
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        alive = loop.run_until_complete(
            scan_blocks(
                args.ranges,
                chunk_size=args.chunk_size,
                per_host_timeout=args.per_host_timeout,
                per_subnet_timeout=args.per_subnet_timeout,
                concurrency=args.concurrency,
                probe_timeout=args.probe_timeout,
                use_broadcast_probe=args.use_broadcast_probe,
                callback_progreso=callback_progreso,
            )
        )
    finally:
        loop.close()

    print(f"\nTotal alive IPs found: {len(alive)} (examples: {alive[:20]})")

    # Notificar finalización de escaneo
    if callback_progreso:
        try:
            callback_progreso(
                {
                    "tipo": "fase",
                    "fase": "escaneo_completado",
                    "mensaje": f"Escaneo completado: {len(alive)} IPs activas encontradas",
                }
            )
        except Exception:
            pass

    print(f"[DEBUG] Escaneo completado: {len(alive)} IPs vivas encontradas")

    # No hacer merge_with_arp - el servidor no obtiene MACs, solo IPs
    # Los clientes enviarán sus MACs cuando se conecten
    merged = [(ip, "unknown") for ip in alive]  # Tuplas (IP, MAC) con MAC="unknown"
    print(f"[DEBUG] Retornando {len(merged)} IPs sin lookup de MAC")

    # Estadísticas
    print(f"[RESULTADO] {len(merged)} IPs activas encontradas (MACs serán enviadas por clientes)")

    # Notificar resultado final
    if callback_progreso:
        try:
            callback_progreso(
                {
                    "tipo": "fase",
                    "fase": "escaneo_completado",
                    "mensaje": f"Escaneo completado: {len(merged)} IPs encontradas",
                }
            )
        except Exception:
            pass

    # --- Guardar IPs descubiertas en CSV temporal (sin MACs todavía) ---
    temp_csv = "discovered_devices.csv"

    # 1. Leer dispositivos existentes del CSV (preservar lista histórica)
    existing_devices = {}
    if os.path.exists(CSV_FILENAME):
        try:
            with open(CSV_FILENAME, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header == ["ip", "mac"]:
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
    sorted_devices = sorted(
        existing_devices.items(), key=lambda item: tuple(map(int, item[0].split(".")))
    )

    # 4. Escribir CSV temporal con todas las IPs
    if callback_progreso:
        try:
            callback_progreso(
                {
                    "tipo": "fase",
                    "fase": "guardando_csv",
                    "mensaje": f"Guardando CSV con {len(sorted_devices)} dispositivos...",
                }
            )
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
            callback_progreso(
                {
                    "tipo": "fase",
                    "fase": "poblando_macs",
                    "mensaje": "Poblando direcciones MAC desde tabla ARP...",
                }
            )
        except Exception:
            pass

    # 5. Copiar CSV sin poblar MACs (los clientes enviarán sus MACs)
    try:
        import shutil
        shutil.copy2(temp_csv, CSV_FILENAME)
        print(f"[OK] CSV guardado: '{CSV_FILENAME}' con {len(merged)} dispositivos")
        print("   - MACs serán enviadas por los clientes al conectarse")

    except Exception as e:
        print(f"Error guardando CSV: {e}")
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
