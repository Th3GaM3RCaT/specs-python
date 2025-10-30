import asyncio, ipaddress, platform, socket, subprocess, csv
from datetime import datetime

CONCURRENCY = 300
ASSUME_SEGMENT_PREFIX = 16  # 10.x.0.0/16

# -----------------------------------------------------
# UTILIDADES BÁSICAS
# -----------------------------------------------------
def get_private_supernets():
    """Solo rangos privados, nunca Internet."""
    return [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16")
    ]

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

def get_local_supernet():
    ip = ipaddress.ip_address(get_local_ip())
    for n in get_private_supernets():
        if ip in n:
            return n
    raise RuntimeError("Tu IP no pertenece a una red privada RFC1918")

async def ping_one(host):
    system = platform.system()
    if system == "Windows":
        cmd = ["ping", "-n", "1", "-w", "700", host]
    else:
        cmd = ["ping", "-c", "1", "-W", "1", host]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        ret = await proc.wait()
        return ret == 0
    except Exception:
        return False

# -----------------------------------------------------
# ESCANEO
# -----------------------------------------------------
async def detect_active_segments(supernet):
    """Detecta qué subredes /16 dentro del supernet tienen hosts activos."""
    print(f"Detectando segmentos activos dentro de {supernet}...")
    segments = list(supernet.subnets(new_prefix=ASSUME_SEGMENT_PREFIX))
    active = []

    for seg in segments:
        # probar 5 IPs al azar dentro del segmento
        test_ips = [str(seg.network_address + i * 5000) for i in range(5)]
        results = await asyncio.gather(*[ping_one(ip) for ip in test_ips])
        if any(results):
            print(f"✔ Segmento activo: {seg}")
            active.append(seg)
        else:
            print(f"✖ Sin respuesta: {seg}")

    return active

async def scan_segment(segment):
    """Escaneo completo de hosts en un segmento dado."""
    print(f"\n--- Escaneando {segment} ---")
    sem = asyncio.Semaphore(CONCURRENCY)
    alive = []

    async def worker(ip):
        async with sem:
            if await ping_one(str(ip)):
                alive.append(str(ip))

    tasks = [asyncio.create_task(worker(ip)) for ip in segment.hosts()]
    await asyncio.gather(*tasks)
    print(f"  {len(alive)} hosts activos en {segment}")
    return alive

# -----------------------------------------------------
# MAIN
# -----------------------------------------------------
async def main():
    supernet = get_local_supernet()
    active_segments = await detect_active_segments(supernet)

    all_alive = {}
    for seg in active_segments:
        alive = await scan_segment(seg)
        all_alive[str(seg)] = alive

    name = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["segment", "ip"])
        for seg, ips in all_alive.items():
            for ip in ips:
                w.writerow([seg, ip])

    print(f"\nResultados guardados en: {name}")

if __name__ == "__main__":
    asyncio.run(main())
