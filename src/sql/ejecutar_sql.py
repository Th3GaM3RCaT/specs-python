import sys
import sqlite3
from typing import Literal, Optional

# Inicializar base de datos
def inicializar_db():
    """Crea las tablas de la base de datos si no existen."""
    from pathlib import Path
    
    # Detecta si está corriendo empaquetado con PyInstaller
    if hasattr(sys, "_MEIPASS"):
        meipass_path = getattr(sys, "_MEIPASS")
        base_path = Path(meipass_path) / "sql"
    else:
        # Buscar relativo al archivo actual
        base_path = Path(__file__).parent
    
    schema_path = base_path / "specs.sql"
    
    # Base de datos en carpeta data/
    if hasattr(sys, "_MEIPASS"):
        db_path = "specs.db"  # En empaquetado, junto al ejecutable
    else:
        db_path = Path(__file__).parent.parent.parent / "specs.db"
        db_path.parent.mkdir(exist_ok=True)
    
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        
        # Conectar y ejecutar schema
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        
        # Verificar si ya existen las tablas
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Dispositivos'")
        if not cur.fetchone():
            print("⚙ Inicializando base de datos...")
            cur.executescript(schema_sql)
            conn.commit()
            print("✓ Base de datos creada correctamente")
        
        conn.close()
    except Exception as e:
        print(f"⚠ Error inicializando base de datos: {e}")

# Inicializar DB al importar el módulo
inicializar_db()

# Path a la base de datos
from pathlib import Path
if hasattr(sys, "_MEIPASS"):
    DB_PATH = "specs.db"
else:
    DB_PATH = str(Path(__file__).parent.parent.parent / "data" / "specs.db")

connection = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = connection.cursor()

def get_thread_safe_connection():
    """
    Crea una nueva conexión SQLite para usar en hilos.
    Cada hilo debe usar su propia conexión.
    """
    return sqlite3.connect(DB_PATH, check_same_thread=False)

#pasar todas las consultas sql solo con esta funcion
def abrir_consulta(
    consulta_sql: Literal[
        "activo-select.sql",
        "almacenamiento-select.sql",
        "aplicaciones-select.sql",
        "Dispositivos-select.sql",
        "informacion_diagnostico-select.sql",
        "memoria-select.sql",
        "registro_cambios-select.sql",
    ],
    condiciones: Optional[dict] = None
) -> tuple[str, tuple]:
    """
    Devuelve la consulta SQL y los parámetros listos para cursor.execute().
    
    Args:
        consulta_sql: Nombre del archivo .sql
        condiciones: Diccionario de filtros {columna: valor}
    
    Returns:
        (consulta_sql_completa, tuple_de_parametros)
    """
    # Detecta si está corriendo empaquetado con PyInstaller
    if hasattr(sys, "_MEIPASS"):
        meipass_path = getattr(sys, "_MEIPASS")
        base_path = Path(meipass_path) / "sql" / "statement"
    else:
        base_path = Path(__file__).parent / "statement"
    
    ruta = base_path / consulta_sql
    with open(ruta, "r", encoding="utf-8") as f:
        statements = f.read().strip()
    
    params = ()
    if condiciones:
        # construir cláusula WHERE con placeholders
        clauses = [f"{col} = ?" for col in condiciones.keys()]
        # quitar ; final si existe
        if statements.endswith(";"):
            statements = statements[:-1]
        statements += "\nWHERE " + " AND ".join(clauses) + ";"
        params = tuple(condiciones.values())

    return statements, params

def setaplication(aplicacion=tuple()):
    """
    Inserta o actualiza una aplicación en la BD.
    
    Args:
        aplicacion: (Dispositivos_serial, name, version, publisher)
    """
    sql, params = abrir_consulta("aplicaciones-select.sql", {"name": aplicacion[1], "publisher": aplicacion[3]})
    cursor.execute(sql, params)
    
    if cursor.fetchone():
        # Actualizar versión si ya existe
        cursor.execute("""UPDATE aplicaciones 
                       SET version = ?
                       WHERE name = ? AND publisher = ?""",
                       (aplicacion[2], aplicacion[1], aplicacion[3]))
    else:
        # Insertar nueva aplicación
        cursor.execute("""INSERT INTO aplicaciones 
                       (Dispositivos_serial, name, version, publisher)
                       VALUES (?,?,?,?)""",
                       (aplicacion[0], aplicacion[1], aplicacion[2], aplicacion[3]))

def setAlmacenamiento(almacenamiento=tuple(), indice=1):
    """
    Inserta información de almacenamiento en la BD.
    
    Args:
        almacenamiento: (Dispositivos_serial, nombre, capacidad, tipo, actual, fecha_instalacion)
        indice: Si es 1, marca otros discos del dispositivo como no actuales
    """
    # Verificar si ya existe
    sql, params = abrir_consulta("almacenamiento-select.sql", {"nombre": almacenamiento[1], "capacidad": almacenamiento[2]})
    cursor.execute(sql, params)
    if cursor.fetchone():
        return  # Ya existe, no duplicar
    
    # Si es el primer disco, marcar otros como no actuales
    if indice <= 1:
        cursor.execute("""UPDATE almacenamiento 
                       SET actual = ?
                       WHERE Dispositivos_serial = ?""",
                       (False, almacenamiento[0]))
    
    # Insertar nuevo almacenamiento
    cursor.execute("""INSERT INTO almacenamiento 
                   (Dispositivos_serial, nombre, capacidad, tipo, actual, fecha_instalacion)
                   VALUES (?,?,?,?,?,?)""",
                   (almacenamiento[0], almacenamiento[1], almacenamiento[2], 
                    almacenamiento[3], almacenamiento[4], almacenamiento[5]))

def setMemoria(memoria=tuple(), indice=1):
    """
    Inserta información de módulo RAM en la BD.
    
    Args:
        memoria: (Dispositivos_serial, modulo, fabricante, capacidad, velocidad, numero_serie, actual, fecha_instalacion)
        indice: Si es 1, marca otros módulos del dispositivo como no actuales
    """
    # Verificar si ya existe por número de serie
    sql, params = abrir_consulta("memoria-select.sql", {"numero_serie": memoria[5]})
    cursor.execute(sql, params)
    if cursor.fetchone():
        return  # Ya existe, no duplicar
    
    # Si es el primer módulo, marcar otros como no actuales
    if indice <= 1:
        cursor.execute("""UPDATE memoria 
                       SET actual = ?
                       WHERE Dispositivos_serial = ?""",
                       (False, memoria[0]))
    
    # Insertar nuevo módulo de memoria
    cursor.execute("""INSERT INTO memoria 
                   (Dispositivos_serial, modulo, fabricante, capacidad, velocidad, numero_serie, actual, fecha_instalacion)
                   VALUES (?,?,?,?,?,?,?,?)""",
                   (memoria[0], memoria[1], memoria[2], memoria[3], 
                    memoria[4], memoria[5], memoria[6], memoria[7]))

def setInformeDiagnostico(informes = tuple()):
    """Inserta información de diagnóstico de dispositivo en la base de datos.
    
    Args:
        informes (tuple): Tupla con (serial_dispositivo, json_diagnostico, reporteDirectX, fecha)
                         Schema: Dispositivos_serial, json_diagnostico, reporteDirectX, fecha, id (AUTOINCREMENT)
    
    Returns:
        None
    """
    cursor.execute("""INSERT INTO informacion_diagnostico 
                   (Dispositivos_serial, json_diagnostico, reporteDirectX, fecha)
                   VALUES (?,?,?,?)""",
                   (informes[0], informes[1], informes[2], informes[3]))
    
def setRegistro_cambios(registro = tuple()):
    """Registra cambios de especificaciones de hardware/software de un dispositivo.
    
    Args:
        registro (tuple): Tupla con (serial_dispositivo, user, processor, GPU, RAM, disk, 
                         license_status, ip, date)
                         Schema: Dispositivos_serial, user, processor, GPU, RAM, disk, 
                         license_status, ip, date, id (AUTOINCREMENT)
    
    Returns:
        None
    """
    cursor.execute("""INSERT INTO registro_cambios 
                   (Dispositivos_serial, user, processor, GPU, RAM, disk, license_status, ip, date)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                   (registro[0], registro[1], registro[2], registro[3], registro[4], 
                    registro[5], registro[6], registro[7], registro[8]))

def setDevice(info_dispositivo = tuple()):
    """Inserta o actualiza información completa de un dispositivo usando UPSERT.
    
    Args:
        info_dispositivo (tuple): Tupla con (serial, DTI, user, MAC, model, processor, 
                                  GPU, RAM, disk, license_status, ip, activo)
                                  Schema completo de tabla Dispositivos (12 campos)
    
    Returns:
        None
    
    Note:
        Usa ON CONFLICT para actualizar si el serial ya existe. Este es el único caso
        donde UPSERT está justificado por la complejidad de los 12 campos a actualizar.
    """
    cursor.execute("""INSERT INTO Dispositivos 
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(serial) DO UPDATE SET
                       DTI = excluded.DTI,
                       user = excluded.user,
                       MAC = excluded.MAC,
                       model = excluded.model,
                       processor = excluded.processor,
                       GPU = excluded.GPU,
                       RAM = excluded.RAM,
                       disk = excluded.disk,
                       license_status = excluded.license_status,
                       ip = excluded.ip,
                       activo = excluded.activo""",(
            info_dispositivo[0], info_dispositivo[1], info_dispositivo[2], info_dispositivo[3],
            info_dispositivo[4], info_dispositivo[5], info_dispositivo[6], info_dispositivo[7],
            info_dispositivo[8], info_dispositivo[9], info_dispositivo[10], info_dispositivo[11]
    ))

def actualizar_serial_temporal(serial_real, mac):
    """Actualiza el serial temporal (TEMP_{MAC}) por el serial real del BIOS.
    
    Args:
        serial_real (str): Serial real obtenido del BIOS
        mac (str): MAC address del dispositivo (para buscar serial temporal)
    
    Returns:
        bool: True si se actualizó algún registro, False si no existía serial temporal
    
    Note:
        Esta función busca dispositivos con serial temporal basado en MAC
        (formato: TEMP_{MAC_sin_separadores}) y los actualiza con el serial real.
        También actualiza todas las tablas relacionadas.
    """
    if not serial_real or serial_real.startswith("TEMP"):
        return False  # No actualizar si el serial sigue siendo temporal
    
    if not mac:
        return False
    
    # Generar serial temporal esperado (formato usado al crear desde CSV)
    serial_temporal = f"TEMP_{mac.replace(':', '').replace('-', '')}"
    
    # Verificar si existe dispositivo con serial temporal
    cursor.execute("SELECT serial FROM Dispositivos WHERE serial = ?", (serial_temporal,))
    if not cursor.fetchone():
        return False  # No existe dispositivo con serial temporal
    
    print(f"[UPDATE] Actualizando serial temporal {serial_temporal} -> {serial_real}")
    
    # Actualizar todas las tablas relacionadas
    # 1. Dispositivos
    cursor.execute("""UPDATE Dispositivos 
                     SET serial = ? 
                     WHERE serial = ?""", (serial_real, serial_temporal))
    
    # 2. activo
    cursor.execute("""UPDATE activo 
                     SET Dispositivos_serial = ? 
                     WHERE Dispositivos_serial = ?""", (serial_real, serial_temporal))
    
    # 3. registro_cambios
    cursor.execute("""UPDATE registro_cambios 
                     SET Dispositivos_serial = ? 
                     WHERE Dispositivos_serial = ?""", (serial_real, serial_temporal))
    
    # 4. almacenamiento
    cursor.execute("""UPDATE almacenamiento 
                     SET Dispositivos_serial = ? 
                     WHERE Dispositivos_serial = ?""", (serial_real, serial_temporal))
    
    # 5. memoria
    cursor.execute("""UPDATE memoria 
                     SET Dispositivos_serial = ? 
                     WHERE Dispositivos_serial = ?""", (serial_real, serial_temporal))
    
    # 6. aplicaciones
    cursor.execute("""UPDATE aplicaciones 
                     SET Dispositivos_serial = ? 
                     WHERE Dispositivos_serial = ?""", (serial_real, serial_temporal))
    
    # 7. informacion_diagnostico
    cursor.execute("""UPDATE informacion_diagnostico 
                     SET Dispositivos_serial = ? 
                     WHERE Dispositivos_serial = ?""", (serial_real, serial_temporal))
    
    connection.commit()
    print(f"[OK] Serial actualizado exitosamente en todas las tablas")
    return True

def setActive(dispositivoEstado = tuple()):
    """Inserta estado de actividad de un dispositivo (encendido/apagado).
    
    Args:
        dispositivoEstado (tuple): Tupla con (serial_dispositivo, powerOn, date)
                                  Schema: Dispositivos_serial, powerOn, date 
                                  (sin id porque no tiene PRIMARY KEY AUTOINCREMENT)
    
    Returns:
        None
    
    Warning:
        SIEMPRE usar DELETE antes de INSERT para evitar duplicados (1 registro por dispositivo).
        Ver logica_servidor.py para implementación correcta.
    """
    cursor.execute("""INSERT INTO activo 
                   VALUES (?,?,?)""", (
                       dispositivoEstado[0], dispositivoEstado[1], dispositivoEstado[2]
                       ))

def set_dispositivo_inicial(ip, mac):
    """
    Inserta o actualiza un dispositivo con información básica (IP y MAC).
    Si la MAC ya existe, actualiza la IP.
    Si no existe, crea un nuevo registro con valores por defecto.
    """
    # Usar la MAC como clave temporal para el serial si no existe
    serial_provisional = mac 
    
    cursor.execute("""
        INSERT INTO Dispositivos (serial, MAC, ip, activo) 
        VALUES (?, ?, ?, ?)
        ON CONFLICT(MAC) DO UPDATE SET
            ip = excluded.ip;
    """, (serial_provisional, mac, ip, False))
    connection.commit()


#ejemplo de uso
#abrir_consulta("Dispositivos-select.sql","serial","=","'12345'")