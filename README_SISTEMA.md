# Sistema de Inventario de Hardware en Red

## Descripción General

Sistema cliente-servidor para Windows que recopila especificaciones de hardware/software de equipos en red, almacena la información en una base de datos SQLite y presenta una interfaz gráfica para visualización y gestión.

## Arquitectura del Sistema

### 1. **Cliente (`specs.py`)**
Aplicación que se ejecuta en cada equipo de la red para recopilar y enviar información.

#### Modos de Ejecución:
- **Modo GUI** (por defecto): `python specs.py`
  - Interfaz gráfica para ejecutar manualmente el informe
  - Botón para enviar datos al servidor
  
- **Modo Tarea**: `python specs.py --tarea`
  - Se ejecuta en segundo plano
  - Escucha broadcasts del servidor en puerto `37020`
  - Responde automáticamente enviando sus datos

#### Datos Recopilados:
- **Hardware**: Serial, Modelo, Procesador, GPU, RAM, Disco
- **Sistema**: Nombre del equipo, Usuario, MAC Address, IP
- **Software**: Aplicaciones instaladas, Estado de licencia Windows
- **Diagnóstico**: Reporte DirectX completo (dxdiag)

### 2. **Servidor (`servidor.py` + `logica_servidor.py`)**
Aplicación central que recibe datos de clientes y los almacena en la base de datos.

#### Componentes:
- **Servidor TCP** (puerto `5255`): Recibe JSON de clientes
- **Broadcast UDP** (puerto `37020`): Anuncia presencia en la red
- **Base de Datos**: SQLite (`specs.db`)
- **Procesamiento**: Parsea JSON y DirectX, guarda en tablas normalizadas

#### Tablas de la Base de Datos:
- `Dispositivos`: Información principal del equipo
- `activo`: Historial de estados (encendido/apagado)
- `memoria`: Módulos RAM individuales
- `almacenamiento`: Discos y particiones
- `aplicaciones`: Software instalado
- `informacion_diagnostico`: Reportes completos (JSON + DirectX)
- `registro_cambios`: Historial de modificaciones de hardware

### 3. **Interfaz de Gestión (`mainServidor.py`)**
UI para visualizar y administrar el inventario de dispositivos.

#### Características:
- **Tabla de Dispositivos**: Muestra todos los equipos registrados
  - Estado (Encendido/Apagado/Inactivo)
  - DTI, Serial, Usuario, Modelo
  - Procesador, GPU, RAM, Disco
  - Estado de licencia, IP
  
- **Filtros y Búsqueda**:
  - Buscar por cualquier campo
  - Filtrar por: Activos, Inactivos, Encendidos, Apagados, Sin Licencia
  
- **Detalles por Dispositivo**:
  - Diagnóstico completo
  - Aplicaciones instaladas
  - Detalles de almacenamiento
  - Módulos de memoria RAM
  - Historial de cambios

### 4. **Escaneo de Red (`optimized_block_scanner.py`)**
Descubre dispositivos en la red para consultar su información.

#### Funcionalidad:
- Escanea rangos `10.100.0.0/16` a `10.119.0.0/16`
- Usa probes SSDP/mDNS + ping-sweep asíncrono
- Parsea tabla ARP para asociar IP ↔ MAC
- Genera CSV: `optimized_scan_YYYYMMDD_HHMMSS.csv`

## Flujo de Trabajo Completo

### Instalación Inicial

1. **Servidor**:
   ```bash
   # Crear base de datos
   sqlite3 specs.db < sql_specs/specs.sql
   
   # Ejecutar servidor
   python servidor.py
   ```

2. **Clientes**:
   ```bash
   # Modo manual
   python specs.py
   
   # Modo automático (tarea programada)
   python specs.py --tarea
   ```

### Proceso de Recopilación de Datos

```
1. SERVIDOR anuncia su presencia
   └─> Broadcast UDP: "servidor specs" → 255.255.255.255:37020

2. CLIENTE detecta servidor
   └─> Escucha puerto 37020, extrae IP del sender

3. CLIENTE recopila información
   ├─> WMI: Serial, Modelo, Procesador, RAM
   ├─> psutil: CPU, Memoria, Disco, Red
   ├─> dxdiag: GPU y diagnóstico completo
   ├─> windows_tools: Aplicaciones instaladas
   └─> slmgr: Estado de licencia Windows

4. CLIENTE envía datos al servidor
   └─> TCP connect a SERVIDOR:5255, envía JSON completo

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
| `DTI` | Manual | - (se asigna manualmente) |
| `user` | JSON | `Name` |
| `MAC` | JSON | `MAC Address` |
| `model` | JSON | `Model` |
| `processor` | DirectX | `Processor:` |
| `GPU` | DirectX | `Card name:` |
| `RAM` | JSON | Suma de `Capacidad_GB` de módulos |
| `disk` | DirectX | `Drive:`, `Model:`, `Total Space:` |
| `license_status` | JSON | `License status` |
| `ip` | JSON | `client_ip` |
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

### Servidor:
```bash
pyinstaller --onedir --noconsole servidor.py ^
  --add-data "sql_specs/statement/*.sql;sql_specs/statement"
```

### Cliente:
```bash
pyinstaller --onedir --noconsole specs.py ^
  --hidden-import=wmi --hidden-import=psutil
```

## Configuración de Puertos

| Puerto | Protocolo | Uso |
|--------|-----------|-----|
| `5255` | TCP | Recepción de datos de clientes |
| `37020` | UDP | Broadcast de descubrimiento |

**Importante**: Firewall debe permitir estos puertos.

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

1. **Autenticación**: Tokens o certificados para clientes
2. **Encriptación**: TLS/SSL para comunicación TCP
3. **Discovery Robusto**: mDNS/Zeroconf en lugar de broadcasts
4. **API REST**: Para integración con otros sistemas
5. **Mapa de Red**: Visualización con NetworkX/Graphviz
6. **Alertas**: Notificaciones cuando dispositivos caen
7. **Reportes**: Exportar a Excel, PDF
8. **Multi-servidor**: Replicación y alta disponibilidad

## Troubleshooting

### Cliente no encuentra servidor
- Verificar firewall (puerto 37020 UDP)
- Confirmar que están en la misma subnet
- Ejecutar cliente en modo `--tarea` para escuchar broadcasts

### Servidor no recibe datos
- Verificar puerto 5255 TCP abierto
- Ver logs en consola del servidor
- Confirmar que `specs.db` existe y tiene permisos de escritura

### Errores de encoding en DirectX
- Asegurar que `dxdiag_output.txt` se lee con `encoding='cp1252'`

### DB locked error
- Solo una instancia del servidor debe acceder a `specs.db`
- Cerrar conexiones después de commits
- Usar `connection.commit()` después de escrituras

## Contacto y Soporte

Para reportar bugs o solicitar features, crear issue en el repositorio.
