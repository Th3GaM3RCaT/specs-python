# Troubleshooting: Compilación con PyInstaller

## Problema: "ModuleNotFoundError: No module named 'logica'"

### Síntoma

Al ejecutar el `.exe` compilado con PyInstaller, aparece el error:

```
Traceback (most recent call last):
  File "specs.py", line 4, in <module>
ModuleNotFoundError: No module named 'logica'
```

### Causa Raíz

PyInstaller no puede resolver imports relativos cuando el código está dentro de una estructura de carpetas (`src/`). 

En `src/specs.py`:
```python
from logica.logica_Hilo import Hilo  # ❌ PyInstaller no encuentra 'logica/'
```

PyInstaller busca módulos en el Python path, pero no sabe que debe buscar en `src/logica/`.

---

## Solución: Flag `--paths=src`

Agregar el flag `--paths=src` al comando de PyInstaller:

```powershell
pyinstaller --onefile --noconsole --name "SpecsCliente" \
  --paths=src \  # ✅ Agrega src/ al Python path
  src/specs.py
```

Esto le dice a PyInstaller:
- "Busca módulos también en el directorio `src/`"
- Ahora puede resolver `from logica.xxx` → `src/logica/xxx.py`

---

## Comando Completo Correcto

### Cliente:

```powershell
pyinstaller --onedir --noconsole --name "SpecsCliente" \
  --add-data "src/ui/*.ui;ui" \
  --hidden-import=wmi \
  --hidden-import=psutil \
  --hidden-import=getmac \
  --hidden-import=windows_tools.installed_software \
  --paths=src \
  src/specs.py
```

### Servidor:

```powershell
pyinstaller --onedir --noconsole --name "SpecsServidor" \
  --add-data "src/sql/statement/*.sql;sql/statement" \
  --add-data "src/ui/*.ui;ui" \
  --hidden-import=wmi \
  --hidden-import=psutil \
  --paths=src \
  src/servidor.py
```

### ¿Por qué `--onedir` y no `--onefile`?

| Característica | `--onefile` | `--onedir` ⭐ |
|----------------|-------------|------------|
| **Velocidad de inicio** | ❌ 5-15 segundos | ✅ <1 segundo |
| **Motivo de lentitud** | Desempaqueta todo a temp cada vez | Todo ya desempaquetado |
| **Distribución** | ✅ Un solo .exe | ❌ Carpeta completa (.zip) |
| **Tamaño** | ~47 MB | ~60 MB (carpeta) |
| **Debugging** | ❌ Difícil | ✅ Fácil (archivos visibles) |
| **Uso recomendado** | Distribución única | Aplicaciones frecuentes |

**Conclusión**: Para aplicaciones que se ejecutan frecuentemente (como este cliente/servidor que puede ejecutarse varias veces al día), `--onedir` es **mucho mejor** por la velocidad de inicio.

---

## Uso de Scripts Automatizados

Para evitar escribir comandos largos, usa los scripts en `scripts/`:

```powershell
# Habilitar ejecución de scripts (una vez)
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# Compilar cliente
.\scripts\build_cliente.ps1

# Compilar servidor
.\scripts\build_servidor.ps1
```

Los scripts ya incluyen todos los flags necesarios, incluyendo `--paths=src`.

---

## Verificación de Compilación

### 1. Verificar que se creó el ejecutable:

```powershell
Test-Path "dist/SpecsCliente/SpecsCliente.exe"
```

**Esperado**: `True`

### 2. Verificar tamaño:

```powershell
$fileSize = (Get-Item "dist/SpecsCliente/SpecsCliente.exe").Length / 1MB
$folderSize = (Get-ChildItem "dist/SpecsCliente" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "Ejecutable: $([math]::Round($fileSize, 2)) MB"
Write-Host "Carpeta completa: $([math]::Round($folderSize, 2)) MB"
```

**Esperado**: 
- Ejecutable: ~0.5 MB (stub)
- Carpeta completa: ~60 MB

### 3. Probar ejecución:

```powershell
.\dist\SpecsCliente\SpecsCliente.exe
```

**Esperado**: La interfaz gráfica debe abrirse **instantáneamente** (< 1 segundo).

### 4. Probar modo tarea:

```powershell
.\dist\SpecsCliente\SpecsCliente.exe --tarea
```

**Esperado**: Debe escuchar broadcasts en background (sin GUI).

---

## Debugging: Ver Errores en Consola

Si el ejecutable falla silenciosamente, compílalo con `--console` para ver errores:

```powershell
pyinstaller --onedir --console --name "SpecsCliente_Debug" \
  --paths=src \
  src/specs.py
```

Ejecuta:

```powershell
.\dist\SpecsCliente_Debug\SpecsCliente_Debug.exe
```

Ahora verás una ventana de consola con los mensajes de error de Python.

---

## Errores Comunes y Soluciones

### Error: "FileNotFoundError: [Errno 2] No such file or directory: 'ui/specs_window.ui'"

**Causa**: No incluiste los archivos `.ui` con `--add-data`.

**Solución**:
```powershell
--add-data "src/ui/*.ui;ui"  # Copia archivos .ui al ejecutable
```

---

### Error: "ImportError: cannot import name 'consultas_sql'"

**Causa**: PyInstaller no encuentra los módulos en `src/sql/`.

**Solución**: Verificar que tienes `--paths=src`.

---

### Error: "sqlite3.OperationalError: unable to open database file"

**Causa**: La base de datos `specs.db` debe estar en `data/specs.db` relativo al ejecutable.

**Solución**: Asegúrate de que la carpeta `data/` existe junto a la carpeta del ejecutable:

```
dist/
├── SpecsCliente/
│   ├── SpecsCliente.exe
│   └── _internal/
└── data/
    └── specs.db  # ← Debe existir aquí (un nivel arriba)
```

O crea la carpeta data dentro de SpecsCliente:
```
dist/
└── SpecsCliente/
    ├── SpecsCliente.exe
    ├── _internal/
    └── data/
        └── specs.db  # ← También puede estar aquí
```

---

### Error: "Ejecutable inicia lento (5-15 segundos)"

**Causa**: Compilaste con `--onefile` que desempaqueta todo cada vez.

**Solución**: Recompilar con `--onedir`:

```powershell
# Eliminar build anterior
Remove-Item dist/SpecsCliente.exe -Force
Remove-Item build -Recurse -Force

# Recompilar con --onedir
pyinstaller --onedir --noconsole --name "SpecsCliente" --paths=src src/specs.py
```

**Resultado**: Inicio instantáneo (< 1 segundo).

---

### Error: "No module named 'wmi'"

**Causa**: PyInstaller no detectó la dependencia `wmi` automáticamente.

**Solución**:
```powershell
--hidden-import=wmi  # Fuerza la inclusión de wmi
```

---

## Estructura de Imports

### ✅ Correcto (Imports Absolutos):

```python
# En src/specs.py
from logica.logica_Hilo import Hilo
from logica.logica_specs import informe
from ui.specs_window_ui import Ui_MainWindow
```

Con `--paths=src`, PyInstaller puede resolver estos imports.

### ❌ Incorrecto (Imports Relativos):

```python
# En src/specs.py
from .logica.logica_Hilo import Hilo  # ❌ No funciona con PyInstaller
```

Los imports relativos (con `.`) no funcionan bien en ejecutables empaquetados.

---

## Alternativa: Usar `--onedir` en lugar de `--onefile` ⭐

**Recomendado para aplicaciones que se ejecutan frecuentemente.**

### ¿Por qué `--onedir` es mejor?

#### `--onefile` (NO recomendado para uso frecuente):
```
Usuario → Click en .exe
    ↓
PyInstaller desempaqueta TODO a carpeta temporal (5-15 seg)
    ↓
Ejecuta aplicación
    ↓
Usuario cierra app
    ↓
PyInstaller BORRA archivos temporales
    ↓
Próximo click → REPITE TODO EL PROCESO (otra vez 5-15 seg)
```

#### `--onedir` (⭐ Recomendado):
```
Usuario → Click en .exe
    ↓
Ejecuta directamente (< 1 segundo)
```

### Migrar de `--onefile` a `--onedir`:

```powershell
# Limpiar build anterior
Remove-Item dist/SpecsCliente.exe -Force
Remove-Item build -Recurse -Force

# Compilar con --onedir
pyinstaller --onedir --noconsole --name "SpecsCliente" \
  --add-data "src/ui/*.ui;ui" \
  --hidden-import=wmi \
  --hidden-import=psutil \
  --hidden-import=getmac \
  --hidden-import=windows_tools.installed_software \
  --paths=src \
  src/specs.py
```

Esto crea:
```
dist/
└── SpecsCliente/
    ├── SpecsCliente.exe  # Ejecutable principal (stub pequeño)
    └── _internal/        # Librerías (desempaquetadas permanentemente)
        ├── python313.dll
        ├── PySide6/
        ├── wmi.pyc
        └── ... (todos los módulos)
```

### Distribución:

Para distribuir, comprime la carpeta completa:

```powershell
Compress-Archive -Path "dist/SpecsCliente" -DestinationPath "SpecsCliente.zip"
```

El usuario descomprime y ejecuta `SpecsCliente/SpecsCliente.exe`.

### Ventajas de `--onedir`:

✅ **Inicio instantáneo** (< 1 segundo vs 5-15 segundos)  
✅ **Fácil debugging** (puedes ver los archivos .pyc, DLLs, etc.)  
✅ **Menos I/O** (no desempaqueta/borra cada vez)  
✅ **Mejor para aplicaciones frecuentes** (clientes, servidores)

### Desventajas de `--onedir`:

❌ **Más archivos** (~60 MB de carpeta vs 47 MB de .exe único)  
❌ **Distribución más compleja** (necesitas comprimir carpeta)

---

## Testing Completo

### Test 1: Modo GUI

```powershell
.\dist\SpecsCliente.exe
```

**Esperado**:
1. Ventana GUI se abre
2. Botón "Recopilar Especificaciones" funciona
3. Botón "Enviar al Servidor" funciona
4. Statusbar muestra mensajes de estado

### Test 2: Modo Tarea

```powershell
# Terminal 1: Iniciar servidor
.\dist\SpecsServidor.exe

# Terminal 2: Iniciar cliente en modo tarea
.\dist\SpecsCliente.exe --tarea
```

**Esperado**:
1. Cliente escucha broadcasts en puerto 37020
2. Cuando servidor anuncia IP, cliente envía datos automáticamente
3. Servidor recibe y guarda datos en `data/specs.db`

### Test 3: Verificar Logs

Si compilaste con `--console`, verás logs en la consola:

```
🔍 Buscando servidor (escuchando broadcasts en puerto 37020)...
✓ Servidor encontrado: 10.100.2.152
✓ Token de autenticación agregado
🔌 Conectando al servidor 10.100.2.152:5255...
✓ Datos enviados correctamente al servidor
```

---

## Referencias

- **PyInstaller Docs**: https://pyinstaller.org/en/stable/
- **`--paths` flag**: https://pyinstaller.org/en/stable/usage.html#cmdoption-p
- **Scripts de build**: `scripts/build_cliente.ps1`, `scripts/build_servidor.ps1`
- **README**: `README.md` (sección "Compilación")

---

**Última actualización**: Noviembre 2025
