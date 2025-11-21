"""
Monitor de Tendencias de Recursos
Detecta recursos saturados de forma persistente (3 consultas consecutivas).

Lógica:
- Captura datos cuando supera umbral (ej: RAM > 74%)
- Si 3 consultas consecutivas superan umbral → ALERTA
- Si una consulta baja del umbral → resetea contador
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional


class MonitorTendencias:
    """
    Monitorea tendencias de RAM, CPU y Almacenamiento.
    Alerta solo si hay saturación persistente (3 consultas consecutivas).
    """

    # Umbrales configurables
    UMBRAL_RAM = 74.0  # %
    UMBRAL_CPU = 74.0  # %
    UMBRAL_DISCO = 85.0  # %
    CONSULTAS_REQUERIDAS = 3  # Número de consultas consecutivas para alertar

    def __init__(self, db_path: str = "specs.db"):
        self.db_conn = sqlite3.connect(db_path)
        self.db_cursor = self.db_conn.cursor()
        self._crear_tabla_tendencias()

    def _crear_tabla_tendencias(self):
        """Crea tabla para almacenar histórico de tendencias"""
        self.db_cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS tendencias_recursos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dispositivo_serial VARCHAR NOT NULL,
            tipo_recurso VARCHAR NOT NULL,  -- 'RAM', 'CPU', 'DISCO'
            valor_porcentaje REAL NOT NULL,
            timestamp DATETIME NOT NULL,
            alerta_generada BOOLEAN DEFAULT 0,
            FOREIGN KEY (dispositivo_serial) REFERENCES Dispositivos(serial)
        )
        """
        )

        # Índice para consultas rápidas
        self.db_cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_tendencias_serial_tipo 
        ON tendencias_recursos(dispositivo_serial, tipo_recurso, timestamp DESC)
        """
        )

        self.db_conn.commit()

    def registrar_medicion(self, serial: str, tipo: str, porcentaje: float):
        """
        Registra una medición de recurso.

        Args:
            serial: Serial del dispositivo
            tipo: 'RAM', 'CPU' o 'DISCO'
            porcentaje: Valor porcentual (0-100)
        """
        self.db_cursor.execute(
            """
        INSERT INTO tendencias_recursos 
        (dispositivo_serial, tipo_recurso, valor_porcentaje, timestamp)
        VALUES (?, ?, ?, ?)
        """,
            (serial, tipo, porcentaje, datetime.now()),
        )
        self.db_conn.commit()

    def verificar_tendencia(self, serial: str, tipo: str) -> Optional[Dict]:
        """
        Verifica si hay tendencia de saturación (3 consultas consecutivas).

        Args:
            serial: Serial del dispositivo
            tipo: 'RAM', 'CPU' o 'DISCO'

        Returns:
            Dict con alerta si hay saturación persistente, None si no
        """
        # Obtener umbral según tipo
        umbral = {
            "RAM": self.UMBRAL_RAM,
            "CPU": self.UMBRAL_CPU,
            "DISCO": self.UMBRAL_DISCO,
        }.get(tipo, 74.0)

        # Obtener últimas N mediciones
        self.db_cursor.execute(
            """
        SELECT valor_porcentaje, timestamp, alerta_generada
        FROM tendencias_recursos
        WHERE dispositivo_serial = ?
        AND tipo_recurso = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
            (serial, tipo, self.CONSULTAS_REQUERIDAS),
        )

        mediciones = self.db_cursor.fetchall()

        # Necesitamos al menos N mediciones
        if len(mediciones) < self.CONSULTAS_REQUERIDAS:
            return None

        # Verificar si TODAS las últimas N mediciones superan el umbral
        valores = [m[0] for m in mediciones]
        todas_superan = all(v > umbral for v in valores)

        # Verificar si ya se generó alerta para estas mediciones
        ya_alertado = any(m[2] for m in mediciones)

        if todas_superan and not ya_alertado:
            # Marcar mediciones como alertadas
            self.db_cursor.execute(
                """
            UPDATE tendencias_recursos
            SET alerta_generada = 1
            WHERE dispositivo_serial = ?
            AND tipo_recurso = ?
            AND id IN (
                SELECT id FROM tendencias_recursos
                WHERE dispositivo_serial = ?
                AND tipo_recurso = ?
                ORDER BY timestamp DESC
                LIMIT ?
            )
            """,
                (serial, tipo, serial, tipo, self.CONSULTAS_REQUERIDAS),
            )
            self.db_conn.commit()

            # Obtener info del dispositivo
            self.db_cursor.execute(
                "SELECT Name FROM Dispositivos WHERE serial = ?", (serial,)
            )
            nombre = self.db_cursor.fetchone()
            nombre_host = nombre[0] if nombre else serial

            return {
                "tipo": tipo,
                "serial": serial,
                "nombre": nombre_host,
                "valores": valores,
                "promedio": sum(valores) / len(valores),
                "umbral": umbral,
                "timestamp": datetime.now(),
            }

        return None

    def limpiar_tendencia(self, serial: str, tipo: str):
        """
        Limpia el histórico de tendencias cuando el valor baja del umbral.
        Esto resetea el contador de consultas consecutivas.

        Args:
            serial: Serial del dispositivo
            tipo: 'RAM', 'CPU' o 'DISCO'
        """
        # Solo eliminar mediciones NO alertadas
        self.db_cursor.execute(
            """
        DELETE FROM tendencias_recursos
        WHERE dispositivo_serial = ?
        AND tipo_recurso = ?
        AND alerta_generada = 0
        """,
            (serial, tipo),
        )
        self.db_conn.commit()

    def procesar_actualizacion_dispositivo(
        self, serial: str, datos: Dict
    ) -> List[Dict]:
        """
        Procesa una actualización de dispositivo y verifica tendencias.

        Args:
            serial: Serial del dispositivo
            datos: Diccionario con datos del dispositivo (debe incluir porcentajes)

        Returns:
            List[Dict]: Lista de alertas generadas (vacía si no hay alertas)
        """
        alertas = []

        # Extraer porcentaje de RAM
        ram_percent_str = datos.get("Percentage virtual memory", "0%")
        try:
            ram_percent = float(ram_percent_str.strip().replace("%", ""))

            if ram_percent > self.UMBRAL_RAM:
                # Registrar medición
                self.registrar_medicion(serial, "RAM", ram_percent)

                # Verificar tendencia
                alerta = self.verificar_tendencia(serial, "RAM")
                if alerta:
                    alertas.append(alerta)
            else:
                # Si baja del umbral, limpiar histórico
                self.limpiar_tendencia(serial, "RAM")
        except:
            pass

        # Extraer porcentaje de CPU
        cpu_percent_str = datos.get("Total CPU Usage", "0%")
        try:
            cpu_percent = float(cpu_percent_str.strip().replace("%", ""))

            if cpu_percent > self.UMBRAL_CPU:
                self.registrar_medicion(serial, "CPU", cpu_percent)
                alerta = self.verificar_tendencia(serial, "CPU")
                if alerta:
                    alertas.append(alerta)
            else:
                self.limpiar_tendencia(serial, "CPU")
        except:
            pass

        # Extraer porcentaje de Disco (puede haber múltiples particiones)
        # Buscar todos los campos que contengan "Percentage" y no sean memoria
        for key, value in datos.items():
            if "Percentage" in key and "memory" not in key.lower():
                try:
                    disco_percent = float(value.strip().replace("%", ""))

                    if disco_percent > self.UMBRAL_DISCO:
                        # Usar key como identificador único para cada partición
                        tipo_disco = f"DISCO_{key}"
                        self.registrar_medicion(serial, tipo_disco, disco_percent)
                        alerta = self.verificar_tendencia(serial, tipo_disco)
                        if alerta:
                            alerta["particion"] = key
                            alertas.append(alerta)
                    else:
                        self.limpiar_tendencia(serial, f"DISCO_{key}")
                except:
                    pass

        return alertas

    def obtener_dispositivos_en_seguimiento(self) -> List[Dict]:
        """
        Obtiene lista de dispositivos que están siendo monitoreados.

        Returns:
            List[Dict]: Dispositivos con conteo de mediciones por tipo
        """
        self.db_cursor.execute(
            """
        SELECT 
            dispositivo_serial,
            tipo_recurso,
            COUNT(*) as mediciones,
            AVG(valor_porcentaje) as promedio,
            MAX(timestamp) as ultima_medicion
        FROM tendencias_recursos
        WHERE alerta_generada = 0
        GROUP BY dispositivo_serial, tipo_recurso
        HAVING mediciones > 0
        ORDER BY dispositivo_serial, tipo_recurso
        """
        )

        resultados = []
        for serial, tipo, count, avg, timestamp in self.db_cursor.fetchall():
            resultados.append(
                {
                    "serial": serial,
                    "tipo": tipo,
                    "mediciones": count,
                    "promedio": round(avg, 2),
                    "ultima_medicion": timestamp,
                    "faltan": max(0, self.CONSULTAS_REQUERIDAS - count),
                }
            )

        return resultados


# Función de integración simple
def verificar_recursos_dispositivo(
    serial: str, datos: Dict, db_path: str = "specs.db"
) -> List[Dict]:
    """
    Función helper para usar en logica_servidor.py

    Args:
        serial: Serial del dispositivo
        datos: Datos completos del dispositivo
        db_path: Ruta a la DB

    Returns:
        List[Dict]: Alertas generadas (vacía si no hay)
    """
    monitor = MonitorTendencias(db_path)
    alertas = monitor.procesar_actualizacion_dispositivo(serial, datos)
    monitor.db_conn.close()
    return alertas


if __name__ == "__main__":
    # Test
    print("=== TEST MONITOR DE TENDENCIAS ===\n")

    monitor = MonitorTendencias(":memory:")

    # Simular 3 consultas con RAM alta
    print("Simulando 3 consultas con RAM > 74%...")
    for i in range(3):
        datos = {
            "Percentage virtual memory": f"{80 + i}%",
            "Total CPU Usage": "50%",
            "Percentage": "60%",  # Disco
        }
        alertas = monitor.procesar_actualizacion_dispositivo("TEST123", datos)
        print(f"  Consulta {i+1}: RAM {80+i}% - Alertas: {len(alertas)}")

        if alertas:
            for alerta in alertas:
                print(f"    [ALERTA] {alerta['tipo']} saturado en {alerta['nombre']}")
                print(f"    Promedio últimas 3 consultas: {alerta['promedio']:.1f}%")

    print("\nSimulando consulta con RAM baja (resetea)...")
    datos_bajos = {
        "Percentage virtual memory": "50%",
        "Total CPU Usage": "30%",
        "Percentage": "55%",
    }
    alertas = monitor.procesar_actualizacion_dispositivo("TEST123", datos_bajos)
    print(f"  RAM 50% - Tendencia reseteada - Alertas: {len(alertas)}")

    print("\nDispositivos en seguimiento:")
    seguimiento = monitor.obtener_dispositivos_en_seguimiento()
    print(f"  Total: {len(seguimiento)}")
