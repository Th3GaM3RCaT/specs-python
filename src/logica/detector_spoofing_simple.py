"""
Detector de Spoofing MINIMALISTA
Version simplificada sin todo el framework de alertas.
Solo detecta MACs duplicadas entre subredes y lo muestra en consola.
"""

import sqlite3
from typing import Dict, List
from collections import defaultdict


def detectar_spoofing_simple(db_path: str = "specs.db") -> List[Dict]:
    """
    Detecta MACs duplicadas en diferentes subredes (spoofing).

    Returns:
        List[Dict]: Lista de casos de spoofing detectados
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Buscar MACs duplicadas
    cursor.execute(
        """
    SELECT MAC, GROUP_CONCAT(ip, ', ') as ips, COUNT(*) as contador
    FROM Dispositivos
    WHERE MAC IS NOT NULL
    GROUP BY MAC
    HAVING COUNT(*) > 1
    """
    )

    casos_spoofing = []

    for mac, ips_str, contador in cursor.fetchall():
        ips = ips_str.split(", ")

        # Extraer segmentos
        segmentos = set()
        for ip in ips:
            segmento = ".".join(ip.split(".")[:3])
            segmentos.add(segmento)

        # Si está en múltiples subredes = SPOOFING
        if len(segmentos) > 1:
            casos_spoofing.append(
                {
                    "mac": mac,
                    "ips": ips,
                    "segmentos": list(segmentos),
                    "severidad": "ALTA",
                }
            )

            print(f"\n[SPOOFING DETECTADO]")
            print(f"  MAC: {mac}")
            print(f"  Aparece en {len(segmentos)} subredes diferentes:")
            for seg in segmentos:
                ips_seg = [ip for ip in ips if ip.startswith(seg)]
                print(f"    - Segmento {seg}: {', '.join(ips_seg)}")

    conn.close()
    return casos_spoofing


if __name__ == "__main__":
    print("=== DETECTOR DE SPOOFING SIMPLE ===\n")
    casos = detectar_spoofing_simple()
    print(f"\nTotal casos detectados: {len(casos)}")
