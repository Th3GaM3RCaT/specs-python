#!/usr/bin/env python3
"""
network_scanner_with_mac_chunked.py

Versión segura y práctica del escáner interno (RFC1918) que:
 - Detecta segmentos activos (/16 por defecto).
 - Escanea subredes activas en detalle (por defecto /24).
 - Usa barridos de ping por CHUNKS con timeout por host y timeout global por subred.
 - Lee tabla ARP (ip neigh / arp -a) y asocia IP -> MAC.
 - Exporta CSV con segment, ip, mac.
"""

import argparse
import asyncio
import ipaddress
import platform
import socket
import subprocess
import re
import csv
import sys
import random
import time
from datetime import datetime
from itertools import islice

# ---------------- CONFIG DEFAULTS ----------------
CONCURRENCY = 300              # concurrencia global para ping sweep
ASSUME_SEGMENT_PREFIX = 16    # tamaño del segmento para detectar (p. ej. /16 -> 10.x.0.0/16)
DETAILED_PREFIX = 24          # prefijo para escaneo detallado dentro de segmento (p. ej. /24)
SAMPLE_RANDOM_COUNT = 5       # muestras aleatorias por segmento para detección
MAX_ADDRESSES_PER_SWEEP = 4096  # por subnet para sweep detallado (evita sweeps enormes)
CSV_NAME_PREFIX = "scan_rfc1918" # prefijo para archivo CSV de salida
# Defaults para chunked sweep
DEFAULT_CHUNK_SIZE = 255        # hosts paralelos por chunk
DEFAULT_PER_HOST_TIMEOUT = 1.0     # segundos por host (ping)
DEFAULT_PER_SUBNET_TIMEOUT = 20.0  # segundos máximo por subnet
# -------------------------------------------------

def get_private_supernets():
    return [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
    ]

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # no envía datos realmente pero fuerza selección de interfaz
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

def get_local_supernet():
    local_ip = ipaddress.ip_address(get_local_ip())
    for net in get_private_supernets():
        if local_ip in net:
            return net
    raise RuntimeError(f"IP local {local_ip} no está en redes privadas RFC1918. Abortando por seguridad.")

# ------------------ PING (base y wrapper con timeout) ------------------
async def ping_one_cmd(host, per_host_timeout):
    """Llama al comando ping (plataforma) y espera per_host_timeout en su propia lógica CLI."""
    system = platform.system()
    if system == "Windows":
        cmd = ["ping", "-n", "1", "-w", str(int(per_host_timeout * 1000)), host]
    elif system == "Darwin":
        # en macOS el -W no siempre existe, usamos -t (TTL) con 1 como aproximación
        cmd = ["ping", "-c", "1", "-t", "1", host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(int(max(1, per_host_timeout))), host]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        ret = await proc.wait()
        return ret == 0
    except Exception:
        return False

async def ping_host(host, per_host_timeout):
    """Wrapper seguro que aplica un timeout real por host."""
    try:
        return await asyncio.wait_for(ping_one_cmd(host, per_host_timeout), timeout=per_host_timeout + 0.5)
    except asyncio.TimeoutError:
        return False
    except Exception:
        return False

# ------------------ CHUNKED SWEEP ------------------
def chunked_iterable(iterable, size):
    """Generador que devuelve listas de tamaño 'size' desde iterable."""
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk

async def ping_sweep_chunked(network, chunk_size, per_host_timeout, per_subnet_timeout, concurrency):
    """
    Barrido seguro de 'network' (ipaddress.ip_network).
    - Envía pings en chunks paralelos de chunk_size.
    - Aplica timeout total per_subnet_timeout y timeout por host.
    - Usa semáforo global 'concurrency'.
    - Devuelve lista de IPs vivas (strings).
    """
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
            print(f"  - Timeout global por subnet alcanzado ({per_subnet_timeout}s). Abortando resto.")
            break

        tasks = [asyncio.create_task(worker(ip)) for ip in chunk]

        # procesar results conforme vayan completando para mostrar progreso
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
            # per-subnet timeout alcanzado durante as_completed; cancelar tareas pendientes
            for t in tasks:
                if not t.done():
                    t.cancel()
            print(f"  - Timeout global por subnet alcanzado durante chunk. Abortando resto.")
            break
        finally:
            # asegurar cancelación de tareas no finalizadas
            for t in tasks:
                if not t.done():
                    t.cancel()

        processed += len(chunk)
        pct = (processed / total * 100) if total else 100
        print(f"  - Progreso subnet: {processed}/{total} hosts ({pct:.1f}%), vivos hasta ahora: {len(alive)}")

    return sorted(set(alive), key=lambda s: tuple(int(x) for x in s.split(".")))

# ------------------ ARP PARSERS ------------------
def parse_arp_windows(output):
    entries = []
    for line in output.splitlines():
        m = re.search(r'^\s*(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-fA-F\-\:]{11,17})', line)
        if m:
            ip = m.group(1)
            mac = m.group(2).replace('-', ':').lower()
            entries.append((ip, mac))
    return entries

def parse_arp_unix(output):
    entries = []
    for line in output.splitlines():
        m = re.search(r'(?P<ip>\d{1,3}(?:\.\d{1,3}){3}).*(lladdr|at)\s+(?P<mac>[0-9a-fA-F:]{11,17})', line)
        if m:
            ip = m.group("ip")
            mac = m.group("mac").lower()
            entries.append((ip, mac))
            continue
        m2 = re.search(r'\((?P<ip>\d{1,3}(?:\.\d{1,3}){3})\)\s+at\s+(?P<mac>[0-9a-fA-F:]{11,17})', line)
        if m2:
            entries.append((m2.group("ip"), m2.group("mac").lower()))
            continue
        m3 = re.search(r'(?P<ip>\d{1,3}(?:\.\d{1,3}){3}).*(ether|at)\s+(?P<mac>[0-9a-fA-F:]{11,17})', line)
        if m3:
            entries.append((m3.group("ip"), m3.group("mac").lower()))
    return entries

def parse_arp_table_raw():
    entries = []
    system = platform.system()
    try:
        if system == "Windows":
            proc = subprocess.run(["arp", "-a"], capture_output=True, text=True, check=False)
            out = (proc.stdout or "") + (proc.stderr or "")
            entries = parse_arp_windows(out)
        else:
            try:
                proc = subprocess.run(["ip", "neigh"], capture_output=True, text=True, check=False)
                out = (proc.stdout or "") + (proc.stderr or "")
                if out.strip():
                    entries = parse_arp_unix(out)
                    if entries:
                        return entries
            except FileNotFoundError:
                pass
            proc2 = subprocess.run(["arp", "-a"], capture_output=True, text=True, check=False)
            out2 = (proc2.stdout or "") + (proc2.stderr or "")
            entries = parse_arp_unix(out2)
    except Exception:
        entries = []
    norm = {}
    for ip, mac in entries:
        if not mac:
            continue
        norm[ip] = mac.lower()
    return list(norm.items())

# ------------------ SEGMENTOS Y MUESTREO ------------------
def generate_segments_for_supernet(supernet, segment_prefix_len):
    if supernet.prefixlen <= segment_prefix_len:
        return list(supernet.subnets(new_prefix=segment_prefix_len))
    else:
        return [supernet]

def sample_ips_for_segment(segment, fixed_offsets=(1,128,254), random_count=5):
    hosts = list(segment.hosts())
    if not hosts:
        return []
    picks = []
    base_int = int(segment.network_address)
    for off in fixed_offsets:
        try:
            cand = ipaddress.ip_address(base_int + off)
            if cand in segment:
                picks.append(str(cand))
        except Exception:
            pass
    if len(hosts) > len(picks):
        remaining = [h for h in hosts if str(h) not in picks]
        if remaining:
            sample = random.sample(remaining, min(random_count, len(remaining)))
            picks.extend(str(x) for x in sample)
    seen = set()
    final = []
    for ip in picks:
        if ip not in seen:
            final.append(ip)
            seen.add(ip)
    return final

async def is_segment_active_by_probe(segment, random_count=SAMPLE_RANDOM_COUNT):
    ips = sample_ips_for_segment(segment, random_count=random_count)
    if not ips:
        return False, []
    tasks = [asyncio.create_task(ping_host(ip, DEFAULT_PER_HOST_TIMEOUT)) for ip in ips]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    alive = [ip for ip, ok in zip(ips, results) if ok is True]
    return (len(alive) > 0), alive

# ------------------ FLOW PRINCIPAL ------------------
def merge_ip_mac(alive_ips, arp_entries, allowed_networks):
    arp_map = dict(arp_entries)
    kept = {}
    for ip in alive_ips:
        try:
            ip_obj = ipaddress.ip_address(ip)
        except Exception:
            continue
        if not any(ip_obj in n for n in allowed_networks):
            continue
        kept[ip] = arp_map.get(ip)
    for ip, mac in arp_entries:
        try:
            ip_obj = ipaddress.ip_address(ip)
        except Exception:
            continue
        if any(ip_obj in n for n in allowed_networks):
            if ip not in kept:
                kept[ip] = mac
    return kept

def print_summary_and_save(kept_map, csv_name):
    print("\n---- RESULTADO FINAL (ejemplos) ----")
    ips_sorted = sorted(kept_map.keys(), key=lambda s: tuple(int(x) for x in s.split(".")))
    for ip in ips_sorted[:200]:
        print(f"{ip} -> {kept_map[ip] or '(sin MAC)'}")
    print(f"\nTotal únicas encontradas: {len(ips_sorted)}")
    with open(csv_name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ip", "mac"])
        for ip in ips_sorted:
            w.writerow([ip, kept_map[ip] or ""])
    print("CSV guardado en", csv_name)

async def scan_active_segments(active_segments, detailed_prefix, concurrency, max_addresses_per_sweep,
                               chunk_size, per_host_timeout, per_subnet_timeout, max_consecutive_empty):
    all_alive = []
    for seg in active_segments:
        if detailed_prefix and detailed_prefix > seg.prefixlen:
            subnets = list(seg.subnets(new_prefix=detailed_prefix))
            print(f"\nEscaneando {len(subnets)} subnets /{detailed_prefix} dentro de {seg} ...")
            consecutive_empty = 0
            for s in subnets:
                if s.num_addresses - 2 > max_addresses_per_sweep:
                    print(f"  - Omitiendo {s} (demasiado grande: {s.num_addresses} hosts).")
                    continue
                print(f"  - Sweep {s} (chunk_size={chunk_size}, per_host_timeout={per_host_timeout}, per_subnet_timeout={per_subnet_timeout})")
                alive = await ping_sweep_chunked(s, chunk_size=chunk_size, per_host_timeout=per_host_timeout,
                                                 per_subnet_timeout=per_subnet_timeout, concurrency=concurrency)
                if alive:
                    print(f"    => {len(alive)} vivos (ej: {alive[:8]})")
                    all_alive.extend(alive)
                    consecutive_empty = 0  # reiniciar contador al encontrar hosts
                else:
                    consecutive_empty += 1
                    print(f"    => 0 vivos en {s} (consecutivos vacíos: {consecutive_empty}/{max_consecutive_empty})")
                    if consecutive_empty >= max_consecutive_empty:
                        print(f"    => Se alcanzó {consecutive_empty} subnets vacías consecutivas. Saltando resto de subnets en {seg}.")
                        break
        else:
            # sweep directo del segmento entero (igual que antes)
            if seg.num_addresses - 2 > max_addresses_per_sweep:
                print(f"\nOmitiendo sweep directo de {seg} (demasiado grande: {seg.num_addresses} hosts).")
                continue
            print(f"\nPing sweep directo sobre {seg} (chunk_size={chunk_size}, per_host_timeout={per_host_timeout}) ...")
            alive = await ping_sweep_chunked(seg, chunk_size=chunk_size, per_host_timeout=per_host_timeout,
                                             per_subnet_timeout=per_subnet_timeout, concurrency=concurrency)
            print(f"  => {len(alive)} hosts vivos en {seg}")
            all_alive.extend(alive)
    return sorted(set(all_alive), key=lambda s: tuple(int(x) for x in s.split(".")))

def parse_args():
    p = argparse.ArgumentParser(description="Escaneo interno (RFC1918) con MACs via ARP y barrido chunked.")
    p.add_argument("--segment-prefix", type=int, default=ASSUME_SEGMENT_PREFIX, help="prefijo de segmento para descubrir (ej 16).")
    p.add_argument("--detailed-prefix", type=int, default=DETAILED_PREFIX, help="prefijo para escaneo detallado dentro del segmento (ej 24).")
    p.add_argument("--concurrency", type=int, default=CONCURRENCY, help="concurrency global para ping sweep.")
    p.add_argument("--sample-random", type=int, default=SAMPLE_RANDOM_COUNT, help="IPs aleatorias a muestrear por segmento.")
    p.add_argument("--max-sweep", type=int, default=MAX_ADDRESSES_PER_SWEEP, help="max direcciones a barrer por sweep (seguridad).")
    p.add_argument("--no-arp", action="store_true", help="no leer ARP al final (solo pings).")
    p.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="hosts paralelos por chunk en barrido.")
    p.add_argument("--per-host-timeout", type=float, default=DEFAULT_PER_HOST_TIMEOUT, help="timeout (s) por host.")
    p.add_argument("--per-subnet-timeout", type=float, default=DEFAULT_PER_SUBNET_TIMEOUT, help="timeout (s) máximo por subnet.")
    p.add_argument("--max-consecutive-empty", type=int, default=5, help="máx subnets consecutivas vacías antes de saltar al siguiente /16 (por defecto 5).")
    return p.parse_args()

def main():
    args = parse_args()

    global CONCURRENCY, SAMPLE_RANDOM_COUNT
    CONCURRENCY = args.concurrency
    SAMPLE_RANDOM_COUNT = args.sample_random

    try:
        local_super = get_local_supernet()
    except Exception as e:
        print("ERROR:", e)
        sys.exit(1)

    print("Local supernet detectado:", local_super)
    segments = generate_segments_for_supernet(local_super, args.segment_prefix)
    # --- FILTRO PERSONALIZADO PARA 10.100.x.x → 10.119.x.x ---
    filtered = []
    for seg in segments:
        # convertimos el segmento a int para comparar
        first_octet = int(str(seg.network_address).split('.')[1])
        if 100 <= first_octet <= 119:
            filtered.append(seg)
    segments = filtered
    print(f"Filtrados {len(segments)} segmentos en rango 10.100.x.x - 10.119.x.x")
    # ----------------------------------------------------------

    print(f"Generados {len(segments)} segmentos /{args.segment_prefix} a evaluar.")

    print("\nLeyendo tabla ARP local (para ayudar a detección)...")
    arp_entries = parse_arp_table_raw()
    arp_entries = [(ip, mac) for ip, mac in arp_entries if ipaddress.ip_address(ip) in local_super]
    print(f"Entradas ARP locales dentro de {local_super}: {len(arp_entries)} (ej: {arp_entries[:6]})")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    active_segments = []
    try:
        for seg in segments:
            arp_active = any(ipaddress.ip_address(ip) in seg for ip, _ in arp_entries)
            probe_active = False
            if not args.no_arp:
                try:
                    probe_active, _ = loop.run_until_complete(is_segment_active_by_probe(seg, random_count=SAMPLE_RANDOM_COUNT))
                except Exception as e:
                    print("WARN: probe falló para", seg, "->", e)
            if arp_active or probe_active:
                active_segments.append(seg)
                reason = []
                if arp_active: reason.append("arp")
                if probe_active: reason.append("probe")
                print(f"[ACTIVO] {seg}  (detectado por: {', '.join(reason)})")
            else:
                print(f"[INACTIVO] {seg}")
    finally:
        pass

    if not active_segments:
        print("No se detectaron segmentos activos. Terminando.")
        return

    loop2 = asyncio.new_event_loop()
    asyncio.set_event_loop(loop2)
    try:
        alive_ips = loop2.run_until_complete(scan_active_segments(active_segments,
                                                          args.detailed_prefix,
                                                          args.concurrency,
                                                          args.max_sweep,
                                                          args.chunk_size,
                                                          args.per_host_timeout,
                                                          args.per_subnet_timeout,
                                                          args.max_consecutive_empty))


    finally:
        loop2.close()

    print(f"\nHosts vivos por ping detectados: {len(alive_ips)} (ej: {alive_ips[:20]})")

    arp_after = []
    if not args.no_arp:
        print("\nLeyendo tabla ARP local nuevamente para asociar MACs (ip neigh / arp -a)...")
        arp_after = parse_arp_table_raw()
        arp_after = [(ip, mac) for ip, mac in arp_after if ipaddress.ip_address(ip) in local_super]
        print(f"Entradas ARP encontradas ahora: {len(arp_after)} (ej: {arp_after[:6]})")

    allowed_networks = [local_super]
    kept_map = merge_ip_mac(alive_ips, arp_after if arp_after else arp_entries, allowed_networks)

    csv_name = f"{CSV_NAME_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    segment_len = args.segment_prefix
    with open(csv_name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["segment", "ip", "mac"])
        for ip in sorted(kept_map.keys(), key=lambda s: tuple(int(x) for x in s.split("."))):
            ip_obj = ipaddress.ip_address(ip)
            seg = None
            for s in segments:
                if ip_obj in s:
                    seg = s
                    break
            seg_str = str(seg) if seg else ""
            w.writerow([seg_str, ip, kept_map[ip] or ""])

    print_summary_and_save(kept_map, csv_name)

if __name__ == "__main__":
    main()
