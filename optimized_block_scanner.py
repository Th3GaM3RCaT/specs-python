#!/usr/bin/env python3
"""
optimized_block_scanner.py

Escaneo optimizado por bloques dentro de segmentos 10.100.0.0/16 .. 10.119.0.0/16.
Usa probes broadcast/multicast (SSDP/mDNS) por bloque y fallback a ping-sweep chunked
si no hay respuestas. Luego asocia MACs leyendo la tabla ARP.

Ejemplo:
  python3 optimized_block_scanner.py --start 100 --end 119 --use-broadcast-probe

"""
import argparse
import asyncio
import ipaddress
import socket
import subprocess
import re
import csv
import sys
import select
import time
from datetime import datetime
from itertools import islice

# ------------------ DEFAULTS ------------------
DEFAULT_START = 100
DEFAULT_END = 119
DEFAULT_CHUNK = 255
DEFAULT_PER_HOST_TIMEOUT = 0.8
DEFAULT_PER_SUBNET_TIMEOUT = 8.0
DEFAULT_CONCURRENCY = 300
DEFAULT_PROBE_TIMEOUT = 0.9
CSV_PREFIX = "optimized_scan"

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
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
        try:
            msock.sendto(SSDP_MSEARCH, ("239.255.255.250", 1900))
        except Exception:
            pass

        bsock = None
        if use_broadcast:
            try:
                baddr = str(segment_network.broadcast_address)
                bsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                bsock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
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
            rlist, _, _ = select.select(sock_list, [], [], remaining)
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
                results.add(addr[0])
    finally:
        try:
            msock.close() # type: ignore
        except Exception:
            pass
    return results

# ------------------ PING CHUNKED (async) ------------------
async def ping_one_cmd(host, per_host_timeout):
    system = sys.platform
    if system.startswith("win"):
        cmd = ["ping", "-n", "1", "-w", str(int(per_host_timeout * 1000)), host]
    elif system.startswith("darwin"):
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

# ------------------ ARP PARSING ------------------
def parse_arp_table(): # type: ignore
    entries = []
    try:
        proc = subprocess.run(["ip", "neigh"], capture_output=True, text=True, check=False)
        out = (proc.stdout or "") + (proc.stderr or "")
        if out.strip():
            for line in out.splitlines():
                m = re.search(r'(?P<ip>\d{1,3}(?:\.\d{1,3}){3}).*(lladdr|at)\s+(?P<mac>[0-9a-fA-F:]{11,17})', line)
                if m:
                    entries.append((m.group("ip"), m.group("mac").lower()))
            if entries:
                return entries
    except Exception:
        pass
    # fallback arp -a
    try:
        proc2 = subprocess.run(["arp", "-a"], capture_output=True, text=True, check=False)
        out2 = (proc2.stdout or "") + (proc2.stderr or "")
        for line in out2.splitlines():
            m2 = re.search(r'\((?P<ip>\d{1,3}(?:\.\d{1,3}){3})\)\s+at\s+(?P<mac>[0-9a-fA-F:]{11,17})', line)
            if m2:
                entries.append((m2.group("ip"), m2.group("mac").lower()))
    except Exception:
        pass
    # normalize dict
    d = {}
    for ip, mac in entries:
        if mac:
            d[ip] = mac.lower()
    return list(d.items())

# ------------------ BLOCK PATTERNS ------------------
# Blocks are tuples (start_ip_inclusive, end_ip_inclusive) defined inside each /16.
# We'll create ipaddress.ip_network objects for each block
def blocks_for_segment(second_octet):
    """
    Return list of (ip_network) blocks to scan for given 10.<second>.* segment.
    Uses patterns inferred from your data.
    """
    seg_base = f"10.{second_octet}.0.0/16"
    blocks = []
    s = second_octet
    if s == 100:
        # specific blocks found in data
        blocks += [
            ipaddress.ip_network("10.100.0.0/25"),    # .0 - .127
            ipaddress.ip_network("10.100.0.128/25"),  # .128 - .255 (we'll cover to .132 via first block but keep both)
            ipaddress.ip_network("10.100.2.0/24"),    # big concentrated block 2.x
            ipaddress.ip_network("10.100.3.0/24"),    # 3.x cluster
            ipaddress.ip_network("10.100.5.0/24"),    # scattered
            ipaddress.ip_network("10.100.10.0/24"),   # dense 10.x cluster
        ]
    else:
        # default heuristic blocks for other segments:
        # - very small low block around .1
        # - .0/25 to catch .1-.127
        # - .50/32 and block around .100/30
        blocks += [
            ipaddress.ip_network(f"10.{s}.0.0/25"),            # low .1..127
            ipaddress.ip_network(f"10.{s}.50.0/32") if False else ipaddress.ip_network(f"10.{s}.0.0/32"), # placeholder (we'll probe specific ips too)
            ipaddress.ip_network(f"10.{s}.100.0/26")           # around .100 (covers .100-.127)
        ]
    return blocks

# ------------------ SMALL HELPERS ------------------
def ips_from_range(net):
    return list(net.hosts())

def probe_block(segment_net, iface_ip, timeout, use_broadcast):
    ssdp = probe_ssdp(segment_net, iface_ip=iface_ip, timeout=timeout, use_broadcast=use_broadcast)
    if ssdp:
        return set(ssdp)
    mdns = probe_mdns(segment_net, iface_ip=iface_ip, timeout=timeout)
    return set(mdns)

# ------------------ MAIN FLOW ------------------
async def scan_blocks(start, end, chunk_size, per_host_timeout, per_subnet_timeout, concurrency, probe_timeout, use_broadcast_probe):
    local_super = get_local_supernet()
    all_alive = set()
    loop = asyncio.get_event_loop()

    for second in range(start, end + 1):
        print(f"\n--- Segment 10.{second}.x.x ---")
        blks = blocks_for_segment(second)
        # dedupe blocks
        seen = set()
        final_blocks = []
        for b in blks:
            if str(b) in seen:
                continue
            seen.add(str(b))
            final_blocks.append(b)

        # Also test a few "typical" single IP probes: .1, .50, .100
        typical_ips = [f"10.{second}.1", f"10.{second}.50", f"10.{second}.100"]

        # 1) Probe typical single IPs (fast)
        for tip in typical_ips:
            try:
                ok = await ping_host(tip, per_host_timeout)
            except Exception:
                ok = False
            if ok:
                print(f"  - quick alive: {tip}")
                all_alive.add(tip)

        # 2) For each block: probe by broadcast/multicast first (cheap)
        for b in final_blocks:
            print(f"  -> block {b}")
            found_ips = set()
            if use_broadcast_probe:
                try:
                    found_ips = await loop.run_in_executor(None, probe_block, b, None, probe_timeout, True)
                except Exception:
                    found_ips = set()
                if found_ips:
                    print(f"     probe found {len(found_ips)} hosts (examples: {list(found_ips)[:6]})")
                    all_alive.update(found_ips)
                    continue  # skip sweep if probe returned results

            # if no probe hits, do limited chunked sweep on block (not entire /24 unless block is big)
            # but limit total addresses we will sweep to reasonable counts
            num_hosts = b.num_addresses - 2
            if num_hosts <= 0:
                continue
            # build a temporary network for sweep: use the block as-is
            # but skip if block too large
            if num_hosts > 4096:
                print(f"     skipping sweep of {b} (too large: {num_hosts} hosts)")
                continue
            print(f"     doing chunked sweep of {b} ({num_hosts} hosts)")
            alive = await ping_sweep_chunked(b, chunk_size=chunk_size, per_host_timeout=per_host_timeout,
                                             per_subnet_timeout=per_subnet_timeout, concurrency=concurrency)
            if alive:
                print(f"     => {len(alive)} alive in block (examples: {alive[:6]})")
                all_alive.update(alive)
            else:
                print("     => 0 alive in block")

    return sorted(all_alive, key=lambda s: tuple(int(x) for x in s.split(".")))

def merge_with_arp(alive_ips):
    arp = parse_arp_table()
    arp_map = dict(arp)
    out = []
    for ip in sorted(alive_ips, key=lambda s: tuple(int(x) for x in s.split("."))):
        mac = arp_map.get(ip)
        out.append((ip, mac))
    return out

def parse_args():
    p = argparse.ArgumentParser(description="Optimized block scanner for 10.100..10.119 ranges.")
    p.add_argument("--start", type=int, default=DEFAULT_START)
    p.add_argument("--end", type=int, default=DEFAULT_END)
    p.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK)
    p.add_argument("--per-host-timeout", type=float, default=DEFAULT_PER_HOST_TIMEOUT)
    p.add_argument("--per-subnet-timeout", type=float, default=DEFAULT_PER_SUBNET_TIMEOUT)
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    p.add_argument("--probe-timeout", type=float, default=DEFAULT_PROBE_TIMEOUT)
    p.add_argument("--use-broadcast-probe", action="store_true", help="use SSDP/mDNS probe before sweeping blocks")
    p.add_argument("--csv", action="store_true", help="save CSV (default: yes)")
    return p.parse_args()

def parse_arp_table():
    # wrapper: reuse parse_arp_table from previous patterns
    return parse_arp_table_raw_fallback()

def parse_arp_table_raw_fallback():
    entries = []
    try:
        proc = subprocess.run(["ip", "neigh"], capture_output=True, text=True, check=False)
        out = (proc.stdout or "") + (proc.stderr or "")
        if out.strip():
            for line in out.splitlines():
                m = re.search(r'(?P<ip>\d{1,3}(?:\.\d{1,3}){3}).*(lladdr|at)\s+(?P<mac>[0-9a-fA-F:]{11,17})', line)
                if m:
                    entries.append((m.group("ip"), m.group("mac").lower()))
            if entries:
                return entries
    except Exception:
        pass
    try:
        proc2 = subprocess.run(["arp", "-a"], capture_output=True, text=True, check=False)
        out2 = (proc2.stdout or "") + (proc2.stderr or "")
        for line in out2.splitlines():
            m2 = re.search(r'\((?P<ip>\d{1,3}(?:\.\d{1,3}){3})\)\s+at\s+(?P<mac>[0-9a-fA-F:]{11,17})', line)
            if m2:
                entries.append((m2.group("ip"), m2.group("mac").lower()))
    except Exception:
        pass
    d = {}
    for ip, mac in entries:
        if mac:
            d[ip] = mac.lower()
    return list(d.items())

# ------------------ ENTRYPOINT ------------------
def main():
    args = parse_args()
    try:
        local_super = get_local_supernet()
    except Exception as e:
        print("ERROR:", e)
        sys.exit(1)

    print(f"Scanning 10.{args.start}.x.x .. 10.{args.end}.x.x  (use-broadcast={args.use_broadcast_probe})")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        alive = loop.run_until_complete(scan_blocks(args.start, args.end,
                                                    chunk_size=args.chunk_size,
                                                    per_host_timeout=args.per_host_timeout,
                                                    per_subnet_timeout=args.per_subnet_timeout,
                                                    concurrency=args.concurrency,
                                                    probe_timeout=args.probe_timeout,
                                                    use_broadcast_probe=args.use_broadcast_probe))
    finally:
        loop.close()

    print(f"\nTotal alive IPs found: {len(alive)} (examples: {alive[:20]})")
    merged = merge_with_arp(alive)
    csv_name = f"{CSV_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(csv_name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ip", "mac"])
        for ip, mac in merged:
            w.writerow([ip, mac or ""])
    print("CSV saved:", csv_name)

if __name__ == "__main__":
    main()