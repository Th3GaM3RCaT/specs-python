# ✅ REORGANIZACIÓN COMPLETADA

## 🎯 Resumen de Cambios

### Estructura Nueva

```
specs-python/
├── 📂 src/                         # TODO el código fuente
│   ├── specs.py, mainServidor.py
│   ├── logica/                      # Lógica de negocio
│   ├── datos/                       # Recolección de datos
│   ├── sql/                         # Base de datos
│   └── ui/                          # Interfaces Qt (.ui + _ui.py juntos)
│           
├── 📂 scripts/                     # Utilidades (build, sign, install)
├── 📂 tests/                       # Tests automatizados
├── 📂 docs/                        # Toda la documentación
├── 📂 config/                      # Configuración (security_config.py)
├── 📂 data/                        # Datos runtime (*.db, *.csv)
│           
├── run_cliente.py                   # Wrapper: ejecuta src/specs.py
├── run_servidor.py                  # Wrapper: ejecuta src/servidor.py
├── requirements.txt
└── README.md
```

### Archivos Movidos

| Antes | Después |
|-------|---------|
| `logica_*.py` (raíz) | `src/logica/` |
| `datos/` | `src/datos/` |
| `sql_specs/` | `src/sql/` |
| `ui/` | `src/ui/` |
| `*.ps1` scripts | `scripts/` |
| `test_connectivity.py` | `tests/` |
| `DISTRIBUCION*.md`, etc | `docs/` |
| `security_config.py` | `config/` |
| `specs.db`, `*.csv` | `data/` |

### Imports Actualizados

**Antes**:
```python
from logica_specs import LogicaSpecs
from ui.specs_window_ui import Ui_MainWindow
from sql_specs.consultas_sql import cursor
```

**Después**:
```python
from logica.logica_specs import LogicaSpecs  # Desde src/
from ui.specs_window_ui import Ui_MainWindow  # Desde src/
from sql.consultas_sql import cursor         # Desde src/
```

### Cambios en Base de Datos

- **Antes**: `specs.db` en raíz del proyecto
- **Después**: `data/specs.db` (carpeta dedicada)
- **PyInstaller**: Detecta automáticamente y usa path correcto

### Cambios en Seguridad

- **Antes**: `security_config.py` en raíz
- **Después**: `config/security_config.py`
- **Template**: `config/security_config.example.py` (sin secretos)
- **Import**: Automático con sys.path manipulation

### `.gitignore` Actualizado

- Ignora `data/*.db`, `data/*.csv`, `data/*.json`
- Ignora `config/security_config.py` (protege secretos)
- Permite `docs/**/*.png` (imágenes de documentación)
- Más organizado y específico

## 🚀 Cómo Ejecutar Ahora

### Opción 1: Desde raíz (Wrappers)

```powershell
# Cliente
python run_cliente.py

# Servidor
python run_servidor.py
```

### Opción 2: Directamente desde src/

```powershell
cd src

# Cliente
python specs.py

# Servidor
python servidor.py

# Inventario
python all_specs.py
```

### Opción 3: Scripts de utilidad

```powershell
# Compilar todo
.\scripts\build_all.ps1

# Ejecutar tests
python -m pytest tests/

# Escanear red
python scripts/optimized_block_scanner.py
```

## 📝 Archivos de Configuración

### `config/security_config.py` (Crear primero)

```powershell
# Copiar template
Copy-Item config/security_config.example.py config/security_config.py

# Editar y configurar SHARED_SECRET
notepad config/security_config.py
```

O usar el instalador automático:
```powershell
.\scripts\install.ps1  # Genera security_config.py automáticamente
```

## 🔧 PyInstaller Actualizado

Los comandos de PyInstaller en `scripts/build_all.ps1` ahora usan:

```powershell
pyinstaller --onedir --noconsole src/servidor.py `
    --add-data "src/sql/statement/*.sql;sql/statement" `
    --add-data "src/ui/*.ui;ui"
```

## ✅ Beneficios

1. **Organización Clara**: Cada tipo de archivo en su carpeta
2. **Menos Archivos en Raíz**: Solo 5 archivos importantes
3. **Estructura Estándar**: Familiar para desarrolladores Python
4. **Git Más Limpio**: `.gitignore` organizado por categorías
5. **Seguridad Mejorada**: `config/` separado, template sin secretos
6. **Datos Separados**: `data/` contiene todo lo runtime
7. **Documentación Centralizada**: `docs/` con toda la info
8. **Scripts Agrupados**: `scripts/` con todas las utilidades
9. **UI Workflow Preservado**: `.ui` y `_ui.py` juntos (extensión funciona)
10. **Testeable**: `tests/` listo para pytest/unittest

## ⚠️  Nota Importante

Si usas PyCharm, VS Code u otro IDE:

1. **Marcar `src/` como Source Root**
2. **Python Path**: El IDE debe incluir `src/` automáticamente
3. **Extensión Qt**: Seguirá generando `_ui.py` en `src/ui/` correctamente

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'logica'"

**Solución**: Ejecutar desde raíz con wrappers o desde dentro de `src/`:

```powershell
# ✅ Correcto
python run_cliente.py

# ✅ Correcto
cd src; python specs.py

# ❌ Incorrecto
python src/specs.py  # Falla porque Python no ve src/ en PYTHONPATH
```

### "FileNotFoundError: security_config.py"

**Solución**: Copiar el template:

```powershell
Copy-Item config/security_config.example.py config/security_config.py
```

Luego editar `SHARED_SECRET` con un token aleatorio.

### "Database not found"

**Solución**: La carpeta `data/` debe existir:

```powershell
mkdir data -Force
```

El código crea `data/specs.db` automáticamente la primera vez.

## 📚 Documentación

Toda la documentación movida a `docs/`:

- `docs/DISTRIBUCION_RAPIDA.md` - Guía rápida de distribución
- `docs/DISTRIBUCION.md` - Guía completa
- `docs/NETWORK_FLOW.md` - Arquitectura de red detallada
- `docs/SECURITY_README.md` - Configuración de seguridad
- `docs/REORGANIZACION.md` - Propuesta de reorganización (este archivo)

**🎉 Reorganización completada exitosamente!**
