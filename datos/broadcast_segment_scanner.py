#!/usr/bin/env python3

import time

# Inicio del contador lo más arriba posible
start_time = time.time()
"""
broadcast_segment_scanner.py

Escáner orientado a segmentos RFC1918 usando probes basados en broadcast/multicast
(SSDP / mDNS) para detectar rápidamente qué subredes (por ejemplo /24) dentro de un
/16 contienen hosts. Mantiene los filtros que veníamos usando (limitar a RFC1918,
limitar a un rango de segundos octetos 10.100.x.x-10.119.x.x por defecto) y en caso
de no obtener respuestas usa un fallback basado en ping chunked que ya conocemos.

Salida: CSV con columnas segment, ip, mac y resúmenes por consola.

NOTAS:
 - Las probes SSDP/mDNS funcionan sólo en L2 (misma VLAN). Si el segmento está en otra VLAN
   y no permites directed-broadcast, no verás respuestas.
 - Para asociar MACs se vuelve a leer la tabla ARP (ip neigh / arp -a).
 - Puede ejecutarse sin root; sin embargo, para ciertos broadcasts o lectura avanzada
   de ARP en algunos sistemas puede requerirse privilegios.

Uso ejemplo:
  python3 broadcast_segment_scanner.py --start 100 --end 119 --segment-prefix 16 --detailed-prefix 24

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
import select
import time
import random
from datetime import datetime
from itertools import islice

# ------------------ DEFAULTS ------------------
DEFAULT_SEGMENT_PREFIX = 16   # genera /16 dentro del supernet local (ej 10.0.0.0/8 -> 10.x.0.0/16)
DEFAULT_DETAILED = 24         # dentro de cada /16, escanea /24 por defecto
DEFAULT_CHUNK_SIZE = 512
DEFAULT_PER_HOST_TIMEOUT = 0.8
DEFAULT_PER_SUBNET_TIMEOUT = 8.0
DEFAULT_CONCURRENCY = 512
DEFAULT_SAMPLE_RANDOM = 5
DEFAULT_MAX_SWEEP = 4096
DEFAULT_MAX_CONSEC_EMPTY = 2
DEFAULT_START_SECOND = 100
DEFAULT_END_SECOND = 119
CSV_PREFIX = "broadcast_scan"

SSDP_MSEARCH = '\r\n'.join([
    'M-SEARCH * HTTP/1.1',
    'HOST:239.255.255.250:1900',
    'MAN:"ssdp:discover"',
    'MX:2',
    'ST:ssdp:all',
    '', ''
]).encode('utf-8')

MDNS_SIMPLE = b"\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00"  # placeholder simple

# ------------------ UTILIDADES RED ------------------

def get_private_supernets():
    return [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
    ]


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def get_local_supernet():
    local_ip = ipaddress.ip_address(get_local_ip())
    for n in get_private_supernets():
        if local_ip in n:
            return n
    raise RuntimeError(f"IP local {local_ip} no está en redes privadas RFC1918. Abortando por seguridad.")

# ------------------ PROBES BROADCAST / MULTICAST ------------------

def probe_segment_ssdp(segment, iface_ip=None, timeout=1.5, use_broadcast=True):
    """Envía SSDP M-SEARCH al grupo multicast y opcionalmente al broadcast del segmento.
    Devuelve dict ip -> [bytes respuestas]
    """
    results = {}
    sock_list = []
    try:
        # multicast socket
        msock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        msock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            msock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        except Exception:
            pass
        if iface_ip:
            try:
                msock.bind((iface_ip, 0))
            except Exception:
                pass
        msock.setblocking(False)
        sock_list.append(msock)
        # send to multicast group
        try:
            msock.sendto(SSDP_MSEARCH, ("239.255.255.250", 1900))
        except Exception:
            pass

        # optional directed broadcast
        bsock = None
        if use_broadcast:
            try:
                bcast_addr = str(segment.broadcast_address)
                bsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                bsock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                if iface_ip:
                    try:
                        bsock.bind((iface_ip, 0))
                    except Exception:
                        pass
                try:
                    bsock.sendto(SSDP_MSEARCH, (bcast_addr, 1900))
                except Exception:
                    pass
                bsock.setblocking(False)
                sock_list.append(bsock)
            except Exception:
                bsock = None

        # listen
        start = time.time()
        while True:
            remaining = start + timeout - time.time()
            if remaining <= 0:
                break
            rlist, _, _ = select.select(sock_list, [], [], remaining)
            if not rlist:
                continue
            for s in rlist:
                try:
                    data, addr = s.recvfrom(65535)
                except Exception:
                    continue
                ip = addr[0]
                results.setdefault(ip, []).append(data)
    finally:
        for s in sock_list:
            try:
                s.close()
            except Exception:
                pass
    return results


def probe_segment_mdns(segment, iface_ip=None, timeout=1.5):
    """Envía consulta mDNS simple al grupo 224.0.0.251:5353. Devuelve dict ip->list(respuestas).
    Nota: para queries DNS-SD avanzadas conviene construir el paquete DNS; este es un probe simple.
    """
    results = {}
    try:
        msock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        msock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            msock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
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
            rlist, _, _ = select.select([msock], [], [], remaining)
            if not rlist:
                continue
            for s in rlist:
                try:
                    data, addr = s.recvfrom(65535)
                except Exception:
                    continue
                ip = addr[0]
                results.setdefault(ip, []).append(data)
    finally:
        try:
            msock.close() # type: ignore
        except Exception:
            pass
    return results

# ------------------ PING CHUNKED (fallback) ------------------

async def ping_one_cmd(host, per_host_timeout):
    system = platform.system()
    if system == "Windows":
        cmd = ["ping", "-n", "1", "-w", str(int(per_host_timeout * 1000)), host]
    elif system == "Darwin":
        cmd = ["ping", "-c", "1", "-t", "1", host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(int(max(1, per_host_timeout))), host]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        ret = await proc.wait()
        return ret == 0
    except Exception:
        return False

async def ping_host(host, per_host_timeout):
    try:
        return await asyncio.wait_for(ping_one_cmd(host, per_host_timeout), timeout=per_host_timeout + 0.5)
    except Exception:
        return False


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
            print(f"  - Timeout global por subnet alcanzado ({per_subnet_timeout}s). Abortando resto.")
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
            print(f"  - Timeout global por subnet alcanzado durante chunk. Abortando resto.")
            break
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()

        processed += len(chunk)
        pct = (processed / total * 100) if total else 100
        print(f"  - Progreso subnet: {processed}/{total} hosts ({pct:.1f}%), vivos hasta ahora: {len(alive)}")

    return sorted(set(alive), key=lambda s: tuple(int(x) for x in s.split(".")))

# ------------------ ARP parsing para asociar MACs ------------------

def parse_arp_unix(output):
    entries = []
    for line in output.splitlines():
        m = re.search(r'(?P<ip>\d{1,3}(?:\.\d{1,3}){3}).*(lladdr|at)\s+(?P<mac>[0-9a-fA-F:]{11,17})', line)
        if m:
            entries.append((m.group('ip'), m.group('mac').lower()))
            continue
        m2 = re.search(r'\((?P<ip>\d{1,3}(?:\.\d{1,3}){3})\)\s+at\s+(?P<mac>[0-9a-fA-F:]{11,17})', line)
        if m2:
            entries.append((m2.group('ip'), m2.group('mac').lower()))
    return entries


def parse_arp_table_raw():
    entries = []
    system = platform.system()
    try:
        if system == 'Windows':
            proc = subprocess.run(['arp', '-a'], capture_output=True, text=True, check=False)
            out = (proc.stdout or '') + (proc.stderr or '')
            # parse windows output basic
            for line in out.splitlines():
                m = re.search(r'^\s*(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-fA-F\-:]{11,17})', line)
                if m:
                    ip = m.group(1)
                    mac = m.group(2).replace('-', ':').lower()
                    entries.append((ip, mac))
        else:
            try:
                proc = subprocess.run(['ip', 'neigh'], capture_output=True, text=True, check=False)
                out = (proc.stdout or '') + (proc.stderr or '')
                if out.strip():
                    return parse_arp_unix(out)
            except FileNotFoundError:
                pass
            proc2 = subprocess.run(['arp', '-a'], capture_output=True, text=True, check=False)
            out2 = (proc2.stdout or '') + (proc2.stderr or '')
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

def generate_segments_for_supernet(supernet, segment_prefix_len, start_second=None, end_second=None):
    segments = []
    if supernet.prefixlen <= segment_prefix_len:
        for s in supernet.subnets(new_prefix=segment_prefix_len):
            if start_second is not None and end_second is not None:
                # comprobar segundo octeto
                second = int(str(s.network_address).split('.')[1])
                if second < start_second or second > end_second:
                    continue
            segments.append(s)
    else:
        segments = [supernet]
    return segments


def sample_ips_for_segment(segment, fixed_offsets=(1,128,254), random_count=DEFAULT_SAMPLE_RANDOM):
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

async def is_segment_active_by_broadcast(segment, iface_ip=None, timeout=1.5):
    # probar SSDP
    try:
        res = await asyncio.get_event_loop().run_in_executor(None, probe_segment_ssdp, segment, iface_ip, timeout, True)
        if res:
            return True, list(res.keys())
    except Exception:
        pass
    # probar mDNS
    try:
        res2 = await asyncio.get_event_loop().run_in_executor(None, probe_segment_mdns, segment, iface_ip, timeout)
        if res2:
            return True, list(res2.keys())
    except Exception:
        pass
    return False, []

async def is_segment_active_by_probe(segment, random_count=DEFAULT_SAMPLE_RANDOM):
    ips = sample_ips_for_segment(segment, random_count=random_count)
    if not ips:
        return False, []
    tasks = [asyncio.create_task(ping_host(ip, DEFAULT_PER_HOST_TIMEOUT)) for ip in ips]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    alive = [ip for ip, ok in zip(ips, results) if ok is True]
    return (len(alive) > 0), alive

# ------------------ FLOW PRINCIPAL ------------------

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
                    consecutive_empty = 0
                else:
                    consecutive_empty += 1
                    print(f"    => 0 vivos en {s} (consecutivos vacíos: {consecutive_empty}/{max_consecutive_empty})")
                    if consecutive_empty >= max_consecutive_empty:
                        print(f"    => Se alcanzó {consecutive_empty} subnets vacías consecutivas. Saltando resto de subnets en {seg}.")
                        break
        else:
            if seg.num_addresses - 2 > max_addresses_per_sweep:
                print(f"\nOmitiendo sweep directo de {seg} (demasiado grande: {seg.num_addresses} hosts).")
                continue
            print(f"\nPing sweep directo sobre {seg} (chunk_size={chunk_size}, per_host_timeout={per_host_timeout}) ...")
            alive = await ping_sweep_chunked(seg, chunk_size=chunk_size, per_host_timeout=per_host_timeout,
                                             per_subnet_timeout=per_subnet_timeout, concurrency=concurrency)
            print(f"  => {len(alive)} hosts vivos en {seg}")
            all_alive.extend(alive)
    return sorted(set(all_alive), key=lambda s: tuple(int(x) for x in s.split('.')))


def merge_ip_mac(alive_ips, arp_entries, allowed_networks, segments_map):
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
    # añadir segmento string por ip
    final = {}
    for ip, mac in kept.items():
        s_str = ""
        try:
            ip_obj = ipaddress.ip_address(ip)
            for seg in segments_map:
                if ip_obj in seg:
                    s_str = str(seg)
                    break
        except Exception:
            pass
        final[ip] = (s_str, mac)
    return final


def print_and_save(results_map, csv_name):
    print("\n---- RESULTADO FINAL (ejemplos) ----")
    ips_sorted = sorted(results_map.keys(), key=lambda s: tuple(int(x) for x in s.split('.')))
    for ip in ips_sorted[:200]:
        seg, mac = results_map[ip]
        print(f"{seg}\t{ip}\t{mac or '(sin MAC)'}")
    print(f"\nTotal únicas encontradas: {len(ips_sorted)}")
    with open(csv_name, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['segment','ip','mac'])
        for ip in ips_sorted:
            seg, mac = results_map[ip]
            w.writerow([seg, ip, mac or ''])
    print('CSV guardado en', csv_name)

# ------------------ CLI y MAIN ------------------

def parse_args():
    p = argparse.ArgumentParser(description='Broadcast/multicast segment scanner (RFC1918).')
    p.add_argument('--segment-prefix', type=int, default=DEFAULT_SEGMENT_PREFIX)
    p.add_argument('--detailed-prefix', type=int, default=DEFAULT_DETAILED)
    p.add_argument('--concurrency', type=int, default=DEFAULT_CONCURRENCY)
    p.add_argument('--sample-random', type=int, default=DEFAULT_SAMPLE_RANDOM)
    p.add_argument('--max-sweep', type=int, default=DEFAULT_MAX_SWEEP)
    p.add_argument('--chunk-size', type=int, default=DEFAULT_CHUNK_SIZE)
    p.add_argument('--per-host-timeout', type=float, default=DEFAULT_PER_HOST_TIMEOUT)
    p.add_argument('--per-subnet-timeout', type=float, default=DEFAULT_PER_SUBNET_TIMEOUT)
    p.add_argument('--max-consecutive-empty', type=int, default=DEFAULT_MAX_CONSEC_EMPTY)
    p.add_argument('--start', type=int, default=DEFAULT_START_SECOND, help='primer segundo octeto (ej 100)')
    p.add_argument('--end', type=int, default=DEFAULT_END_SECOND, help='último segundo octeto (ej 119)')
    p.add_argument('--use-broadcast-probe', action='store_true', help='usar SSDP/mDNS broadcast probe antes del probe por ping')
    p.add_argument('--no-arp', action='store_true', help='no leer ARP al final')
    return p.parse_args()


def main():
    args = parse_args()
    try:
        local_super = get_local_supernet()
    except Exception as e:
        print('ERROR:', e)
        sys.exit(1)

    print('Local supernet detectado:', local_super)
    segments = generate_segments_for_supernet(local_super, args.segment_prefix, start_second=args.start, end_second=args.end)
    print(f'Generados {len(segments)} segmentos /{args.segment_prefix} a evaluar (filtrado {args.start}-{args.end}).')

    print('\nLeyendo ARP local...')
    arp_entries = parse_arp_table_raw()
    arp_entries = [(ip, mac) for ip, mac in arp_entries if ipaddress.ip_address(ip) in local_super]
    print(f'Entradas ARP locales dentro de {local_super}: {len(arp_entries)}')

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    active_segments = []
    segments_map = segments
    try:
        for seg in segments:
            arp_active = any(ipaddress.ip_address(ip) in seg for ip, _ in arp_entries)
            probe_active = False
            probe_examples = []
            if args.use_broadcast_probe:
                try:
                    probe_active, probe_examples = loop.run_until_complete(is_segment_active_by_broadcast(seg, iface_ip=None, timeout=1.5))
                except Exception as e:
                    print('WARN: broadcast probe falló para', seg, '->', e)
            if not probe_active:
                try:
                    probe_active, probe_examples = loop.run_until_complete(is_segment_active_by_probe(seg, random_count=args.sample_random))
                except Exception as e:
                    print('WARN: probe ping muestreo falló para', seg, '->', e)
            if arp_active or probe_active:
                active_segments.append(seg)
                reason = []
                if arp_active: reason.append('arp')
                if probe_active: reason.append('probe')
                print(f'[ACTIVO] {seg}  (detectado por: {", ".join(reason)})')
            else:
                print(f'[INACTIVO] {seg}')
    finally:
        pass

    if not active_segments:
        print('No se detectaron segmentos activos. Fin.')
        return

    try:
        alive_ips = loop.run_until_complete(scan_active_segments(active_segments,
                                                                 args.detailed_prefix,
                                                                 args.concurrency,
                                                                 args.max_sweep,
                                                                 args.chunk_size,
                                                                 args.per_host_timeout,
                                                                 args.per_subnet_timeout,
                                                                 args.max_consecutive_empty))
    finally:
        loop.close()


    print(f'\nHosts vivos por ping detectados: {len(alive_ips)} (ej: {alive_ips[:20]})')

    arp_after = []
    if not args.no_arp:
        print('\nLeyendo ARP local otra vez...')
        arp_after = parse_arp_table_raw()
        arp_after = [(ip, mac) for ip, mac in arp_after if ipaddress.ip_address(ip) in local_super]
        print(f'Entradas ARP encontradas ahora: {len(arp_after)}')

    merged = merge_ip_mac(alive_ips, arp_after if arp_after else arp_entries, [local_super], segments_map)

    csv_name = f"{CSV_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    print_and_save(merged, csv_name)

if __name__ == '__main__':
    main()


# Fin del contador al final del script
end_time = time.time()
print(f"Tiempo total de ejecución: {end_time - start_time:.6f} segundos")