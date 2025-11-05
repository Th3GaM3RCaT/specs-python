"""
Sistema de Agentes de Verificación de Red
Permite a clientes verificados actuar como agentes distribuidos para:
- Escanear su segmento local (ARP)
- Detectar MAC spoofing
- Reportar al servidor
"""
import socket
import subprocess
import re
from datetime import datetime
from typing import List, Tuple, Dict
import json


def obtener_segmento_local() -> str:
    """
    Obtiene el segmento de red local del cliente.
    
    Returns:
        str: Segmento de red en formato "10.100.X.0/24"
    """
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Extraer segmento (ej: 10.100.2.152 -> 10.100.2.0/24)
        octetos = local_ip.split('.')
        segmento = f"{octetos[0]}.{octetos[1]}.{octetos[2]}.0/24"
        
        return segmento
    except Exception as e:
        print(f"[ERROR] No se pudo obtener segmento local: {e}")
        return None # type: ignore


def escanear_arp_local() -> List[Tuple[str, str]]:
    """
    Escanea la tabla ARP local del sistema (sin hacer pings).
    Más rápido y menos intrusivo que escaneo activo completo.
    
    Returns:
        List[Tuple[str, str]]: Lista de tuplas (ip, mac)
    """
    resultados = []
    
    try:
        # Ejecutar arp -a (Windows)
        proc = subprocess.run(
            ['arp', '-a'],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        if proc.returncode != 0:
            return resultados
        
        output = proc.stdout
        
        # Parsear salida ARP de Windows
        # Formato: "  10.100.2.152      3c-52-82-57-32-cb     dinámico"
        patron = r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2})'
        
        for match in re.finditer(patron, output):
            ip = match.group(1)
            mac = match.group(2).replace('-', ':').lower()
            
            # Filtrar IPs broadcast, multicast, etc.
            if not ip.endswith('.255') and not ip.startswith('224.'):
                resultados.append((ip, mac))
        
        return resultados
        
    except subprocess.TimeoutExpired:
        print("[WARN] Timeout ejecutando arp -a")
        return resultados
    except Exception as e:
        print(f"[ERROR] Error escaneando ARP: {e}")
        return resultados


def generar_reporte_agente() -> Dict:
    """
    Genera un reporte completo del agente para enviar al servidor.
    
    Returns:
        Dict: Reporte con segmento, timestamp, IP/MAC encontradas
    """
    segmento = obtener_segmento_local()
    arp_entries = escanear_arp_local()
    
    reporte = {
        "tipo": "reporte_agente",
        "timestamp": datetime.now().isoformat(),
        "segmento": segmento,
        "agente_ip": socket.gethostbyname(socket.gethostname()),
        "total_dispositivos": len(arp_entries),
        "dispositivos": [
            {"ip": ip, "mac": mac}
            for ip, mac in arp_entries
        ]
    }
    
    return reporte


def enviar_reporte_servidor(reporte: Dict, server_ip: str, server_port: int = 5255) -> bool:
    """
    Envía el reporte al servidor.
    
    Args:
        reporte: Diccionario con el reporte
        server_ip: IP del servidor
        server_port: Puerto TCP del servidor
        
    Returns:
        bool: True si se envió exitosamente
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((server_ip, server_port))
        
        # Enviar reporte como JSON
        mensaje = json.dumps(reporte).encode('utf-8')
        sock.sendall(mensaje)
        
        sock.close()
        print(f"[OK] Reporte de agente enviado al servidor {server_ip}")
        return True
        
    except Exception as e:
        print(f"[ERROR] No se pudo enviar reporte: {e}")
        return False


# Funciones para integración con specs.py
def ejecutar_como_agente(server_ip: str) -> bool:
    """
    Función principal para ejecutar cliente como agente.
    Llamar desde specs.py cuando el servidor lo solicite.
    
    Args:
        server_ip: IP del servidor para enviar reporte
        
    Returns:
        bool: True si el escaneo y envío fueron exitosos
    """
    print("\n" + "="*60)
    print("MODO AGENTE DE VERIFICACION ACTIVADO")
    print("="*60)
    
    segmento = obtener_segmento_local()
    print(f"\n[INFO] Segmento local: {segmento}")
    print("[INFO] Escaneando tabla ARP local...")
    
    reporte = generar_reporte_agente()
    
    print(f"[OK] Encontrados {reporte['total_dispositivos']} dispositivos en ARP")
    
    # Mostrar primeros 5
    for i, disp in enumerate(reporte['dispositivos'][:5], 1):
        print(f"  {i}. {disp['ip']:15} -> {disp['mac']}")
    
    if len(reporte['dispositivos']) > 5:
        print(f"  ... y {len(reporte['dispositivos']) - 5} más")
    
    print(f"\n[INFO] Enviando reporte al servidor {server_ip}...")
    
    if enviar_reporte_servidor(reporte, server_ip):
        print("[SUCCESS] Reporte enviado exitosamente")
        print("="*60 + "\n")
        return True
    else:
        print("[FAILED] No se pudo enviar reporte")
        print("="*60 + "\n")
        return False


if __name__ == "__main__":
    # Test local
    print("=== TEST DE AGENTE DE VERIFICACION ===\n")
    
    segmento = obtener_segmento_local()
    print(f"Segmento local: {segmento}\n")
    
    print("Escaneando ARP...")
    resultados = escanear_arp_local()
    
    print(f"\nEncontrados {len(resultados)} dispositivos:\n")
    for ip, mac in resultados[:10]:
        print(f"  {ip:15} -> {mac}")
    
    if len(resultados) > 10:
        print(f"\n  ... y {len(resultados) - 10} más")
