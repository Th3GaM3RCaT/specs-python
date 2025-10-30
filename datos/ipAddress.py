#!/usr/bin/env python3
"""
network_scanner.py

Escaneo en dos etapas:
  1) Descubrir segmentos (ej: /16) activos mediante muestreo + ARP.
  2) Escanear en detalle solo los segmentos activos (ej: /24).

Configuración via constantes al inicio.
"""

import argparse
import asyncio
import ipaddress
import platform
import random
import socket
import subprocess
import re
from datetime import datetime
import csv
import sys

# ------------------ CONFIG ------------------
ASSUME_CIDR = "/16"            # fallback cuando solo hay IP local
BASE_NETWORKS_AUTO = True      # si True y la IP local empieza por 10. => añade 10.0.0.0/8
AUTO_ADD_10_OVERALL = True
SEGMENT_PREFIX_LEN = 16        # tamaño del "segmento" que queremos detectar (ej 16 -> 10.101.0.0/16)
DETAILED_PREFIX_LEN = 24       # cuando un segmento está activo, escanear subredes de este prefijo (ej 24)
SAMPLE_FIXED_OFFSETS = [1, 128, 254]   # offsets fijos dentro de cada segmento a probar
SAMPLE_RANDOM_COUNT = 5        # cantidad de direcciones aleatorias muestreadas por segmento
CONCURRENCY = 300
MAX_ADDRESSES_FOR_DIRECT_SWEEP = 50000   # evita sweeps directos enormes (por seguridad)
MAX_ADDRESSES_PER_SUBNET_SWEEP = 4096    # si un detalle/subnet es mayor que esto, se omite
PING_TIMEOUT_SECONDS = 1       # timeout que usamos indirectamente con ping CLI
CSV_OUTPUT = True
CSV_NAME_PREFIX = "scan_clean"
# -------------------------------------------

def get_local_ip():
    """Devuelve IP local usada para salida (no contacta a internet realmente)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

def parse_network_from_cidr(text):
    try:
        return ipaddress.ip_network(text, strict=False)
    except Exception:
        return None

def get_candidate_networks():
    """
    Intenta detectar redes conectadas leyendo tabla de rutas (ip route, route print, netstat).
    Si no encuentra nada, usa IP local + ASSUME_CIDR y opcionalmente 10.0.0.0/8.
    Devuelve lista de ipaddress.IPv4Network
    """
    nets = set()

    # ip route (Linux)
    try:
        proc = subprocess.run(["ip", "route"], capture_output=True, text=True, check=False)
        out = (proc.stdout or "") + (proc.stderr or "")
        for m in re.finditer(r'(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2})', out):
            n = parse_network_from_cidr(m.group(1))
            if n:
                nets.add(n)
    except FileNotFoundError:
        pass
    except Exception:
        pass

    # route print (Windows)
    try:
        if not nets:
            proc = subprocess.run(["route", "print"], capture_output=True, text=True, check=False)
            out = (proc.stdout or "") + (proc.stderr or "")
            for line in out.splitlines():
                # buscar líneas con destino y máscara
                parts = re.split(r'\s+', line.strip())
                if len(parts) >= 3 and re.match(r'^\d+\.\d+\.\d+\.\d+$', parts[0]) and re.match(r'^\d+\.\d+\.\d+\.\d+$', parts[1]):
                    dst, mask = parts[0], parts[1]
                    try:
                        pfx = ipaddress.IPv4Network(f"0.0.0.0/{mask}").prefixlen
                        n = ipaddress.ip_network(f"{dst}/{pfx}", strict=False)
                        nets.add(n)
                    except Exception:
                        pass
    except Exception:
        pass

    # netstat -rn fallback
    try:
        if not nets:
            proc = subprocess.run(["netstat", "-rn"], capture_output=True, text=True, check=False)
            out = (proc.stdout or "") + (proc.stderr or "")
            for m in re.finditer(r'(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3})', out):
                dst, maybe_mask = m.group(1), m.group(2)
                # heurística: si dst parece red con .0 agregamos ASSUME_CIDR
                if dst.endswith('.0'):
                    try:
                        n = ipaddress.ip_network(dst + ASSUME_CIDR, strict=False)
                        nets.add(n)
                    except Exception:
                        pass
    except Exception:
        pass

    if not nets:
        local_ip = get_local_ip()
        try:
            nets.add(ipaddress.ip_network(local_ip + ASSUME_CIDR, strict=False))
        except Exception:
            pass
        if AUTO_ADD_10_OVERALL and local_ip.startswith("10."):
            try:
                nets.add(ipaddress.ip_network("10.0.0.0/8"))
                print("DEBUG: Añadida 10.0.0.0/8 automáticamente (AUTO_ADD_10_OVERALL=True).")
            except Exception:
                pass

    nets_list = sorted(nets, key=lambda n: (int(n.network_address), n.prefixlen))
    print("Redes detectadas (candidate networks):")
    for n in nets_list:
        print("  -", n)
    return nets_list

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
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        ret = await proc.wait()
        return ret == 0
    except Exception:
        return False

async def ping_sweep(network, concurrency=200):
    """
    Hace ping a todos los hosts de 'network' (ipaddress.ip_network).
    """
    sem = asyncio.Semaphore(concurrency)
    alive = []

    async def worker(ip):
        async with sem:
            ok = await ping_one(str(ip))
            if ok:
                alive.append(str(ip))

    tasks = []
    for ip in network.hosts():
        tasks.append(asyncio.create_task(worker(ip)))
    if not tasks:
        return alive
    await asyncio.gather(*tasks)
    return alive

# ------------------ ARP ------------------
def parse_arp_table_raw():
    """Parsea salida de arp -a en multiplataforma y devuelve lista (ip, mac_or_None)."""
    try:
        proc = subprocess.run(["arp", "-a"], capture_output=True, text=True, check=False)
        out = (proc.stdout or "") + (proc.stderr or "")
    except Exception:
        out = ""
    lines = out.splitlines()
    entries = []
    for line in lines:
        m = re.search(r'\((?P<ip>\d{1,3}(?:\.\d{1,3}){3})\)\s+at\s+(?P<mac>[0-9a-fA-F:]{11,17})', line)
        if m:
            entries.append((m.group("ip"), m.group("mac").lower()))
            continue
        m2 = re.search(r'^(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\s+(?P<mac>[0-9a-fA-F:-]{11,17})', line.strip())
        if m2:
            mac = m2.group("mac").replace('-', ':').lower()
            entries.append((m2.group("ip"), mac))
            continue
        m3 = re.search(r'(?P<ip>\d{1,3}(?:\.\d{1,3}){3}).*(?P<mac>[0-9a-fA-F:]{11,17})', line)
        if m3:
            entries.append((m3.group("ip"), m3.group("mac").replace('-', ':').lower()))
            continue
        m4 = re.search(r'(?P<ip>\d{1,3}(?:\.\d{1,3}){3})', line)
        if m4:
            entries.append((m4.group("ip"), None))
    return entries

# ------------------ SEGMENTOS y DESCUBRIMIENTO ------------------
def generate_segments_from_networks(networks, segment_prefix_len):
    """
    Dado un conjunto de networks (ej: 10.0.0.0/8 o 10.100.0.0/16), genera subredes de tamaño segment_prefix_len.
    """
    segments = []
    for net in networks:
        if net.prefixlen <= segment_prefix_len:
            segments.extend(list(net.subnets(new_prefix=segment_prefix_len)))
        else:
            # si la red detectada ya es más pequeña que el segmento, la tomamos tal cual
            segments.append(net)
    return segments

def sample_ips_for_segment(segment_net, fixed_offsets=SAMPLE_FIXED_OFFSETS, random_count=SAMPLE_RANDOM_COUNT):
    """
    Devuelve lista de direcciones IP (strings) a usar como muestra para detectar si el segmento está activo.
    Incluye offsets fijos (ej .1, .128, .254) relativos al primer /24 del segmento, y N aleatorias distribuidas.
    """
    hosts = list(segment_net.hosts())
    if not hosts:
        return []
    picks = []
    # Offsets fijos: tomar a partir del primer host como base
    base_int = int(segment_net.network_address)
    for off in fixed_offsets:
        candidate = ipaddress.ip_address(base_int + off)
        if candidate in segment_net and candidate.is_global:
            picks.append(str(candidate))
        else:
            # fallback a primer host
            picks.append(str(hosts[0]))
    # picks aleatorios
    if len(hosts) > len(picks):
        # elegir sin repetición
        remaining = set(hosts) - {ipaddress.ip_address(p) for p in picks}
        if remaining:
            sample = random.sample(list(remaining), min(random_count, len(remaining)))
            picks.extend(str(x) for x in sample)
    # dedupe
    seen = set()
    final = []
    for ip in picks:
        if ip not in seen:
            final.append(ip)
            seen.add(ip)
    return final

async def is_segment_active_by_probe(segment_net):
    """
    Hace pings a la muestra de ips del segmento. Si cualquiera responde -> activo.
    """
    sample_ips = sample_ips_for_segment(segment_net)
    if not sample_ips:
        return False, []
    sem = asyncio.Semaphore(min(CONCURRENCY, len(sample_ips)))
    alive = []

    async def w(ip):
        async with sem:
            ok = await ping_one(ip)
            if ok:
                alive.append(ip)

    tasks = [asyncio.create_task(w(ip)) for ip in sample_ips]
    await asyncio.gather(*tasks)
    return (len(alive) > 0), alive

def is_segment_active_by_arp(segment_net, arp_entries):
    """
    Revisa la tabla ARP local: si hay alguna entrada perteneciente al segmento -> activo.
    """
    for ip, mac in arp_entries:
        try:
            ip_obj = ipaddress.ip_address(ip)
        except Exception:
            continue
        if ip_obj in segment_net:
            return True, (ip, mac)
    return False, None

# ------------------ FILTRADO Y CONSOLIDACION ------------------
def combine_alive_from_scans(alive_lists):
    """Combina listas de hosts vivos evitando duplicados y devuelve lista ordenada."""
    s = set()
    for lst in alive_lists:
        s.update(lst)
    # ordenar numéricamente por octetos
    return sorted(s, key=lambda s: tuple(int(x) for x in s.split('.')))

def filter_entries_by_networks(entries, networks):
    """Filtra entradas arp según pertenencia a al menos una de las networks (lista)."""
    kept = {}
    discarded = []
    for ip_str, mac in entries:
        reason = None
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except Exception:
            reason = "IP inválida"
            discarded.append((ip_str, mac, reason))
            continue
        if any(ip_obj == net.broadcast_address for net in networks if hasattr(net, "broadcast_address")):
            reason = "broadcast IP"
            discarded.append((ip_str, mac, reason))
            continue
        if ip_obj.is_multicast or ip_obj.is_unspecified or ip_obj.is_loopback:
            reason = "multicast/unspecified/loopback"
            discarded.append((ip_str, mac, reason))
            continue
        if not any((ip_obj in net) for net in networks):
            reason = "fuera de redes detectadas"
            discarded.append((ip_str, mac, reason))
            continue
        mac_norm = mac.lower() if mac else None
        if ip_str not in kept:
            kept[ip_str] = mac_norm
        else:
            if kept[ip_str] is None and mac_norm:
                kept[ip_str] = mac_norm
    return kept, discarded

# ------------------ MAIN FLOW ------------------
def scan(args):
    networks = get_candidate_networks()
    segments = generate_segments_from_networks(networks, args.segment_prefix_len)

    print(f"\nGenerados {len(segments)} segmentos de tamaño /{args.segment_prefix_len} para evaluar.")
    arp_entries = parse_arp_table_raw()

    # etapa 1: descubrimiento (mezcla ARP + muestreo ping)
    active_segments = []
    probes_info = {}  # segmento -> ejemplo hosts vivos / arp encontrado
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        for seg in segments:
            # chequeo ARP rápido
            arp_active, example = is_segment_active_by_arp(seg, arp_entries)
            probe_alive = []
            detected_by = []
            if arp_active:
                detected_by.append("arp")
                probes_info[str(seg)] = {"arp_example": example}

            # probe de muestreo (async)
            if not args.skip_probe:
                try:
                    active_by_probe, alive_list = loop.run_until_complete(is_segment_active_by_probe(seg))
                    if active_by_probe:
                        detected_by.append("probe")
                        probe_alive = alive_list
                except Exception as e:
                    # no bloquear en caso de error de probe
                    print("WARN: probe fallo para", seg, "->", e)
            if detected_by:
                active_segments.append(seg)
                probes_info[str(seg)] = probes_info.get(str(seg), {})
                probes_info[str(seg)]["detected_by"] = detected_by
                if probe_alive:
                    probes_info[str(seg)]["probe_alive_example"] = probe_alive
                print(f"[ACTIVO] {seg}  (detectado por: {', '.join(detected_by)})")
            else:
                print(f"[INACTIVO] {seg}")
    finally:
        loop.close()

    if not active_segments:
        print("No se detectaron segmentos activos. Revisa accesos/rutas/ARP.")
        return

    # etapa 2: escaneo detallado de segmentos activos
    all_alive = []
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        for seg in active_segments:
            # Si el segmento tiene muchas direcciones y el usuario quiere detallar por subnets:
            num_addresses_seg = seg.num_addresses
            if args.detailed_prefix_len and args.detailed_prefix_len > seg.prefixlen:
                # generar subredes detalladas dentro del segmento
                subnets = list(seg.subnets(new_prefix=args.detailed_prefix_len))
                print(f"\nEscaneando subredes /{args.detailed_prefix_len} dentro de {seg} -> {len(subnets)} subredes.")
                for s in subnets:
                    if s.num_addresses - 2 > args.max_subnet_sweep:
                        print(f"  - Omitiendo sweep de {s} (demasiado grande: {s.num_addresses} hosts).")
                        continue
                    try:
                        print(f"  - Ping sweep {s} ...")
                        alive = loop.run_until_complete(ping_sweep(s, concurrency=args.concurrency))
                        if alive:
                            print(f"    => {len(alive)} hosts vivos (ej: {alive[:8]})")
                            all_alive.extend(alive)
                    except Exception as e:
                        print("    Errored sweep:", e)
            else:
                # hacer sweep del segmento entero (si no demasiado grande)
                if num_addresses_seg > args.max_direct_sweep:
                    print(f"\nOmitiendo sweep directo de {seg} (demasiado grande: {num_addresses_seg} direcciones).")
                    continue
                print(f"\nPing sweep directo sobre {seg} ... (num={num_addresses_seg})")
                try:
                    alive = loop.run_until_complete(ping_sweep(seg, concurrency=args.concurrency))
                    print(f"  => {len(alive)} hosts vivos (ej: {alive[:8]})")
                    all_alive.extend(alive)
                except Exception as e:
                    print("  Sweep directo falló:", e)
    finally:
        loop.close()

    combined_alive = combine_alive_from_scans([all_alive])
    print("\nHosts vivos combinados:", len(combined_alive))
    if combined_alive:
        print("Ejemplos:", combined_alive[:20])

    # componer reporte final mezclando ARP y alive pings
    kept, discarded = filter_and_merge_results(arp_entries, combined_alive, networks)

    print_report(kept, discarded)

    if args.csv and kept:
        csv_name = f"{CSV_NAME_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            with open(csv_name, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["ip", "mac"])
                for ip in sorted(kept.keys(), key=lambda s: tuple(int(x) for x in s.split("."))):
                    w.writerow([ip, kept[ip] or ""])
            print("CSV guardado en", csv_name)
        except Exception as e:
            print("No se pudo guardar CSV:", e)

def filter_and_merge_results(arp_entries, alive_list, networks):
    """
    Crea dict kept donde:
      - Todas las IPs 'alive' entran con MAC si existe en ARP.
      - Todas las entradas ARP dentro de networks se incorporan también.
    Devuelve (kept, discarded) usando filter_entries_by_networks para ARP.
    """
    # empezar por ARP filtrado
    arp_kept, discarded = filter_entries_by_networks(arp_entries, networks)
    # añadir hosts alive (si no están en arp_kept se agregan con None MAC)
    for ip in alive_list:
        if ip not in arp_kept:
            try:
                # chequear pertenencia a networks
                ip_obj = ipaddress.ip_address(ip)
                if any(ip_obj in n for n in networks):
                    arp_kept[ip] = None
            except Exception:
                pass
    return arp_kept, discarded

def print_report(kept, discarded):
    print("\n---- RESULTADOS FILTRADOS ----")
    if not kept:
        print("No se encontró ninguna IP válida con MAC dentro de las redes detectadas.")
    else:
        for ip in sorted(kept.keys(), key=lambda s: tuple(int(x) for x in s.split("."))):
            mac = kept[ip] or "(sin MAC)"
            print(f"{ip} -> {mac}")
    print(f"\nTotal válidas: {len(kept)}")
    print("\n---- ENTRADAS DESCARTADAS (ejemplos) ----")
    for ip, mac, reason in discarded[:40]:
        print(f"{ip} -> {mac or '(no mac)'}  : {reason}")
    print(f"\nTotal descartadas: {len(discarded)}")

# ------------------ CLI ------------------
def parse_args():
    p = argparse.ArgumentParser(description="Escaneo segmentado en dos etapas (detección + escaneo detallado).")
    p.add_argument("--segment-prefix-len", type=int, default=SEGMENT_PREFIX_LEN, help="prefijo de segmento para descubrimiento (ej 16).")
    p.add_argument("--detailed-prefix-len", type=int, default=DETAILED_PREFIX_LEN, help="prefijo para escaneo detallado dentro de segmento (ej 24).")
    p.add_argument("--sample-random-count", type=int, default=SAMPLE_RANDOM_COUNT, help="IPs aleatorias a muestrear por segmento.")
    p.add_argument("--concurrency", type=int, default=CONCURRENCY, help="concurrency para ping sweep.")
    p.add_argument("--max-direct-sweep", type=int, default=MAX_ADDRESSES_FOR_DIRECT_SWEEP, help="max addresses para sweep directo del segmento.")
    p.add_argument("--max-subnet-sweep", type=int, default=MAX_ADDRESSES_PER_SUBNET_SWEEP, help="max addresses para sweep por subnet detallada.")
    p.add_argument("--csv", action="store_true", default=CSV_OUTPUT, help="guardar CSV con resultados filtrados.")
    p.add_argument("--skip-probe", action="store_true", help="no hacer probes de muestreo (usar solo ARP para detection).")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    # aplicar valores dinámicos
    SAMPLE_RANDOM_COUNT = args.sample_random_count
    CONCURRENCY = args.concurrency

    try:
        scan(args)
    except KeyboardInterrupt:
        print("\nInterrumpido por usuario.")
        sys.exit(1)
