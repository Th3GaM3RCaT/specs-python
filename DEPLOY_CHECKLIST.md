# Checklist de Implementación - Tracking de Cambios de Hardware

## Pre-Deploy Verification

- [ ] No hay cambios no commitados en Git
  ```powershell
  git status  # Debe estar limpio (clean working tree)
  ```

- [ ] Base de datos existe
  ```powershell
  Test-Path data\specs.db  # Debe retornar True
  ```

- [ ] Tabla `registro_cambios` existe
  ```powershell
  python -c "import sqlite3; c = sqlite3.connect('data/specs.db'); print('OK' if c.execute('SELECT 1 FROM registro_cambios LIMIT 1').fetchone() else 'ERROR')"
  ```

## Archivos Modificados (Verificar)

- [ ] [ejecutar_sql.py](src/sql/ejecutar_sql.py)
  - [ ] Función `setMemoria()` tiene lógica de marcar como inactivos
  - [ ] Función `setAlmacenamiento()` tiene lógica de marcar como inactivos
  - [ ] Nueva función `registrar_cambio_hardware()` existe
  - [ ] Imports incluyen `from datetime import datetime`

- [ ] [logica_servidor.py](src/logica/logica_servidor.py)
  - [ ] Nueva función `detectar_cambios_hardware()` existe (línea ~530)
  - [ ] Función `consultar_informacion()` llama `detectar_cambios_hardware()`
  - [ ] El llamado es DESPUÉS de `setDevice()` pero ANTES de `setMemoria()`

- [ ] [copilot-instructions.md](.github/copilot-instructions.md)
  - [ ] Nueva sección "Pattern 6: Detección y Tracking" existe
  - [ ] Common Pitfall #15 menciona `detectar_cambios_hardware()`

- [ ] Nuevos archivos de documentación:
  - [ ] [IMPLEMENTACION_CAMBIOS_HARDWARE.md](IMPLEMENTACION_CAMBIOS_HARDWARE.md)
  - [ ] [HARDWARE_CHANGES_QUICK_REF.md](HARDWARE_CHANGES_QUICK_REF.md)
  - [ ] [test/test_cambios_hardware.py](test/test_cambios_hardware.py)

## Test Manual

### 1. Limpieza Pre-Test
```powershell
# Eliminar BD anterior si existe
Remove-Item data\specs.db -Force -ErrorAction SilentlyContinue

# Crear BD nueva
python -c "from src.sql.ejecutar_sql import inicializar_db; print('DB OK')"
```

### 2. Iniciar Servidor
```powershell
# Terminal 1
python run_servidor.py

# Esperar mensaje: "[OK] Base de datos creada correctamente"
# Esperar mensaje: "Servidor TCP escuchando en puerto 5255"
```

### 3. Ejecutar Test
```powershell
# Terminal 2
python test\test_cambios_hardware.py

# Esperar resultado:
# [OK] Dispositivo eliminado de la BD
# [ENVÍO] Conectando a 127.0.0.1:5255...
# [OK] Datos enviados al servidor
# [VERIFICAR] Consultando datos del dispositivo TEST_CAMBIOS_HW...
# ... (datos iniciales)
# [PASO 2] Envío con cambios...
# ... (datos modificados)
# [VALIDACIONES]
#   [OK] Módulos RAM registrados correctamente
#   [OK] Los módulos antiguos se marcaron como inactivos
#   [OK] Se registraron X cambio(s) de hardware
# RESULTADO: EXITO
```

### 4. Verificar BD Manualmente
```powershell
# Terminal 3
python -c @"
import sqlite3
conn = sqlite3.connect('data/specs.db')
cur = conn.cursor()

print('[DISPOSITIVO]')
cur.execute('SELECT serial, processor, GPU FROM Dispositivos WHERE serial = \"TEST_CAMBIOS_HW\"')
print(cur.fetchone())

print('[MEMORIA - Activos]')
cur.execute('SELECT COUNT(*) FROM memoria WHERE Dispositivos_serial = \"TEST_CAMBIOS_HW\" AND actual = 1')
print(f'Activos: {cur.fetchone()[0]}')

cur.execute('SELECT COUNT(*) FROM memoria WHERE Dispositivos_serial = \"TEST_CAMBIOS_HW\" AND actual = 0')
print(f'Inactivos: {cur.fetchone()[0]}')

print('[CAMBIOS]')
cur.execute('SELECT COUNT(*) FROM registro_cambios WHERE Dispositivos_serial = \"TEST_CAMBIOS_HW\"')
print(f'Registrados: {cur.fetchone()[0]}')
"@
```

## Rollback Plan (Si algo falla)

```powershell
# Revertir cambios en Git
git checkout src/sql/ejecutar_sql.py
git checkout src/logica/logica_servidor.py
git checkout .github/copilot-instructions.md

# Eliminar nuevos archivos
Remove-Item IMPLEMENTACION_CAMBIOS_HARDWARE.md
Remove-Item HARDWARE_CHANGES_QUICK_REF.md
Remove-Item test\test_cambios_hardware.py

# Reiniciar servidor
git status  # Debe mostrar lo revertido
```

## Performance Impact

- **CPU**: Mínimo (~1ms por cambio detectado, 1 SELECT + 1 UPDATE + 1 INSERT)
- **Memory**: Negativo (no hay estructuras nuevas en memoria)
- **Disk**: Negligible (1-2 KB adicionales por cambio en BD)
- **Network**: Ninguno (todo es local en servidor)

## Security Considerations

- ✅ `registrar_cambio_hardware()` usa `conn` parametrizado (SQL injection safe)
- ✅ `detectar_cambios_hardware()` compara strings, no ejecuta código
- ✅ `setMemoria()` y `setAlmacenamiento()` mantienen validación existente
- ✅ No nuevos puntos de entrada de red
- ✅ No nuevas dependencias externas

## Production Deployment

### Opción A: Rolling Update (recomendado)
```powershell
# 1. En servidor actual:
git pull origin main  # Obtener cambios

# 2. Reiniciar servidor (clientes pueden reconectar):
Restart-Service -Name "SpecsNet-Servidor" -Force

# 3. Clientes seguirán funcionando sin cambios
```

### Opción B: Blue-Green (máximo safety)
```powershell
# 1. Preparar servidor new (puerto 5256 temporalmente)
# 2. Ejecutar tests en nuevo puerto
# 3. Cambiar DNS/config para apuntar a nuevo servidor
# 4. Monitorear por 24h
# 5. Apagar servidor antiguo
```

## Post-Deploy Verification

- [ ] Servidor inicia sin errores
  ```
  "[OK] Base de datos creada correctamente" debe aparecer
  ```

- [ ] Primer cliente conecta exitosamente
  - [ ] Log muestra `[OK] Token valido`
  - [ ] Datos aparecen en tabla UI

- [ ] Segundo envío del mismo cliente detecta cambios
  - [ ] Log muestra `[CAMBIO DETECTADO]` si hay cambios
  - [ ] BD muestra componentes antiguos con `actual=0`

- [ ] Histórico es consultable
  ```sql
  SELECT * FROM registro_cambios LIMIT 1
  ```

## Monitoreo Continuo

```powershell
# Archivo de log sugerido: agregar a mainServidor.py
# Ver qué dispositivos tienen más cambios:

python -c @"
import sqlite3
conn = sqlite3.connect('data/specs.db')
cur = conn.cursor()
cur.execute('''
    SELECT Dispositivos_serial, COUNT(*) as cambios
    FROM registro_cambios
    GROUP BY Dispositivos_serial
    ORDER BY cambios DESC
    LIMIT 10
''')
print('Top 10 dispositivos con más cambios:')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]} cambios')
"@
```

---

## Contacto / Soporte

Si hay errores durante test:

1. Verificar que servidor está corriendo (`netstat -an | grep 5255`)
2. Verificar que DB tiene tabla `registro_cambios` (SQL error de otro lado)
3. Revisar console del servidor para tracebacks
4. Check `data/specs.db` no está corrupida

**Last updated**: 2025-01-15
