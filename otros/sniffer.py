#!/usr/bin/env python3
# escucha_broadcast_multi.py
import socket
import selectors
import json
from datetime import datetime

# --- CONFIG ---
# Puedes poner una lista explícita: [5000, 5001, 6000]
PORTS = list(range(4999,5512))
BUFFER_SIZE = 4096
OUTPUT_FILE = "broadcast_log.ndjson"  # cada línea es un JSON
# ----------------

sel = selectors.DefaultSelector()

def create_udp_socket(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Permitir reusar la dirección/puerto (útil en Linux)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Para enviar broadcast se usa SO_BROADCAST; para recibir no es imprescindible,
    # pero no hace daño ponerlo.
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # Bind en todas las interfaces
    s.bind(("", port))
    s.setblocking(False)
    return s

def pretty_payload(data: bytes):
    # intenta decodificar a UTF-8; si falla, devuelve hex
    try:
        text = data.decode("utf-8")
        # si es texto con muchos caracteres de control, mejor mostrar hex
        if any(ord(c) < 9 for c in text[:32]):
            raise ValueError
        return {"type": "text", "value": text}
    except Exception:
        return {"type": "hex", "value": data.hex()}

def handle_read(sock, port):
    try:
        data, addr = sock.recvfrom(BUFFER_SIZE)
    except BlockingIOError:
        return

    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "listen_port": port,
        "from_ip": addr[0],
        "from_port": addr[1],
        "payload": pretty_payload(data)
    }
    # Guardar como una línea JSON (NDJSON)
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # También imprimir por consola (opcional)
    print(f"[{entry['timestamp']}] {addr[0]}:{addr[1]} -> port {port} -> {entry['payload']['type']}")

def main():
    sockets = {}
    try:
        for p in PORTS:
            try:
                s = create_udp_socket(p)
                sel.register(s, selectors.EVENT_READ, data=p)
                sockets[p] = s
                print(f"Escuchando broadcast UDP en el puerto {p}")
            except Exception as e:
                print(f"No pude bindear puerto {p}: {e}")

        print(f"Guardando paquetes en {OUTPUT_FILE} (una línea JSON por paquete). Ctrl-C para salir.")
        while True:
            events = sel.select(timeout=None)
            for key, mask in events:
                sock = key.fileobj
                port = key.data
                handle_read(sock, port)

    except KeyboardInterrupt:
        print("\nCerrando sockets...")
    finally:
        for s in sockets.values():
            try:
                sel.unregister(s)
                s.close()
            except Exception:
                pass

if __name__ == "__main__":
    main()
