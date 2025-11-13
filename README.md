# Sistema de Inventario de Hardware en Red - SpecsNet

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](https://www.microsoft.com/windows)

Sistema cliente-servidor para Windows que recopila especificaciones de hardware/software de equipos en red mediante **consultas directas TCP**, almacena la información en una base de datos SQLite y presenta una interfaz gráfica para visualización y gestión.

**Arquitectura:** El servidor **solicita activamente** los datos a cada cliente mediante conexión TCP directa (no se usan broadcasts UDP). Cada cliente ejecuta un daemon que escucha en puerto 5256 y responde a comandos.

---

## ✨ Características Principales

- 🔄 **Consultas Directas TCP**: Servidor solicita activamente datos a cada cliente (sin broadcasts UDP)
- ⚡ **Escaneo Paralelo**: Procesa hasta 50 dispositivos simultáneamente con `asyncio`
- 🔍 **Discovery Inteligente**: Combina SSDP/mDNS + ping sweep (detecta dispositivos que no responden a multicast)
- 🔐 **Autenticación por Token**: Seguridad basada en tokens con expiración de 5 minutos
- 📊 **UI en Tiempo Real**: Actualiza estados cada 10 segundos automáticamente (sin mensajes)
- 🔢 **Ordenamiento Numérico**: IPs ordenadas correctamente (10.100.1.12 < 10.100.1.110)
- 🎯 **Estados Visuales**: Colores en tabla (🟢 Encendido, 🔴 Apagado, ⚪ Sin IP)
- 💾 **SQLite Normalizado**: Schema completo con 8+ tablas relacionadas
- 🛡️ **Thread-Safe**: Operaciones DB seguras desde múltiples hilos
- 🚀 **Ejecución en Segundo Plano**: Cliente daemon sin intervención del usuario

---

## 📑 Índice

1. [Estructura del Proyecto](#-estructura-del-proyecto)
2. [Inicio Rápido](#-inicio-rápido)
   - [Instalación](#instalación)
   - [Ejecución](#ejecución)
3. [Arquitectura del Sistema](#arquitectura-del-sistema)
   - [Cliente](#1-cliente-srcspecspy)
   - [Servidor](#2-servidor-srcservidorpy--srclogicalogica_servidorpy)
   - [Interfaz de Gestión](#3-interfaz-de-gestión-srcmainservidorpy)
   - [Escaneo de Red](#4-escaneo-de-red-optimized_block_scannerpy)
4. [Flujo de Trabajo Completo](#flujo-de-trabajo-completo)
   - [Instalación Inicial](#instalación-inicial)
   - [Proceso de Recopilación de Datos](#proceso-de-recopilación-de-datos)
   - [Escaneo y Descubrimiento Masivo](#escaneo-y-descubrimiento-masivo)
5. [Mapeo de Datos JSON → Base de Datos](#mapeo-de-datos-json--base-de-datos)
6. [Funciones Principales](#funciones-principales)
7. [Compilación (PyInstaller)](#compilación-pyinstaller)
8. [Configuración de Puertos](#configuración-de-puertos)
9. [Dependencias](#dependencias)
10. [Notas de Implementación](#notas-de-implementación)
11. [Mejoras Futuras](#mejoras-futuras)
12. [Troubleshooting](#troubleshooting)
13. [Contacto y Soporte](#contacto-y-soporte)
14. [Licencia](#-licencia)

---

## 📁 Estructura del Proyecto

```
specs-python/
│
├── 📂 src/                          # Código fuente principal
│   ├── specs.py                     # Cliente (entry point)
│   ├── servidor.py                  # Servidor (entry point)
│   ├── all_specs.py                 # Inventario completo (entry point)
│   │
│   ├── 📂 logica/                   # Lógica de negocio
│   │   ├── logica_specs.py          # Recolección de datos del sistema
│   │   ├── logica_servidor.py       # Servidor TCP/UDP + procesamiento
│   │   ├── logica_Hilo.py           # Threading helpers (Hilo, HiloConProgreso)
│   │   └── mainServidor.py          # UI principal del servidor
│   │
│   ├── 📂 datos/                    # Módulos de recolección de datos
│   │   ├── scan_ip_mac.py           # Escaneo de red + resolución MAC
│   │   ├── get_ram.py               # Información de módulos RAM
│   │   ├── informeDirectX.py        # Parseo de dxdiag
│   │   ├── ipAddress.py             # Detección de IP local
│   │   └── serialNumber.py          # Número de serie del equipo
│   │
│   ├── 📂 sql/                      # Capa de base de datos
│   │   ├── consultas_sql.py         # Funciones de acceso a DB
│   │   ├── specs.sql                # Schema de la base de datos
│   │   └── 📂 statement/            # Queries SQL parametrizadas
│   │       ├── Dispositivos-select.sql
│   │       ├── activo-select.sql
│   │       └── ... (otros queries)
│   │
│   └── 📂 ui/                       # Interfaces Qt Designer
│       ├── specs_window.ui          # Diseño cliente
│       ├── specs_window_ui.py       # Auto-generado por extensión
│       ├── servidor_specs_window.ui
│       ├── servidor_specs_window_ui.py
│       ├── inventario.ui
│       ├── inventario_ui.py
│       ├── all_specs.ui
│       └── all_specs_ui.py
│
├── 📂 scripts/                      # Scripts de utilidad
│   ├── build_all.ps1                # Compilar con PyInstaller
│   ├── sign_executables.ps1         # Firmar ejecutables
│   ├── create_self_signed_cert.ps1  # Crear certificado para testing
│   ├── install.ps1                  # Instalador desde código fuente
│   └── optimized_block_scanner.py   # Escáner masivo de red
│
├── 📂 tests/                        # Tests automatizados
│   └── test_connectivity.py         # Tests de conectividad cliente-servidor
│
├── 📂 docs/                         # Documentación
│   ├── DISTRIBUCION.md              # Guía completa de distribución
│   ├── DISTRIBUCION_RAPIDA.md       # Guía rápida
│   ├── NETWORK_FLOW.md              # Arquitectura de red
│   ├── SECURITY_README.md           # Configuración de seguridad
│   └── REORGANIZACION.md            # Historial de reorganización
│
├── 📂 config/                       # Configuración
│   └── security_config.example.py   # Template de configuración de seguridad
│
├── 📂 data/                         # Datos de runtime (ignorado por Git)
│   ├── specs.db                     # Base de datos SQLite
│   └── .gitkeep
│
├── run_cliente.py                   # Ejecutar cliente
├── run_servidor.py                  # Ejecutar servidor
├── requirements.txt                 # Dependencias Python
├── .gitignore                       # Archivos ignorados por Git
└── README.md                        # Este archivo
```

## 🚀 Inicio Rápido

### Instalación

```powershell
# Clonar repositorio
git clone https://github.com/Th3GaM3RCaT/SpecsNet.git
cd specs-python

# Ejecutar instalador automático
.\scripts\install.ps1
```

### Ejecución

```powershell
# Iniciar servidor (UI de gestión + servidor TCP)
python run_servidor.py

# Iniciar cliente daemon en segundo plano (escucha en puerto 5256)
python run_cliente.py
```

**Nota:** El servidor solicita activamente los datos a cada cliente. No es necesario que el cliente "envíe" manualmente - el daemon responde automáticamente a las solicitudes del servidor.

## Arquitectura del Sistema

### 1. **Cliente (`src/specs.py` + `cliente_daemon.py`)**
Daemon que se ejecuta en cada equipo de la red y **responde a solicitudes del servidor**.

#### Modo de Ejecución:
- **Daemon TCP** (puerto `5256`): `python run_cliente.py` o `python cliente_daemon.py`
  - Se ejecuta en segundo plano
  - Escucha conexiones TCP en puerto 5256
  - Responde a comandos:
    - `PING`: Confirma que está vivo (`{'status': 'alive'}`)
    - `GET_SPECS`: Recopila y envía especificaciones completas en JSON

#### Datos Recopilados (al recibir GET_SPECS):
- **Hardware**: Serial, Modelo, Procesador, GPU, RAM, Disco
- **Sistema**: Nombre del equipo, Usuario, MAC Address, IP
- **Software**: Aplicaciones instaladas, Estado de licencia Windows
- **Diagnóstico**: Reporte DirectX completo (dxdiag)

### 2. **Servidor (`src/mainServidor.py` + `src/logica/logica_servidor.py`)**
Aplicación central que **solicita activamente** datos a los clientes y los almacena en la base de datos.

#### Componentes:
- **Servidor TCP** (puerto `5255`): Recibe conexiones **pasivas** de clientes (deprecado, legacy)
- **Cliente TCP** (puerto `5256`): **Solicita activamente** datos a cada cliente daemon
- **Base de Datos**: SQLite (`data/specs.db`)
- **Procesamiento**: Parsea JSON y DirectX, guarda en tablas normalizadas
- **UI de Gestión**: Interfaz gráfica con tabla de dispositivos y funciones de administración

#### Flujo de Consulta:
1. **Escaneo de red** → Descubre IPs con `optimized_block_scanner.py`
2. **Para cada IP descubierta**:
   - Servidor **conecta** a `IP:5256`
   - Envía comando `GET_SPECS`
   - Recibe JSON completo
   - Guarda en base de datos
3. **Verificación automática** cada 10 segundos:
   - Ping silencioso a todos los dispositivos
   - Actualiza estados (Encendido/Apagado) en UI

#### Tablas de la Base de Datos:
- `Dispositivos`: Información principal del equipo
- `activo`: Estado actual (1 registro por dispositivo - encendido/apagado)
- `memoria`: Módulos RAM individuales
- `almacenamiento`: Discos y particiones
- `aplicaciones`: Software instalado
- `informacion_diagnostico`: Reportes completos (JSON + DirectX)
- `registro_cambios`: Historial de modificaciones de hardware
- `tendencias_recursos`: Histórico para alertas inteligentes (RAM/CPU/Disco)

### 3. **Interfaz de Gestión (`src/mainServidor.py`)**
UI para visualizar y administrar el inventario de dispositivos.

#### Características:
- **Tabla de Dispositivos**: Muestra todos los equipos registrados
  - **Estado** (🟢 Encendido / 🔴 Apagado / ⚪ Sin IP)
  - DTI, Serial, Usuario, Modelo
  - Procesador, GPU, RAM, Disco
  - Estado de licencia, IP
  - **Ordenamiento numérico de IPs** (10.100.1.12 < 10.100.1.110)
  
- **Actualización Automática**:
  - Timer cada **10 segundos** verifica estados (ping silencioso)
  - **NO muestra mensajes** en barra de estado
  - Timer se **pausa durante escaneo completo** (evita conflictos)
  
- **Filtros y Búsqueda**:
  - Buscar por cualquier campo
  - Filtrar por: Activos, Inactivos, Encendidos, Apagados, Sin Licencia
  
- **Detalles por Dispositivo**:
  - Diagnóstico completo
  - Aplicaciones instaladas
  - Detalles de almacenamiento
  - Módulos de memoria RAM
  - Historial de cambios

- **Botón "Actualizar"** (Escaneo Completo):
  1. Escanea red completa (`optimized_block_scanner.py`)
  2. Pobla DB con IPs/MACs descubiertas
  3. **Solicita datos completos** a cada cliente activo (GET_SPECS)
  4. Actualiza tabla con toda la información

### 4. **Escaneo de Red (`src/logica/optimized_block_scanner.py`)**
Descubre dispositivos en la red para consultar su información.

#### Funcionalidad:
- Escanea rangos `10.100.0.0/16` a `10.119.0.0/16`
- Usa **SSDP/mDNS probes + ping-sweep** asíncrono
- **Siempre ejecuta ping sweep** (detecta dispositivos que no responden a multicast)
- Parsea tabla ARP para asociar IP ↔ MAC
- Filtra equipos de red por OUI de MAC (switches, routers, APs)
- Genera CSV: `output/discovered_devices.csv`

#### Uso:
```powershell
# Escaneo completo (segmentos 100-119)
python src\logica\optimized_block_scanner.py --start 100 --end 119 --use-broadcast-probe

# Escaneo de segmento único
python src\logica\optimized_block_scanner.py --start 100 --end 100
```

## Flujo de Trabajo Completo

### Instalación Inicial

1. **Servidor**:
   ```powershell
   # Base de datos se crea automáticamente al iniciar
   python run_servidor.py
   ```

2. **Clientes** (en cada equipo):
   ```powershell
   # Instalar dependencias
   pip install -r requirements.txt
   
   # Ejecutar daemon (se queda en segundo plano)
   python run_cliente.py
   ```

### Proceso de Recopilación de Datos (Nueva Arquitectura)

```
1. SERVIDOR ejecuta escaneo de red
   └─> optimized_block_scanner.py descubre IPs activas → CSV

2. SERVIDOR carga CSV y consulta cada dispositivo
   └─> Para cada IP:
       ├─> PING (verificar si está activo)
       └─> Si activo:
           ├─> CONECTAR a IP:5256 (cliente daemon)
           ├─> ENVIAR comando "GET_SPECS"
           └─> RECIBIR JSON completo

3. CLIENTE DAEMON recibe solicitud
   ├─> Detecta comando "GET_SPECS"
   ├─> Recopila información:
   │   ├─> WMI: Serial, Modelo, Procesador, RAM
   │   ├─> psutil: CPU, Memoria, Disco, Red
   │   ├─> dxdiag: GPU y diagnóstico completo
   │   ├─> windows_tools: Aplicaciones instaladas
   │   └─> slmgr: Estado de licencia Windows
   └─> ENVÍA JSON de respuesta

4. SERVIDOR procesa y almacena
   ├─> Parsea JSON + DirectX
   ├─> Extrae datos según esquema de DB
   ├─> Inserta/actualiza en tablas:
   │   ├─ Dispositivos (info principal)
   │   ├─ activo (estado - 1 registro por dispositivo)
   │   ├─ memoria (módulos RAM)
   │   ├─ almacenamiento (discos)
   │   ├─ aplicaciones (software)
   │   └─ informacion_diagnostico (reportes completos)
   └─> Commit a SQLite

5. INTERFAZ muestra datos actualizados
   ├─> Consulta DB y presenta en tabla con colores
   └─> Timer cada 10s verifica estados (silencioso)
```

### Escaneo y Descubrimiento Masivo

```
1. Usuario hace clic en "Actualizar" en UI del servidor

2. PASO 1/4: ESCANEO DE RED
   └─> optimized_block_scanner.py escanea 10.100.x.x - 10.119.x.x
       ├─ Probes SSDP/mDNS (para dispositivos que respondan multicast)
       ├─ Ping sweep (SIEMPRE - para dispositivos que solo responden ICMP)
       └─ Parsea ARP para obtener MACs

3. PASO 2/4: GENERAR CSV
   └─> output/discovered_devices.csv
       ├─ Formato: IP,MAC
       ├─ 10.100.2.150,00:4e:01:99:97:11
       └─ ~305 dispositivos (filtrados por OUI de computadoras)

4. PASO 3/4: POBLAR DB INICIAL
   └─> Inserta registros básicos (IP/MAC) en tabla Dispositivos

5. PASO 4/4: CONSULTAR DISPOSITIVOS (PARALELO)
   └─> Para cada IP en CSV:
       ├─ Ping asíncrono (timeout 1s)
       ├─ Si responde:
       │   ├─ Conectar a IP:5256
       │   ├─ Enviar GET_SPECS
       │   ├─ Recibir JSON completo (timeout 10s)
       │   └─ Guardar en DB
       └─ Actualizar estado en tabla 'activo'

6. FINALIZAR
   └─> UI recarga tabla con datos completos
       └─> Timer de 10s reanuda verificación automática
```

5. SERVIDOR procesa y almacena
   ├─> Parsea JSON + DirectX
   ├─> Extrae datos según esquema de DB
   ├─> Inserta/actualiza en tablas:
   │   ├─ Dispositivos (info principal)
   │   ├─ activo (estado encendido/apagado)
   │   ├─ memoria (módulos RAM)
   │   ├─ almacenamiento (discos)
   │   ├─ aplicaciones (software)
   │   └─ informacion_diagnostico (reportes completos)
   └─> Commit a SQLite

6. INTERFAZ muestra datos actualizados
   └─> Consulta DB y presenta en tabla con colores
```

### Escaneo y Descubrimiento Masivo

```
1. EJECUTAR ESCANEO
   └─> python optimized_block_scanner.py --start 100 --end 119

2. GENERAR CSV
   └─> optimized_scan_20251030_HHMMSS.csv
       ├─ IP,MAC
       ├─ 10.100.2.101,bc:ee:7b:74:d5:b0
       └─ ...

3. SERVIDOR CARGA CSV
   └─> ls.cargar_ips_desde_csv()

4. SERVIDOR CONSULTA CADA IP
   ├─> Ping para verificar si está activo
   ├─> Anuncia presencia (broadcast)
   ├─> Espera que cliente se conecte
   └─> Actualiza estado en DB

5. MONITOREO PERIÓDICO
   └─> ls.monitorear_dispositivos_periodicamente(intervalo_minutos=15)
       ├─ Ping a todos los dispositivos
       ├─ Actualiza campo "activo" en DB
       └─ Repite cada N minutos
```

## Mapeo de Datos JSON → Base de Datos

### Tabla `Dispositivos`

| Campo DB | Fuente | Ubicación en JSON/DirectX |
|----------|--------|---------------------------|
| `serial` | JSON | `SerialNumber` |
| `DTI` | Manual | - (por implementar) |
| `user` | JSON | `Name` |
| `MAC` | JSON | `MAC Address` |
| `model` | JSON | `Model` |
| `processor` | DirectX | `Processor:` |
| `GPU` | DirectX | `Card name:` |
| `RAM` | JSON | Suma de `Capacidad_GB` de módulos |
| `disk` | DirectX | `Drive:`, `Model:`, `Total Space:` |
| `license_status` | JSON | `License status` |
| `ip` | JSON | `client_ip` (en primera instancia, obtenida del escaneo)|
| `activo` | Calculado | `True` si envía datos |

### Tabla `memoria`

Extrae módulos RAM del JSON donde hay claves como:
```json
"--- Módulo RAM 1 ---": "",
"Fabricante": "Micron",
"Número_de_Serie": "18573571",
"Capacidad_GB": 4.0,
"Velocidad_MHz": 2400,
"Etiqueta": "Physical Memory 1"
```

### Tabla `aplicaciones`

Extrae del JSON donde:
```json
"Microsoft Office Standard 2016": ["16.0.4266.1001", "Microsoft Corporation"]
```
- `name`: Clave (nombre de la app)
- `version`: Primer elemento del array
- `publisher`: Segundo elemento del array

## Funciones Principales

### `logica_servidor.py`

| Función | Descripción |
|---------|-------------|
| `parsear_datos_dispositivo(json_data)` | Extrae campos de JSON/DirectX para tabla Dispositivos |
| `parsear_modulos_ram(json_data)` | Extrae módulos RAM para tabla memoria |
| `parsear_almacenamiento(json_data)` | Extrae discos para tabla almacenamiento |
| `parsear_aplicaciones(json_data)` | Extrae apps para tabla aplicaciones |
| `consultar_informacion(conn, addr)` | Recibe datos del cliente y guarda en DB |
| `cargar_ips_desde_csv(archivo_csv)` | Lee CSV de escaneo y retorna lista de IPs |
| `solicitar_datos_a_cliente(ip)` | Hace ping y solicita datos a un cliente |
| `consultar_dispositivos_desde_csv()` | Consulta todos los dispositivos del CSV |
| `monitorear_dispositivos_periodicamente()` | Monitorea estados cada N minutos |
| `main()` | Inicia servidor TCP y acepta conexiones |

### `logica_specs.py` (Cliente)

| Función | Descripción |
|---------|-------------|
| `informe()` | Recopila todas las specs del equipo |
| `enviar_a_servidor()` | Descubre servidor y envía JSON |
| `get_license_status()` | Consulta licencia Windows vía slmgr.vbs |
| `configurar_tarea(valor)` | Registra/desregistra tarea en Registry |

### `mainServidor.py` (UI)

| Función | Descripción |
|---------|-------------|
| `iniciar_servidor()` | Inicia servidor TCP en segundo plano |
| `cargar_dispositivos()` | Consulta DB y llena tabla |
| `escanear_red()` | Ejecuta optimized_block_scanner.py |
| `consultar_dispositivos_csv()` | Consulta dispositivos del CSV |
| `on_dispositivo_seleccionado()` | Carga detalles al seleccionar fila |

## Compilación (PyInstaller)

### Opción 1: Usando Scripts Automatizados (Recomendado)

```powershell
# Compilar Cliente
.\scripts\build_cliente.ps1

# Compilar Servidor
.\scripts\build_servidor.ps1
```

**Nota**: Si PowerShell bloquea la ejecución de scripts, ejecuta una vez:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Opción 2: Comando Manual

#### Cliente:
```powershell
pyinstaller --onedir --noconsole --name "SpecsNet - Cliente" --add-data "src/ui/*.ui;ui" --hidden-import=wmi --hidden-import=psutil --hidden-import=getmac --hidden-import=windows_tools.installed_software --hidden-import=wmi --hidden-import=psutil --hidden-import=getmac --hidden-import=windows_tools.installed_software --hidden-import=PySide6 --hidden-import=PySide6.QtCore --hidden-import=PySide6.QtGui --hidden-import=PySide6.QtWidgets --paths=src src/specs.py
```

#### Servidor:
```powershell
pyinstaller --onedir --noconsole --name "SpecsNet - Servidor" --add-data "src/sql/statement/*.sql;sql/statement" --add-data "src/sql/specs.sql;sql" --add-data "src/ui/*.ui;ui" --hidden-import=wmi --hidden-import=psutil --hidden-import=getmac --hidden-import=windows_tools.installed_software --hidden-import=PySide6 --hidden-import=PySide6.QtCore --hidden-import=PySide6.QtGui --hidden-import=PySide6.QtWidgets --paths=src src/mainServidor.py
```

### Resultado

Los ejecutables se generan en:
- **Cliente**: `dist/SpecsNet - Cliente/SpecsNet - Cliente.exe`
- **Servidor**: `dist/SpecsNet - Servidor/SpecsNet - Servidor.exe`

Para distribuir, comprime las carpetas completas:
- `dist/SpecsNet - Cliente/` → `SpecsNet - Cliente.zip`
- `dist/SpecsNet - Servidor/` → `SpecsNet - Servidor.zip`

### Notas de Compilación

- **`--paths=src`**: ⚠️ **CRÍTICO** - Agrega directorio `src/` al Python path para resolver imports (`from logica.xxx`). Sin esto, PyInstaller no puede encontrar los módulos.
- **`--add-data`**: Incluye archivos no-Python necesarios en runtime (archivos `.ui`, `.sql`)
- **`--onedir`**: Genera un directorio con el .exe y todas las dependencias (inicio rápido, ~5-10x más rápido que `--onefile`)
- **`--noconsole`**: No muestra ventana de consola (solo GUI)
- **`--hidden-import`**: Fuerza la inclusión de módulos que PyInstaller no detecta automáticamente

### ¿Por qué `--onedir` en lugar de `--onefile`?

| Característica | `--onefile` | `--onedir` |
|----------------|-------------|------------|
| Velocidad de inicio | ❌ Lento (5-15 seg) | ✅ Rápido (<1 seg) |
| Distribución | ✅ Un solo .exe | ❌ Carpeta completa |
| Tamaño | ~47 MB | ~60 MB (carpeta) |
| Debugging | ❌ Difícil | ✅ Fácil (archivos visibles) |

**Recomendación**: Usar `--onedir` para aplicaciones que se ejecutan frecuentemente (como este cliente/servidor).

### Debugging

Si el ejecutable falla al iniciar, usa `--console` para ver errores:

```powershell
pyinstaller --onedir --console --name "SpecsNet - Cliente_Debug" --paths=src src/specs.py
```

Esto mostrará la ventana de consola con los errores de Python.

## Configuración de Puertos

| Puerto | Protocolo | Uso | Dirección |
|--------|-----------|-----|-----------|
| `5256` | TCP | Cliente daemon (escucha solicitudes del servidor) | Clientes |
| `5255` | TCP | Servidor legacy (recepción pasiva - deprecado) | Servidor |

**Nueva Arquitectura:**
- **Cliente**: Escucha en puerto `5256` esperando comandos (PING, GET_SPECS)
- **Servidor**: Actúa como cliente TCP, conectándose a cada `IP:5256` para solicitar datos

**Importante**: Firewall en **clientes** debe permitir entrada TCP en puerto `5256`.

## Dependencias

```
PySide6         # UI Qt
wmi             # Windows Management Instrumentation
psutil          # System info cross-platform
getmac          # Obtener MAC address
windows_tools   # Aplicaciones instaladas
sqlite3         # Base de datos (incluido en Python)
```

## Notas de Implementación

### Encoding
- **DirectX output** (`dxdiag_output.txt`): `cp1252` (Windows-1252)
- **JSON**: `utf-8`
- **CSV**: `utf-8`

### Threading
- Usar `logica_Hilo.Hilo` para operaciones bloqueantes
- Evita freeze de UI en operaciones de red/DB/WMI

### Broadcast Limitations
- Solo funciona en misma LAN/subnet
- Routers pueden bloquear broadcasts a `255.255.255.255`
- Considerar multicast o discovery protocol más robusto

## Mejoras Futuras

1. ~~**Autenticación**: Tokens o certificados para clientes~~ ✅ **IMPLEMENTADO** (security_config.py)
2. **Encriptación**: TLS/SSL para comunicación TCP
3. ~~**Discovery Robusto**: Eliminados broadcasts UDP~~ ✅ **IMPLEMENTADO** (consultas directas)
4. **API REST**: Para integración con otros sistemas
5. **Mapa de Red**: Visualización con NetworkX/Graphviz
6. ~~**Alertas**: Notificaciones cuando dispositivos caen~~ ⚠️ **PARCIAL** (timer cada 10s verifica estados)
7. **Reportes**: Exportar a Excel, PDF
8. **Multi-servidor**: Replicación y alta disponibilidad
9. ~~**Escaneo Eficiente**: Ping sweep + probes~~ ✅ **IMPLEMENTADO** (optimized_block_scanner.py)
10. ~~**UI Updates en Tiempo Real**~~ ✅ **IMPLEMENTADO** (timer 10s + ordenamiento numérico IPs)

## Troubleshooting

### Cliente daemon no arranca
- Verificar que puerto `5256` no esté en uso: `netstat -an | findstr 5256`
- Ejecutar con permisos de administrador si es necesario
- Revisar logs en consola para errores de dependencias

### Servidor no obtiene datos de cliente
- **Verificar que cliente daemon esté ejecutándose**: `python run_cliente.py`
- Verificar firewall en **cliente** permite entrada TCP puerto `5256`
- Probar conexión manual: `python test_solicitar_cliente.py`
- Confirmar IP del cliente está en CSV de escaneo

### Escaneo completo no detecta dispositivos
- Verificar que dispositivos respondan a ping: `ping 10.100.x.x`
- Scanner siempre ejecuta ping sweep (detecta incluso sin respuesta a multicast)
- Revisar CSV generado en `output/discovered_devices.csv`
- Confirmar que MACs no están en lista de OUIs de equipos de red

### Estados no se actualizan automáticamente
- Timer se ejecuta cada 10 segundos (verificación silenciosa)
- Timer se **pausa durante escaneo completo** (comportamiento esperado)
- Revisar consola para errores en ping asíncrono

### Errores de encoding en DirectX
- Asegurar que `dxdiag_output.txt` se lee con `encoding='cp1252'`
- **NO usar emojis** en código Python (causa UnicodeEncodeError en Windows)

### DB locked error
- Solo una instancia del servidor debe acceder a `data/specs.db`
- Usar `get_thread_safe_connection()` para operaciones multi-thread
- Cerrar conexiones después de commits

### Tabla "activo" con registros duplicados
- **Patrón correcto**: `DELETE` antes de `INSERT` (mantiene 1 registro por dispositivo)
- Verificar que código usa: `DELETE WHERE Dispositivos_serial = ?` antes de INSERT

## Contacto y Soporte

Para reportar bugs o solicitar features, crear issue en el repositorio de GitHub.

---

## 📄 Licencia

Este proyecto está licenciado bajo la [MIT License](LICENSE).

**En resumen:**
- ✅ Uso comercial permitido
- ✅ Modificación permitida
- ✅ Distribución permitida
- ✅ Uso privado permitido
- ℹ️ Requiere incluir el aviso de copyright y licencia

Para más detalles, consulta el archivo [LICENSE](LICENSE).
