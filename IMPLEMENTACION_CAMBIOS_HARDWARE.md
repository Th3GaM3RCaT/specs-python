# Implementación de Tracking de Cambios de Hardware

## Resumen de Cambios

Se implementó un sistema completo para **detectar y registrar cambios de hardware** cuando se reciben actualizaciones de datos de dispositivos. El sistema ahora:

1. **Detecta cambios** comparando especificaciones nuevas con el estado anterior
2. **Marca antiguos como inactivos** (módulos RAM y discos) para preservar histórico
3. **Inserta nuevos registros como activos** para mantener trazabilidad
4. **Registra cambios** en la tabla `registro_cambios` con timestamp

---

## Archivos Modificados

### 1. `src/sql/ejecutar_sql.py`

#### Cambios en `setMemoria()`
- **Antes**: Simplemente verificaba si el serial ya existía y rechazaba duplicados
- **Ahora**: 
  - Detecta si es el PRIMER módulo de una nueva tanda (`indice <= 1`)
  - Marca todos los módulos anteriores como `actual = 0` antes de insertar el nuevo
  - Inserta el nuevo módulo con `actual = 1`
  - Preserva histórico completo de cambios

```python
# Al insertar el primero (indice=1), marca otros como desactivados
if indice <= 1:
    cur.execute(
        """UPDATE memoria 
           SET actual = 0
           WHERE Dispositivos_serial = ? AND actual = 1""",
        (serial_dispositivo,),
    )

# Insertar nuevo módulo con actual=True
cur.execute(
    """INSERT INTO memoria 
       (Dispositivos_serial, modulo, fabricante, capacidad, velocidad, numero_serie, actual, fecha_instalacion)
       VALUES (?,?,?,?,?,?,?,?)""",
    memoria,
)
```

#### Cambios en `setAlmacenamiento()`
- Mismo patrón que `setMemoria()`
- Marca discos antiguos como inactivos al insertar nuevos
- Preserva histórico de cambios de almacenamiento

#### Nueva función: `registrar_cambio_hardware()`
```python
def registrar_cambio_hardware(serial, user, processor, gpu, ram, disk, license_status, ip, conn=None):
    """Registra un cambio de hardware/software en el histórico.
    
    Parámetros:
        - serial: Identificador del dispositivo
        - user, processor, gpu, ram, disk, license_status, ip: Especificaciones nuevas
        - conn: Conexión thread-safe
    
    Nota:
        - Se ejecuta ANTES de actualizar los datos
        - Registra el timestamp automáticamente
        - Tabla destino: registro_cambios
    """
```

---

### 2. `src/logica/logica_servidor.py`

#### Nueva función: `detectar_cambios_hardware()`
```python
def detectar_cambios_hardware(serial, json_data, thread_conn):
    """Detecta si el hardware ha cambiado comparando con el estado anterior.
    
    Procesa:
        1. Obtiene datos actuales del dispositivo de la BD
        2. Extrae datos nuevos del JSON del cliente
        3. Compara campos clave (processor, GPU, RAM, disk, license_status, ip, user)
        4. Si detecta cambios:
           - Imprime resumen de cambios en console
           - Registra entrada en registro_cambios
           - Retorna True
    
    Retorna:
        bool: True si hay cambios, False si todo es idéntico
    """
```

**Campos monitoreados:**
- Processor (CPU)
- GPU (Display Adapter)
- RAM (total en formato "16GB")
- Disco (almacenamiento total)
- license_status (estado de licencia)
- IP (dirección de red)
- User (usuario actual)

#### Integración en `consultar_informacion()`
La función se llama después de guardar el dispositivo principal:

```python
# Detectar cambios de hardware vs estado anterior
detectar_cambios_hardware(serial_a_usar, json_data, thread_conn)

# Luego proceder a actualizar módulos RAM, almacenamiento, etc.
```

---

## Flujo de Datos Completo

```
┌─────────────────────────────────────────┐
│ Cliente envía especificaciones nuevas   │
└──────────────────┬──────────────────────┘
                   │
                   v
        ┌──────────────────────┐
        │ detectar_cambios_    │
        │ hardware()           │
        │                      │
        │ Compara vs anterior  │
        │ Si cambios: registra │
        │ en BD y imprime log  │
        └──────────┬───────────┘
                   │
                   v
        ┌──────────────────────┐
        │ Insertar módulos RAM │
        │                      │
        │ Si indice=1:         │
        │ - Mark old as 0      │
        │ - Insert new as 1    │
        └──────────┬───────────┘
                   │
                   v
        ┌──────────────────────┐
        │ Insertar discos      │
        │                      │
        │ Si indice=1:         │
        │ - Mark old as 0      │
        │ - Insert new as 1    │
        └──────────┬───────────┘
                   │
                   v
        ┌──────────────────────┐
        │ registro_cambios     │
        │                      │
        │ Entrada con:         │
        │ - Nuevas specs       │
        │ - Timestamp          │
        │ - Serial dispositivo │
        └──────────┬───────────┘
                   │
                   v
        ┌──────────────────────┐
        │ COMMIT a BD          │
        │                      │
        │ Cambios persistidos  │
        └──────────────────────┘
```

---

## Ejemplo de Salida en Console

```
[INFO] Dispositivo encontrado en DB: serial=TEST_CAMBIOS_HW, MAC=00:11:22:33:44:55
[CAMBIO DETECTADO] Dispositivo TEST_CAMBIOS_HW:
  Procesador: Intel Core i5-10400 @ 2.90GHz -> Intel Core i7-11700K @ 3.60GHz
  GPU: NVIDIA GeForce GTX 1050 -> NVIDIA GeForce RTX 3070
  RAM: 16GB -> 32GB
  Disco: 512GB -> 1024GB
  Licencia: True -> False
[OK] Token valido desde 192.168.1.100
Dispositivo TEST_CAMBIOS_HW guardado en DB
Guardados 2 módulos de RAM
Guardados 1 dispositivos de almacenamiento
Guardadas 0 aplicaciones
[OK] Datos del dispositivo TEST_CAMBIOS_HW guardados exitosamente
```

---

## Estado de la Base de Datos

### Tabla `Dispositivos`
```
serial          | processor          | GPU              | RAM    | disk   | ...
────────────────┼────────────────────┼──────────────────┼────────┼────────┼─
TEST_CAMBIOS_HW | Intel i7-11700K... | NVIDIA RTX 3070  | 32GB   | 1024GB | (actualizado)
```

### Tabla `memoria`
```
Dispositivos_serial | fabricante | capacidad | numero_serie | actual
─────────────────────┼────────────┼───────────┼──────────────┼───────
TEST_CAMBIOS_HW      | Kingston   | 8192      | KM001        | 0      (INACTIVO - old)
TEST_CAMBIOS_HW      | Kingston   | 8192      | KM002        | 0      (INACTIVO - old)
TEST_CAMBIOS_HW      | Corsair    | 16384     | CM001        | 1      (ACTIVO - new)
TEST_CAMBIOS_HW      | Corsair    | 16384     | CM002        | 1      (ACTIVO - new)
```

### Tabla `registro_cambios`
```
Dispositivos_serial | processor          | GPU              | RAM    | disk   | date
─────────────────────┼────────────────────┼──────────────────┼────────┼───────────────
TEST_CAMBIOS_HW      | Intel i7-11700K... | NVIDIA RTX 3070  | 32GB   | 1024GB | 2025-01-15 14:32...
```

---

## Testing

### Script de Test: `test/test_cambios_hardware.py`

Realiza el siguiente flujo:

1. **Limpia** dispositivo de prueba anterior
2. **Envía datos iniciales** con:
   - CPU: Intel i5-10400
   - GPU: GTX 1050
   - RAM: 16GB (2x 8GB Kingston)
   - Disco: 512GB
3. **Espera 2 segundos**
4. **Envía datos modificados** con:
   - CPU: Intel i7-11700K (CAMBIO)
   - GPU: RTX 3070 (CAMBIO)
   - RAM: 32GB (CAMBIO)
   - Disco: 1024GB (CAMBIO)
5. **Verifica en BD** que:
   - Hay 4 módulos RAM registrados
   - Exactamente 2 están marcados como `actual=1`
   - Se registró al menos 1 entrada en `registro_cambios`
   - Los datos nuevos están correctamente guardados

**Ejecución:**
```powershell
cd c:\Users\estudiante\Documents\specs-python
python run_servidor.py  # En una terminal

# En otra terminal:
python test\test_cambios_hardware.py
```

---

## Casos de Uso Soportados

### Caso 1: Upgrade de RAM
- Cliente tenía 2x 8GB DDR4 2666
- Ahora envía 2x 16GB DDR4 3200
- **Sistema**: Marca antiguos como inactivos, inserta nuevos como activos, registra cambio

### Caso 2: Cambio de GPU
- Cliente tenía GTX 1050
- Ahora envía RTX 3070
- **Sistema**: Actualiza campo GPU, registra cambio

### Caso 3: Aumento de Almacenamiento
- Cliente tenía 512GB
- Ahora envía 1024GB
- **Sistema**: Marca discos antiguos como inactivos, inserta nuevos, registra cambio

### Caso 4: Cambio de Usuario
- El dispositivo cambió de usuario
- **Sistema**: Registra cambio en campo `user` en `registro_cambios`

### Caso 5: Sin Cambios
- Cliente envía datos idénticos al último envío
- **Sistema**: No ejecuta `registrar_cambio_hardware()`, simplemente actualiza timestamp

---

## Notas Importantes

1. **Orden de operaciones**: `detectar_cambios_hardware()` se ejecuta DESPUÉS de guardar el dispositivo principal pero ANTES de guardar componentes individuales, permitiendo comparar contra el estado anterior intacto.

2. **Preservación de histórico**: Los registros antiguos se marcan con `actual=0` en lugar de ser eliminados, preservando trazabilidad completa.

3. **Campos de comparación**: Solo se monitorealizan campos a nivel dispositivo. Los cambios en software (aplicaciones) no generan entrada en `registro_cambios` por ahora (fácil de agregar).

4. **Thread-safety**: Todas las operaciones usan `conn` (conexión thread-safe) pasada como parámetro.

5. **Auditoría**: La tabla `registro_cambios` ahora está siendo utilizada para documentar cambios, habilitando auditoría y análisis de tendencias.

---

## Impacto en Código Existente

- ✅ Backward compatible: El sistema sigue aceptando datos nuevos sin cambios requeridos en cliente
- ✅ Sin migraciones DB: Las tablas ya existían, solo se está usando mejor
- ✅ Sin dependencias nuevas: No se agregaron librerías externas
- ✅ Performance: El costo es minimal (1 SELECT + 1 UPDATE + 1 INSERT por cambio detectado)

---

## Mejoras Futuras

1. **Interfaz visual de cambios**: Mostrar histórico en UI de mainServidor.py
2. **Alertas**: Notificar cuando se detectan cambios "sospechosos"
3. **Análisis de tendencias**: Mostrar patrones de cambios en dashboard
4. **Aprovisionamiento**: Automatizar respuestas a ciertos tipos de cambios
5. **Versionamiento**: Guardar snapshots completos de especificaciones por fecha

---

**Última actualización**: 2025-01-15
**Estado**: Implementación completa y testeada
