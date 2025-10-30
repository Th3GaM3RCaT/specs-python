#!/usr/bin/env python3
"""
network_scanner_with_mac.py

Escaneo segmentado + asociación IP -> MAC (usa ARP local).
Seguro: solo opera dentro de redes privadas RFC1918.
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
from datetime import datetime
import random

# ---------------- CONFIG DEFAULTS ----------------
CONCURRENCY = 300
ASSUME_SEGMENT_PREFIX = 16    # tamaño del segmento para detectar (p. ej. /16 -> 10.x.0.0/16)
DETAILED_PREFIX = 24          # prefijo para escaneo detallado dentro de segmento (p. ej. /24). Si = segment size, escanea el segmento entero
SAMPLE_RANDOM_COUNT = 5       # muestras aleatorias por segmento para detección
MAX_ADDRESSES_PER_SWEEP = 4096  # por subnet para sweep detallado (evita sweeps enormes)
PING_TIMEOUT_SECONDS = 1
CSV_NAME_PREFIX = "scan_rfc1918"
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

# ------------------ PING (async) ------------------
async def ping_one(host):
    system = platform.system()
    if system == "Windows":
        cmd = ["ping", "-n", "1", "-w", str(int(PING_TIMEOUT_SECONDS * 1000)), host]
    elif system == "Darwin":
        cmd = ["ping", "-c", "1", "-t", "1", host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(int(PING_TIMEOUT_SECONDS)), host]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd,
                                                    stdout=asyncio.subprocess.DEVNULL,
                                                    stderr=asyncio.subprocess.DEVNULL)
        ret = await proc.wait()
        return ret == 0
    except Exception:
        return False

async def ping_sweep(network, concurrency=200):
    sem = asyncio.Semaphore(concurrency)
    alive = []

    async def worker(ip):
        async with sem:
            ok = await ping_one(str(ip))
            if ok:
                alive.append(str(ip))

    tasks = [asyncio.create_task(worker(ip)) for ip in network.hosts()]
    if not tasks:
        return alive
    await asyncio.gather(*tasks)
    return alive

# ------------------ ARP PARSERS ------------------
def parse_arp_windows(output):
    entries = []
    for line in output.splitlines():
        # Formato típico:  10.0.0.1           00-11-22-33-44-55     dynamic
        m = re.search(r'^\s*(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-fA-F\-\:]{11,17})', line)
        if m:
            ip = m.group(1)
            mac = m.group(2).replace('-', ':').lower()
            entries.append((ip, mac))
    return entries

def parse_arp_unix(output):
    entries = []
    # ip neigh output (linux) like: 10.0.0.1 dev eth0 lladdr 00:11:22:33:44:55 REACHABLE
    for line in output.splitlines():
        m = re.search(r'(?P<ip>\d{1,3}(?:\.\d{1,3}){3}).*(lladdr|at)\s+(?P<mac>[0-9a-fA-F:]{11,17})', line)
        if m:
            ip = m.group("ip")
            mac = m.group("mac").lower()
            entries.append((ip, mac))
            continue
        # fallback for classic arp -a: (10.0.0.1) at 00:11:22:33:44:55 [ether] on eth0
        m2 = re.search(r'\((?P<ip>\d{1,3}(?:\.\d{1,3}){3})\)\s+at\s+(?P<mac>[0-9a-fA-F:]{11,17})', line)
        if m2:
            entries.append((m2.group("ip"), m2.group("mac").lower()))
            continue
        # another fallback: "10.0.0.1 ether 00:11:22:33:44:55 CACHED"
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
            # intentar ip neigh primero (Linux)
            try:
                proc = subprocess.run(["ip", "neigh"], capture_output=True, text=True, check=False)
                out = (proc.stdout or "") + (proc.stderr or "")
                if out.strip():
                    entries = parse_arp_unix(out)
                    if entries:
                        return entries
            except FileNotFoundError:
                pass
            # fallback arp -a
            proc2 = subprocess.run(["arp", "-a"], capture_output=True, text=True, check=False)
            out2 = (proc2.stdout or "") + (proc2.stderr or "")
            entries = parse_arp_unix(out2)
    except Exception:
        # en caso de error, devolver lista vacía
        entries = []
    # normalizar MACs y devolver únicos (manteniendo última mac vista)
    norm = {}
    for ip, mac in entries:
        if not mac:
            continue
        macn = mac.lower()
        norm[ip] = macn
    return list(norm.items())

# ------------------ SEGMENTOS Y MUESTREO ------------------
def generate_segments_for_supernet(supernet, segment_prefix_len):
    # genera subnets del tamaño indicado dentro de supernet
    if supernet.prefixlen <= segment_prefix_len:
        return list(supernet.subnets(new_prefix=segment_prefix_len))
    else:
        # si el supernet ya es más pequeño que el segment size, devolver tal cual
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
    # aleatorios sin repetir
    if len(hosts) > len(picks):
        remaining = [h for h in hosts if str(h) not in picks]
        if remaining:
            sample = random.sample(remaining, min(random_count, len(remaining)))
            picks.extend(str(x) for x in sample)
    # dedupe
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
    tasks = [asyncio.create_task(ping_one(ip)) for ip in ips]
    results = await asyncio.gather(*tasks)
    alive = [ip for ip, ok in zip(ips, results) if ok]
    return (len(alive) > 0), alive

# ------------------ FLOW PRINCIPAL ------------------
def merge_ip_mac(alive_ips, arp_entries, allowed_networks):
    """
    Crea dict ip->mac:
      - Si IP tiene MAC en arp_entries -> usarla.
      - Si no, poner None.
    Filtra por allowed_networks.
    """
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
    # Además incorporar ARP entries que no fueron ping-eadas pero están en networks
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
    # guardar CSV
    with open(csv_name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ip", "mac"])
        for ip in ips_sorted:
            w.writerow([ip, kept_map[ip] or ""])
    print("CSV guardado en", csv_name)

async def scan_active_segments(active_segments, detailed_prefix, concurrency, max_addresses_per_sweep):
    all_alive = []
    for seg in active_segments:
        # decidir si hacer sweeps por subnets (/24) o el segmento entero
        if detailed_prefix and detailed_prefix > seg.prefixlen:
            subnets = list(seg.subnets(new_prefix=detailed_prefix))
            print(f"\nEscaneando {len(subnets)} subnets /{detailed_prefix} dentro de {seg} ...")
            for s in subnets:
                if s.num_addresses - 2 > max_addresses_per_sweep:
                    # omitir subnets muy grandes por seguridad
                    print(f"  - Omitiendo {s} (demasiado grande: {s.num_addresses} hosts).")
                    continue
                alive = await ping_sweep(s, concurrency=concurrency)
                if alive:
                    print(f"  - {s}: {len(alive)} vivos (ej: {alive[:6]})")
                    all_alive.extend(alive)
        else:
            # sweep del segmento entero si no es enorme
            if seg.num_addresses - 2 > max_addresses_per_sweep:
                print(f"\nOmitiendo sweep directo de {seg} (demasiado grande: {seg.num_addresses} hosts).")
                continue
            print(f"\nPing sweep directo sobre {seg} (num={seg.num_addresses}) ...")
            alive = await ping_sweep(seg, concurrency=concurrency)
            print(f"  => {len(alive)} hosts vivos en {seg}")
            all_alive.extend(alive)
    # dedupe y retornar
    return sorted(set(all_alive), key=lambda s: tuple(int(x) for x in s.split(".")))

def parse_args():
    p = argparse.ArgumentParser(description="Escaneo interno (RFC1918) con MACs via ARP.")
    p.add_argument("--segment-prefix", type=int, default=ASSUME_SEGMENT_PREFIX, help="prefijo de segmento para descubrir (ej 16).")
    p.add_argument("--detailed-prefix", type=int, default=DETAILED_PREFIX, help="prefijo para escaneo detallado dentro del segmento (ej 24).")
    p.add_argument("--concurrency", type=int, default=CONCURRENCY, help="concurrency para ping sweep.")
    p.add_argument("--sample-random", type=int, default=SAMPLE_RANDOM_COUNT, help="IPs aleatorias a muestrear por segmento.")
    p.add_argument("--max-sweep", type=int, default=MAX_ADDRESSES_PER_SWEEP, help="max direcciones a barrer por sweep (seguridad).")
    p.add_argument("--no-arp", action="store_true", help="no leer ARP al final (solo pings).")
    return p.parse_args()

def main():
    args = parse_args()

    # ajustar globals desde args
    global CONCURRENCY, SAMPLE_RANDOM_COUNT
    CONCURRENCY = args.concurrency
    SAMPLE_RANDOM_COUNT = args.sample_random

    try:
        local_super = get_local_supernet()
    except Exception as e:
        print("ERROR:", e)
        sys.exit(1)

    print("Local supernet detectado:", local_super)
    # generar segmentos (por ejemplo /16 dentro de 10.0.0.0/8)
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

    # ETAPA 1: detectar segmentos activos mediante muestreo + ARP local
    print("\nLeyendo tabla ARP local (para ayudar a detección)...")
    arp_entries = parse_arp_table_raw()
    # filtrar arp entries por pertenencia al supernet (por seguridad)
    arp_entries = [(ip, mac) for ip, mac in arp_entries if ipaddress.ip_address(ip) in local_super]

    print(f"Entradas ARP locales dentro de {local_super}: {len(arp_entries)} (ej: {arp_entries[:6]})")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    active_segments = []
    try:
        for seg in segments:
            # check por ARP
            arp_active = any(ipaddress.ip_address(ip) in seg for ip, _ in arp_entries)
            probe_active = False
            probe_examples = []
            if not args.no_arp:
                # probe de muestreo (async)
                try:
                    probe_active, probe_examples = loop.run_until_complete(is_segment_active_by_probe(seg, random_count=SAMPLE_RANDOM_COUNT))
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
        # no cerramos event loop si lo vamos a usar despues; lo reusamos abajo
        pass

    if not active_segments:
        print("No se detectaron segmentos activos. Terminando.")
        return

    # ETAPA 2: escaneo detallado solo en segmentos activos
    loop2 = asyncio.new_event_loop()
    asyncio.set_event_loop(loop2)
    try:
        alive_ips = loop2.run_until_complete(scan_active_segments(active_segments,
                                                                  args.detailed_prefix,
                                                                  args.concurrency,
                                                                  args.max_sweep))
    finally:
        loop2.close()

    print(f"\nHosts vivos por ping detectados: {len(alive_ips)} (ej: {alive_ips[:20]})")

    # ETAPA 3: leer ARP otra vez (para asociar MACs)
    arp_after = []
    if not args.no_arp:
        print("\nLeyendo tabla ARP local nuevamente para asociar MACs (ip neigh / arp -a)...")
        arp_after = parse_arp_table_raw()
        arp_after = [(ip, mac) for ip, mac in arp_after if ipaddress.ip_address(ip) in local_super]
        print(f"Entradas ARP encontradas ahora: {len(arp_after)} (ej: {arp_after[:6]})")

    # Combinar pings + arp
    allowed_networks = [local_super]
    kept_map = merge_ip_mac(alive_ips, arp_after if arp_after else arp_entries, allowed_networks)

    # Guardar CSV con ip, mac y (si quieres) segment -> lo podemos derivar
    csv_name = f"{CSV_NAME_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    # Para incluir segmento, derivamos el segmento /segment_prefix donde cae la IP
    segment_len = args.segment_prefix
    with open(csv_name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["segment", "ip", "mac"])
        for ip in sorted(kept_map.keys(), key=lambda s: tuple(int(x) for x in s.split("."))):
            ip_obj = ipaddress.ip_address(ip)
            # localizar segmento base
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
