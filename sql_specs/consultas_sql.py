import sys
import sqlite3
from typing import Literal, Optional
from os.path import join

connection = sqlite3.connect("specs.db")
cursor = connection.cursor()

#pasar todas las consultas sql solo con esta funcion
def abrir_consulta(
    consulta_sql: Literal[
        "activo-select.sql",
        "almacenamiento-select.sql",
        "aplicaciones-select.sql",
        "Dispositivos-select.sql",
        "informacion-diagnostico-select.sql",
        "memoria-select.sql",
        "registro-cambios-select.sql",
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
        base_path = join(sys._MEIPASS, "sql_specs", "statement") # type: ignore
    else:
        base_path = join("sql_specs", "statement")
    
    ruta = join(base_path, consulta_sql)
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


def setaplication(aplicacion = tuple()):
    #consultar si existe por nombre y publisher, de ser asi reemplazar por version
    sql, params = abrir_consulta("aplicaciones-select.sql",{"name":aplicacion[1],"publisher":aplicacion[3]})
    cursor.execute(sql,params)
    data = aplicacion
    if cursor.fetchone():
        cursor.execute("""UPDATE aplicaciones 
                       SET version = ?
                       WHERE name = ? AND publisher = ?""",
                       (data[2],data[1],data[3]))
        return
    cursor.execute("""INSERT INTO Dispositivos 
                   VALUES (?,?,?,?,?)""",
                   (data[0],data[1],data[2],data[3]))    



def setAlmacenamiento(almacenamiento = tuple(), indice = 1):
    data = almacenamiento
    #consultar si existe por nombre y capacidad, de ser asi return
    sql, params = abrir_consulta("almacenamiento-select.sql", {"nombre": data[1], "capacidad": data[2]})
    cursor.execute(sql, params)
    if cursor.fetchone():
        return
    #si indice es 1, cambiar el valor actual a false donde serial coincida
    if indice <= 1:
        cursor.execute("""UPDATE almacenamiento 
                       SET actual = ?
                       WHERE Dispositivos_serial = ?""",
                       (False,data[0]))
    cursor.execute("""INSERT INTO almacenamiento 
                   VALUES (?,?,?,?,?)""",
                   (data[0],data[1],data[2],data[3],data[4],data[5]))


def setMemoria(memoria = tuple(), indice = 1):
    data = memoria
    #consultar si existe por numero_serie, de ser asi return
    sql, params = abrir_consulta("memoria-select.sql", {"numero_serie": data[3]})
    cursor.execute(sql, params)
    if cursor.fetchone():
        return
    #si indice es 1, cambiar el valor actual a false donde serial coincida
    if indice <= 1:
        cursor.execute("""UPDATE memoria 
                       SET actual = ?
                       WHERE Dispositivos_serial = ?""",
                       (False,data[0]))
    cursor.execute("""INSERT INTO memoria 
                   VALUES (?,?,?,?,?)""",
                   (data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7]))
    







def setInformeDiagnostico(informes = tuple()):
    data = informes
    cursor.execute("""INSERT INTO informacion_diagnostico 
                   VALUES (?,?,?,?,?)""",
                   (data[0],data[1],data[2],data[3],data[4]))#listo
    
def setResgistro_cambios(registro = tuple()):
    data = registro
    cursor.execute("""INSERT INTO registro_cambios 
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                   (data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7],data[8],data[9]))#listo

def setDevice(info_dispositivo = tuple()):
    data = info_dispositivo
    cursor.execute("""INSERT INTO Dispositivos 
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(serial) DO UPDATE SET""",(
            data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7],data[8],data[9],data[10],data[11]
    ))#listo

def setActive(dispositivoEstado = tuple()):
    data = dispositivoEstado
    cursor.execute("""INSERT INTO activo 
                   VALUES (?,?,?)
                   ON CONFLICT(Dispositivos_serial) DO UPDATE SET""", (
                       data[0],data[1],data[2]
                       ))#listo


#ejemplo de uso
#abrir_consulta("Dispositivos-select.sql","serial","=","'12345'")