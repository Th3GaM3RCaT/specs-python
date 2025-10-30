import asyncio, ipaddress, platform, socket, subprocess, re, os
from datetime import datetime
ASSUME_CIDR = "/16"   # ajusta si tu red no es /24
CONCURRENCY = 300
def get_local_network():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ipaddress.ip_network(ip + ASSUME_CIDR, strict=False)
async def ping_one(host):
    system = platform.system()
    if system == "Windows":
        cmd = ["ping", "-n", "1", "-w", "1000", host]
    elif system == "Darwin":
        cmd = ["ping", "-c", "1", "-t", "1", host]
    else:
        cmd = ["ping", "-c", "1", "-W", "1", host]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
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
    await asyncio.gather(*tasks)
    return alive
def parse_arp_table_raw():
    try:
        proc = subprocess.run(["arp", "-a"], capture_output=True, text=True, check=False)
        out = proc.stdout + proc.stderr
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
def is_broadcast_ip(ip_obj, network):
    # 255.255.255.255 o broadcast de la red
    if str(ip_obj) == "255.255.255.255":
        return True
    try:
        return ip_obj == network.broadcast_address
    except Exception:
        return False
def is_broadcast_mac(mac):
    if not mac:
        return False
    m = mac.lower()
    return m == "ff:ff:ff:ff:ff:ff" or m == "FF:FF:FF:FF:FF:FF".lower()
def filter_entries(entries, network):
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
        if is_broadcast_ip(ip_obj, network):
            reason = "broadcast IP"
            discarded.append((ip_str, mac, reason))
            continue
        if ip_obj.is_multicast or ip_obj.is_unspecified or ip_obj.is_loopback:
            reason = "multicast/unspecified/loopback"
            discarded.append((ip_str, mac, reason))
            continue
        if ip_obj not in network:
            reason = f"fuera de subred {network}"
            discarded.append((ip_str, mac, reason))
            continue
        if mac and is_broadcast_mac(mac):
            reason = "MAC broadcast"
            discarded.append((ip_str, mac, reason))
            continue
        if mac:
            mac_norm = mac.lower()
        else:
            mac_norm = None
        if ip_str not in kept:
            kept[ip_str] = mac_norm
        else:
            if kept[ip_str] is None and mac_norm:
                kept[ip_str] = mac_norm
    print (kept)
    print(discarded)
    return kept, discarded
def print_report(kept, discarded):
    print("\n---- RESULTADOS FILTRADOS ----")
    if not kept:
        print("No se encontró ninguna IP válida con MAC dentro de la subred.")
    else:
        for ip in sorted(kept.keys(), key=lambda s: tuple(int(x) for x in s.split("."))):
            mac = kept[ip] or "(sin MAC)"
            print(f"{ip} -> {mac}")
    print(f"\nTotal válidas: {len(kept)}")
    print("\n---- ENTRADAS DESCARTADAS (ejemplos) ----")
    for ip, mac, reason in discarded[:40]:
        print(f"{ip} -> {mac or '(no mac)'}  : {reason}")
    print(f"\nTotal descartadas: {len(discarded)}")
def main():
    network = get_local_network()
    try:
        alive = asyncio.run(ping_sweep(network, concurrency=CONCURRENCY))
    except Exception as e:
        pass
    raw = parse_arp_table_raw()
    kept, discarded = filter_entries(raw, network)
    csv_name = f"scan_clean_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    try:
        import csv
        with open(csv_name, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ip", "mac"])
            for ip in sorted(kept.keys(), key=lambda s: tuple(int(x) for x in s.split("."))):
                w.writerow([ip, kept[ip] or ""])
    except Exception as e:
        pass
if __name__ == "__main__":
    main()
