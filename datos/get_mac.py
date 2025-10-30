import csv
import subprocess
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import time

import time

# Inicio del contador lo más arriba posible
start_time = time.time()
# Reutiliza tu parse_arp_table_raw() existente (debe estar en el mismo módulo)
# Si no está en el mismo archivo, impórtala: from myscanner import parse_arp_table_raw
from scan_ip_mac import parse_arp_table_raw

def _ping_ip_sync(ip, timeout=1):
    """Ping síncrono (devuelve True si responde). Timeout en segundos."""
    system = platform.system()
    # Windows wants timeout in ms for -w
    if system == "Windows":
        cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), ip]
    elif system == "Darwin":
        cmd = ["ping", "-c", "1", "-t", "1", ip]
    else:
        # Linux/Unix
        cmd = ["ping", "-c", "1", "-W", str(int(max(1, timeout)) ), ip]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return proc.returncode == 0
    except Exception:
        return False

def update_csv_with_macs(input_csv_path,
                         output_csv_path=None,
                         ping_missing=True,
                         ping_timeout=0.8,
                         workers=50,
                         overwrite=True):
    """
    Lee input_csv_path (acepta encabezados con 'ip' y opcionalmente 'mac' y 'segment'),
    intenta poblar MACs (opcional: hace ping a IPs sin mac para poblar ARP),
    re-lee la tabla ARP (parse_arp_table_raw) y escribe output CSV con MACs actualizadas.

    Args:
      input_csv_path (str): path al CSV de entrada.
      output_csv_path (str|None): si None, crea "<input>_with_macs.csv" (o sobrescribe si overwrite True).
      ping_missing (bool): si True, hace ping a las IPs sin MAC antes de leer ARP.
      ping_timeout (float): timeout por ping en segundos.
      workers (int): concurrencia para pings.
      overwrite (bool): si True y output_csv_path es None, sobrescribe input file.

    Returns:
      dict: {'input':..., 'output':..., 'total_rows':n, 'mac_found':m, 'mac_missing':k}
    """

    if not os.path.isfile(input_csv_path):
        raise FileNotFoundError(f"Input CSV not found: {input_csv_path}")

    # 1) Leer CSV y detectar columnas
    rows = []
    with open(input_csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        # normalize field names
        lower_fields = [h.lower() for h in fields]
        for r in reader:
            row = {k: (v.strip() if v is not None else "") for k, v in r.items()}
            # try to find ip and mac fields
            ip = None
            mac = None
            # common headers
            for candidate in ("ip", "address", "host"):
                if candidate in lower_fields:
                    ip = row[fields[lower_fields.index(candidate)]]
                    break
            if ip is None:
                # try second column heuristics
                # if columns are [segment,ip,mac] -> ip is field 1
                if len(fields) >= 2:
                    ip = row[fields[1]]
            # mac field
            for candidate in ("mac", "ether", "hwaddr"):
                if candidate in lower_fields:
                    mac = row[fields[lower_fields.index(candidate)]]
                    break
            if mac is None and len(fields) >= 3:
                mac = row[fields[2]]
            rows.append({"raw": row, "ip": ip, "mac": (mac or "").strip()})

    total = len(rows)

    # 2) identificar IPs sin MAC
    missing_ips = [r["ip"] for r in rows if r["ip"] and (not r["mac"])]
    missing_ips = list(dict.fromkeys(missing_ips))  # dedupe preserve order
    print(f"CSV rows: {total}, IPs missing MAC: {len(missing_ips)}")

    # 3) opcional: ping masivo concurrente para poblar ARP
    if ping_missing and missing_ips:
        print(f"Pinging {len(missing_ips)} IPs (timeout={ping_timeout}s, workers={workers}) to populate ARP...")
        with ThreadPoolExecutor(max_workers=min(workers, len(missing_ips))) as ex:
            futures = {ex.submit(_ping_ip_sync, ip, ping_timeout): ip for ip in missing_ips}  # type: ignore
            print(futures)
            for fut in as_completed(futures):
                ip = futures[fut]
                try:
                    ok = fut.result()
                except Exception:
                    ok = False
                # optional: progress printing (not too chatty)
        # small wait to allow ARP table to settle
        time.sleep(0.5)

    # 4) re-parse ARP table (usa tu función parse_arp_table_raw)
    try:
        arp_entries = parse_arp_table_raw()  # debe devolver lista [(ip, mac), ...]
    except Exception as e:
        print("Warning: parse_arp_table_raw() falló:", e)
        arp_entries = []

    arp_map = {ip: mac.lower() for ip, mac in arp_entries if mac}

    # 5) actualizar filas con MACs si están ahora en arp_map
    updated = 0
    still_missing = 0
    for r in rows:
        ip = r["ip"]
        if not ip:
            continue
        if r["mac"]:
            continue  # ya tenía mac
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

    # Construir header: conservar los campos originales, pero asegurar 'mac' column exists
    orig_fieldnames = fields[:] if fields else ["ip", "mac"]
    # find or add mac field
    low = [h.lower() for h in orig_fieldnames]
    if "mac" not in low:
        orig_fieldnames.append("mac")  # type: ignore

    with open(output_csv_path, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=orig_fieldnames)
        writer.writeheader()
        for r in rows:
            outrow = {}
            # fill original headers from raw if present
            for h in orig_fieldnames:
                # preserve existing raw column values
                if h in r["raw"]:
                    outrow[h] = r["raw"].get(h, "")
                else:
                    # try case-insensitive match in raw
                    for k in r["raw"]:
                        if k.lower() == h.lower():
                            outrow[h] = r["raw"].get(k, "")
                            break
                    else:
                        outrow[h] = ""
            # ensure 'mac' field is current
            # find index of mac header (case-insensitive)
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

update_csv_with_macs("optimized_scan_20251029_125612.csv")

# Fin del contador al final del script
end_time = time.time()
print(f"Tiempo total de ejecución: {end_time - start_time:.6f} segundos")