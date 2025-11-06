#type: ignore
"""
Integración del Monitor de Tendencias en logica_servidor.py
==========================================================

Solo agregar ESTAS LÍNEAS en el lugar correcto.
"""

# ============================================
# PASO 1: Import al inicio del archivo
# ============================================

# Después de otros imports, agregar:
from logica.monitor_tendencias import verificar_recursos_dispositivo


# ============================================
# PASO 2: En la función que procesa datos del cliente
# ============================================

# Buscar la función consultar_informacion() en logica_servidor.py
# Después de guardar los datos en la DB, agregar:

def consultar_informacion(conn, addr):
    # ... código existente que recibe y guarda datos ...
    
    # Después de insertar en DB exitosamente:
    serial = json_data.get("SerialNumber", "UNKNOWN") 
    
    # AGREGAR ESTAS LÍNEAS:
    # Verificar tendencias de recursos
    alertas = verificar_recursos_dispositivo(serial, json_data)
    
    if alertas:
        for alerta in alertas:
            print(f"\n[ALERTA] {alerta['tipo']} SATURADO")
            print(f"  Dispositivo: {alerta['nombre']} ({alerta['serial']})")
            print(f"  Promedio: {alerta['promedio']:.1f}%")
            print(f"  Valores: {alerta['valores']}")
            print(f"  Umbral: {alerta['umbral']}%")
            
            # Aquí puedes agregar notificación visual, email, etc.
            # Por ahora solo imprime en consola


# ============================================
# EJEMPLO COMPLETO DE INTEGRACIÓN
# ============================================

"""
En logica_servidor.py, línea ~400 (aproximadamente):

def consultar_informacion(conn: socket.socket, addr):
    buffer = b""
    
    # ... recibir datos del cliente ...
    
    json_data = loads(buffer.decode("utf-8"))
    serial = json_data.get("SerialNumber")
    
    # Guardar en DB
    sql.cursor.execute("INSERT INTO Dispositivos ...")
    sql.connection.commit()
    
    # ✅ AGREGAR AQUÍ:
    from logica.monitor_tendencias import verificar_recursos_dispositivo
    alertas = verificar_recursos_dispositivo(serial, json_data)
    
    if alertas:
        print(f"\\n{'='*60}")
        print(f"ALERTAS DE RECURSOS DETECTADAS ({len(alertas)})")
        print('='*60)
        
        for alerta in alertas:
            print(f"\\n[{alerta['tipo']}] {alerta['nombre']}")
            print(f"  Serial: {alerta['serial']}")
            print(f"  Promedio 3 consultas: {alerta['promedio']:.1f}%")
            print(f"  Umbral: {alerta['umbral']}%")
            print(f"  Timestamp: {alerta['timestamp']}")
        
        print('='*60)
    
    conn.close()
"""


# ============================================
# CONFIGURAR UMBRALES (OPCIONAL)
# ============================================

"""
Si quieres cambiar los umbrales por defecto:

from logica.monitor_tendencias import MonitorTendencias

# Cambiar umbrales globalmente
MonitorTendencias.UMBRAL_RAM = 80.0  # %
MonitorTendencias.UMBRAL_CPU = 85.0  # %
MonitorTendencias.UMBRAL_DISCO = 90.0  # %
MonitorTendencias.CONSULTAS_REQUERIDAS = 5  # Número de consultas

# O crear instancia personalizada:
monitor = MonitorTendencias()
monitor.UMBRAL_RAM = 75.0
"""


# ============================================
# VER DISPOSITIVOS EN SEGUIMIENTO
# ============================================

"""
Para ver qué dispositivos están siendo monitoreados:

from logica.monitor_tendencias import MonitorTendencias

monitor = MonitorTendencias()
seguimiento = monitor.obtener_dispositivos_en_seguimiento()

for item in seguimiento:
    print(f"{item['serial']} - {item['tipo']}")
    print(f"  Mediciones: {item['mediciones']}/{MonitorTendencias.CONSULTAS_REQUERIDAS}")
    print(f"  Promedio: {item['promedio']}%")
    print(f"  Faltan: {item['faltan']} consultas para alerta")
"""
