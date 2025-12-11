# Hardware Change Tracking - Quick Reference

## ¿Qué cambió?

✅ **El sistema ahora detecta automáticamente cambios de hardware** cuando un dispositivo envía actualización de datos.

## Flujo Visual

```
[Cliente envía specs NUEVAS]
         ↓
    [Servidor recibe TCP]
         ↓
   [Valida + Parsea JSON]
         ↓
    [NUEVO] detectar_cambios_hardware()
    ├─ Compara vs estado anterior en BD
    ├─ Si hay cambios → registra en BD
    └─ Imprime resumen en console
         ↓
  [setMemoria + setAlmacenamiento]
    ├─ Si indice=1: Marca antiguos como actual=0
    └─ Inserta nuevos como actual=1
         ↓
    [commit() a SQLite]
         ↓
  [BD tiene histórico completo]
```

## Impacto en la BD

### Antes (problema):
```
RAM Modules para dispositivo XYZ:
┌─────────────────────────────────┐
│ Kingston 8GB (actual=1)         │ ← antiguo
│ Kingston 8GB (actual=1)         │ ← antiguo
│ Corsair 16GB (actual=1)         │ ← NUEVO
│ Corsair 16GB (actual=1)         │ ← NUEVO
└─────────────────────────────────┘
  ❌ 4 módulos "activos" (confuso)
  ❌ No se sabe cuál es el estado actual
  ❌ No hay histórico de cambios
```

### Después (solución):
```
RAM Modules para dispositivo XYZ:
┌─────────────────────────────────┐
│ Kingston 8GB (actual=0)         │ ← antiguo
│ Kingston 8GB (actual=0)         │ ← antiguo
│ Corsair 16GB (actual=1)         │ ← NUEVO
│ Corsair 16GB (actual=1)         │ ← NUEVO
└─────────────────────────────────┘
  ✅ Claramente 2 módulos activos
  ✅ Estado anterior preservado
  ✅ Cambio documentado en registro_cambios
```

## Funciones Nuevas

### En `src/sql/ejecutar_sql.py`:

#### `registrar_cambio_hardware()`
```python
sql.registrar_cambio_hardware(
    serial="DEVICE001",
    user="juan.perez",
    processor="Intel i7",
    gpu="RTX 3070",
    ram="32GB",
    disk="1024GB",
    license_status=True,
    ip="192.168.1.100",
    conn=thread_conn
)
# → Inserta fila en tabla registro_cambios con timestamp
```

### En `src/logica/logica_servidor.py`:

#### `detectar_cambios_hardware()`
```python
cambio_detectado = detectar_cambios_hardware(
    serial="DEVICE001",
    json_data={...},  # Datos del cliente
    thread_conn=conexion_sqlite
)

# Retorna:
# True si hubo cambios (e imprime resumen)
# False si no hubo cambios
```

## Ejemplo en Console

Cuando se envía data con cambios:

```
[INFO] Dispositivo encontrado en DB: serial=DEVICE001, MAC=00:11:22:33:44:55
[CAMBIO DETECTADO] Dispositivo DEVICE001:
  Procesador: Intel i5-10400 -> Intel i7-11700K
  GPU: GTX 1050 -> RTX 3070
  RAM: 16GB -> 32GB
  Disco: 512GB -> 1024GB
  Licencia: True -> False
[OK] Token valido desde 192.168.1.100
Dispositivo DEVICE001 guardado en DB
Guardados 2 módulos de RAM
Guardados 1 dispositivos de almacenamiento
[OK] Datos del dispositivo DEVICE001 guardados exitosamente
```

## Campos Monitoreados

✅ Se detectan cambios en:
- `Processor` (CPU)
- `Display Adapter` (GPU)
- `RAM` (total en formato "16GB")
- `Total Disk Size` (almacenamiento total)
- `license_status` (estado de licencia)
- `client_ip` (dirección IP)
- `User` (usuario del dispositivo)

❌ No se monitoredan (por ahora):
- Aplicaciones individuales (fácil de agregar)
- Versiones de apps
- Configuraciones específicas

## Testing

### Ejecutar test automático:

```powershell
# Terminal 1: Iniciar servidor
python run_servidor.py

# Terminal 2: Ejecutar test
python test\test_cambios_hardware.py
```

**Qué hace el test:**
1. Envía especificaciones iniciales (CPU i5, GPU GTX 1050, 16GB RAM, 512GB disco)
2. Espera 2 segundos
3. Envía especificaciones nuevas (CPU i7, GPU RTX 3070, 32GB RAM, 1024GB disco)
4. Verifica que:
   - Hay 4 módulos RAM en BD
   - Exactamente 2 están marcados como `actual=1`
   - Se registró al menos 1 cambio en `registro_cambios`

### Resultado esperado:
```
========================================
RESULTADO: EXITO - Sistema de cambios de hardware funciona correctamente
========================================
```

## Integración en Código Existente

### Si estás modificando `consultar_informacion()`:

**IMPORTANTE**: El orden de operaciones es crítico:

```python
# ✅ CORRECTO (en logica_servidor.py línea ~765)
sql.setDevice(datos_dispositivo, thread_conn)  # Guardar dispositivo principal
print(f"Dispositivo {serial_a_usar} guardado en DB")

# AQUÍ llamar detectar_cambios_hardware ANTES de componentes
detectar_cambios_hardware(serial_a_usar, json_data, thread_conn)

# AHORA guardar componentes (RAM, discos, etc.)
modulos_ram = parsear_modulos_ram(json_data)
for i, modulo in enumerate(modulos_ram, 1):
    sql.setMemoria(modulo, i, thread_conn)
```

```python
# ❌ INCORRECTO (no funciona el tracking)
sql.setMemoria(modulo1, 1, thread_conn)  # Guarda RAM primero
detectar_cambios_hardware(...)  # Luego intenta detectar (datos ya actualizados)
```

### Si modificas `setMemoria()` o `setAlmacenamiento()`:

**NO cambiar** el parámetro `indice`. Es crítico para:
- `indice=1`: Marca antiguos como inactivos
- `indice>1`: Acepta nuevos sin marcar como inactivos

```python
# Correcto: setMemoria maneja todo automáticamente
for i, modulo in enumerate(modulos_ram, 1):  # enumerate comienza en 1
    sql.setMemoria(modulo, i, thread_conn)
    
# Incorrecto: No marca antiguos como inactivos
for modulo in modulos_ram:
    sql.setMemoria(modulo, 999, thread_conn)  # indice > 1
```

## Mejoras Futuras

1. **UI Dashboard**: Mostrar histórico de cambios en mainServidor.py
2. **Alertas**: Enviar notificación cuando se detecten cambios sospechosos
3. **Análisis de tendencias**: Gráficas de evolución de hardware
4. **Aprovisionamiento**: Auto-responder a ciertos cambios
5. **Reportes**: Exportar histórico a Excel/PDF

## FAQ

**P: ¿Qué pasa si un dispositivo envía los mismos datos dos veces?**
R: El sistema detecta que NO hay cambios y NO crea entrada en `registro_cambios`. Solo actualiza timestamps.

**P: ¿Se pierden los datos antiguos?**
R: No. Quedan marcados como `actual=0` en la misma tabla. Es auditoría completa.

**P: ¿Qué pasa si falla la detección?**
R: El sistema sigue persistiendo datos normalmente. La detección es adicional, no crítica.

**P: ¿Puedo consultar el histórico de cambios?**
R: Sí, en la tabla `registro_cambios`:
```sql
SELECT * FROM registro_cambios 
WHERE Dispositivos_serial = 'DEVICE001' 
ORDER BY date DESC;
```

**P: ¿Cómo ignoro cambios en IP pero sí en CPU?**
R: Modificar `detectar_cambios_hardware()` línea ~545-552 para comentar la comparación de IP.

---

**Última actualización**: 2025-01-15
**Estado**: Implementación completa, testeada y documentada
