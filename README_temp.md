# Sistema de Inventario de Hardware en Red

## Descripci├│n General

Sistema cliente-servidor para Windows que recopila especificaciones de hardware/software de equipos en red, almacena la informaci├│n en una base de datos SQLite y presenta una interfaz gr├ífica para visualizaci├│n y gesti├│n.

## Arquitectura del Sistema

### 1. **Cliente (`specs.py`)**
Aplicaci├│n que se ejecuta en cada equipo de la red para recopilar y enviar informaci├│n.

#### Modos de Ejecuci├│n:
- **Modo GUI** (por defecto): `python specs.py`
  - Interfaz gr├ífica para ejecutar manualmente el informe
  - Bot├│n para enviar datos al servidor
  
- **Modo Tarea**: `python specs.py --tarea`
  - Se ejecuta en segundo plano
  - Escucha broadcasts del servidor en puerto `37020`
  - Responde autom├íticamente enviando sus datos

#### Datos Recopilados:
- **Hardware**: Serial, Modelo, Procesador, GPU, RAM, Disco
- **Sistema**: Nombre del equipo, Usuario, MAC Address, IP
- **Software**: Aplicaciones instaladas, Estado de licencia Windows
- **Diagn├│stico**: Reporte DirectX completo (dxdiag)

### 2. **Servidor (`servidor.py` + `logica_servidor.py`)**
Aplicaci├│n central que recibe datos de clientes y los almacena en la base de datos.

#### Componentes:
- **Servidor TCP** (puerto `5255`): Recibe JSON de clientes
- **Broadcast UDP** (puerto `37020`): Anuncia presencia en la red
- **Base de Datos**: SQLite (`specs.db`)
- **Procesamiento**: Parsea JSON y DirectX, guarda en tablas normalizadas

#### Tablas de la Base de Datos:
- `Dispositivos`: Informaci├│n principal del equipo
- `activo`: Historial de estados (encendido/apagado)
- `memoria`: M├│dulos RAM individuales
- `almacenamiento`: Discos y particiones
- `aplicaciones`: Software instalado
- `informacion_diagnostico`: Reportes completos (JSON + DirectX)
- `registro_cambios`: Historial de modificaciones de hardware

### 3. **Interfaz de Gesti├│n (`mainServidor.py`)**
UI para visualizar y administrar el inventario de dispositivos.

#### Caracter├¡sticas:
- **Tabla de Dispositivos**: Muestra todos los equipos registrados
  - Estado (Encendido/Apagado/Inactivo)
  - DTI, Serial, Usuario, Modelo
  - Procesador, GPU, RAM, Disco
  - Estado de licencia, IP
  
- **Filtros y B├║squeda**:
  - Buscar por cualquier campo
  - Filtrar por: Activos, Inactivos, Encendidos, Apagados, Sin Licencia
  
- **Detalles por Dispositivo**:
  - Diagn├│stico completo
  - Aplicaciones instaladas
  - Detalles de almacenamiento
  - M├│dulos de memoria RAM
  - Historial de cambios

### 4. **Escaneo de Red (`optimized_block_scanner.py`)**
Descubre dispositivos en la red para consultar su informaci├│n.

#### Funcionalidad:
- Escanea rangos `10.100.0.0/16` a `10.119.0.0/16`
- Usa probes SSDP/mDNS + ping-sweep as├¡ncrono
- Parsea tabla ARP para asociar IP Ôåö MAC
- Genera CSV: `optimized_scan_YYYYMMDD_HHMMSS.csv`

## Flujo de Trabajo Completo

### Instalaci├│n Inicial

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
   
   # Modo autom├ítico (tarea programada)
   python specs.py --tarea
   ```

### Proceso de Recopilaci├│n de Datos

```
1. SERVIDOR anuncia su presencia
   ÔööÔöÇ> Broadcast UDP: "servidor specs" ÔåÆ 255.255.255.255:37020

2. CLIENTE detecta servidor
   ÔööÔöÇ> Escucha puerto 37020, extrae IP del sender

3. CLIENTE recopila informaci├│n
   Ôö£ÔöÇ> WMI: Serial, Modelo, Procesador, RAM
   Ôö£ÔöÇ> psutil: CPU, Memoria, Disco, Red
   Ôö£ÔöÇ> dxdiag: GPU y diagn├│stico completo
   Ôö£ÔöÇ> windows_tools: Aplicaciones instaladas
   ÔööÔöÇ> slmgr: Estado de licencia Windows

4. CLIENTE env├¡a datos al servidor
   ÔööÔöÇ> TCP connect a SERVIDOR:5255, env├¡a JSON completo

5. SERVIDOR procesa y almacena
   Ôö£ÔöÇ> Parsea JSON + DirectX
   Ôö£ÔöÇ> Extrae datos seg├║n esquema de DB
   Ôö£ÔöÇ> Inserta/actualiza en tablas:
   Ôöé   Ôö£ÔöÇ Dispositivos (info principal)
   Ôöé   Ôö£ÔöÇ activo (estado encendido/apagado)
   Ôöé   Ôö£ÔöÇ memoria (m├│dulos RAM)
   Ôöé   Ôö£ÔöÇ almacenamiento (discos)
   Ôöé   Ôö£ÔöÇ aplicaciones (software)
   Ôöé   ÔööÔöÇ informacion_diagnostico (reportes completos)
   ÔööÔöÇ> Commit a SQLite

6. INTERFAZ muestra datos actualizados
   ÔööÔöÇ> Consulta DB y presenta en tabla con colores
```

### Escaneo y Descubrimiento Masivo

```
1. EJECUTAR ESCANEO
   ÔööÔöÇ> python optimized_block_scanner.py --start 100 --end 119

2. GENERAR CSV
   ÔööÔöÇ> optimized_scan_20251030_HHMMSS.csv
       Ôö£ÔöÇ IP,MAC
       Ôö£ÔöÇ 10.100.2.101,bc:ee:7b:74:d5:b0
       ÔööÔöÇ ...

3. SERVIDOR CARGA CSV
   ÔööÔöÇ> ls.cargar_ips_desde_csv()

4. SERVIDOR CONSULTA CADA IP
   Ôö£ÔöÇ> Ping para verificar si est├í activo
   Ôö£ÔöÇ> Anuncia presencia (broadcast)
   Ôö£ÔöÇ> Espera que cliente se conecte
   ÔööÔöÇ> Actualiza estado en DB

5. MONITOREO PERI├ôDICO
   ÔööÔöÇ> ls.monitorear_dispositivos_periodicamente(intervalo_minutos=15)
       Ôö£ÔöÇ Ping a todos los dispositivos
       Ôö£ÔöÇ Actualiza campo "activo" en DB
       ÔööÔöÇ Repite cada N minutos
```

## Mapeo de Datos JSON ÔåÆ Base de Datos

### Tabla `Dispositivos`

| Campo DB | Fuente | Ubicaci├│n en JSON/DirectX |
|----------|--------|---------------------------|
| `serial` | JSON | `SerialNumber` |
| `DTI` | Manual | - (se asigna manualmente) |
| `user` | JSON | `Name` |
| `MAC` | JSON | `MAC Address` |
| `model` | JSON | `Model` |
| `processor` | DirectX | `Processor:` |
| `GPU` | DirectX | `Card name:` |
| `RAM` | JSON | Suma de `Capacidad_GB` de m├│dulos |
| `disk` | DirectX | `Drive:`, `Model:`, `Total Space:` |
| `license_status` | JSON | `License status` |
| `ip` | JSON | `client_ip` |
| `activo` | Calculado | `True` si env├¡a datos |

### Tabla `memoria`

Extrae m├│dulos RAM del JSON donde hay claves como:
```json
"--- M├│dulo RAM 1 ---": "",
"Fabricante": "Micron",
"N├║mero_de_Serie": "18573571",
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

| Funci├│n | Descripci├│n |
|---------|-------------|
| `parsear_datos_dispositivo(json_data)` | Extrae campos de JSON/DirectX para tabla Dispositivos |
| `parsear_modulos_ram(json_data)` | Extrae m├│dulos RAM para tabla memoria |
| `parsear_almacenamiento(json_data)` | Extrae discos para tabla almacenamiento |
| `parsear_aplicaciones(json_data)` | Extrae apps para tabla aplicaciones |
| `consultar_informacion(conn, addr)` | Recibe datos del cliente y guarda en DB |
| `cargar_ips_desde_csv(archivo_csv)` | Lee CSV de escaneo y retorna lista de IPs |
| `solicitar_datos_a_cliente(ip)` | Hace ping y solicita datos a un cliente |
| `consultar_dispositivos_desde_csv()` | Consulta todos los dispositivos del CSV |
| `monitorear_dispositivos_periodicamente()` | Monitorea estados cada N minutos |
| `main()` | Inicia servidor TCP y acepta conexiones |

### `logica_specs.py` (Cliente)

| Funci├│n | Descripci├│n |
|---------|-------------|
| `informe()` | Recopila todas las specs del equipo |
| `enviar_a_servidor()` | Descubre servidor y env├¡a JSON |
| `get_license_status()` | Consulta licencia Windows v├¡a slmgr.vbs |
| `configurar_tarea(valor)` | Registra/desregistra tarea en Registry |

### `mainServidor.py` (UI)

| Funci├│n | Descripci├│n |
|---------|-------------|
| `iniciar_servidor()` | Inicia servidor TCP en segundo plano |
| `cargar_dispositivos()` | Consulta DB y llena tabla |
| `escanear_red()` | Ejecuta optimized_block_scanner.py |
| `consultar_dispositivos_csv()` | Consulta dispositivos del CSV |
| `on_dispositivo_seleccionado()` | Carga detalles al seleccionar fila |

## Compilaci├│n (PyInstaller)

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

## Configuraci├│n de Puertos

| Puerto | Protocolo | Uso |
|--------|-----------|-----|
| `5255` | TCP | Recepci├│n de datos de clientes |
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

## Notas de Implementaci├│n

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
- Considerar multicast o discovery protocol m├ís robusto

## Mejoras Futuras

1. **Autenticaci├│n**: Tokens o certificados para clientes
2. **Encriptaci├│n**: TLS/SSL para comunicaci├│n TCP
3. **Discovery Robusto**: mDNS/Zeroconf en lugar de broadcasts
4. **API REST**: Para integraci├│n con otros sistemas
5. **Mapa de Red**: Visualizaci├│n con NetworkX/Graphviz
6. **Alertas**: Notificaciones cuando dispositivos caen
7. **Reportes**: Exportar a Excel, PDF
8. **Multi-servidor**: Replicaci├│n y alta disponibilidad

## Troubleshooting

### Cliente no encuentra servidor
- Verificar firewall (puerto 37020 UDP)
- Confirmar que est├ín en la misma subnet
- Ejecutar cliente en modo `--tarea` para escuchar broadcasts

### Servidor no recibe datos
- Verificar puerto 5255 TCP abierto
- Ver logs en consola del servidor
- Confirmar que `specs.db` existe y tiene permisos de escritura

### Errores de encoding en DirectX
- Asegurar que `dxdiag_output.txt` se lee con `encoding='cp1252'`

### DB locked error
- Solo una instancia del servidor debe acceder a `specs.db`
- Cerrar conexiones despu├®s de commits
- Usar `connection.commit()` despu├®s de escrituras

## Contacto y Soporte

Para reportar bugs o solicitar features, crear issue en el repositorio.
