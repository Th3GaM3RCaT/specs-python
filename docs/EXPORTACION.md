# Exportación de Datos del Inventario

## Descripción

El sistema de inventario permite exportar todos los datos de dispositivos a formatos compatibles con Microsoft Excel para análisis y reportes externos.

## Formatos Disponibles

### 1. CSV (Comma-Separated Values)

- **Ventajas**:
  - No requiere paquetes adicionales
  - Abre directamente en Excel
  - Compatible con cualquier hoja de cálculo
  - Tamaño de archivo pequeño

- **Uso**:
  1. Haz clic en "Exportar a CSV (Excel)"
  2. Selecciona ubicación y nombre del archivo
  3. El archivo se abre automáticamente en Excel

### 2. XLSX (Excel Nativo)

- **Ventajas**:
  - Formato nativo de Excel
  - Incluye formato enriquecido:
    - Encabezados con fondo azul y texto en negrita
    - Bordes en todas las celdas
    - Columnas ajustadas automáticamente
    - Primera fila congelada
  - Mejor presentación para reportes

- **Requisito**:
  - Requiere el paquete `openpyxl`
  - Instalación: `pip install openpyxl`

- **Uso**:
  1. Haz clic en "Exportar a XLSX (Excel)"
  2. Selecciona ubicación y nombre del archivo
  3. El archivo se abre automáticamente en Excel

## Datos Exportados

La exportación incluye todos los dispositivos de la base de datos con los siguientes campos:

| Campo | Descripción |
|-------|-------------|
| Serial | Número de serie del dispositivo |
| DTI | Número de inventario DTI |
| Usuario | Nombre del usuario asignado |
| MAC | Dirección MAC |
| Modelo | Modelo del dispositivo |
| Procesador | CPU instalado |
| GPU | Tarjeta gráfica |
| RAM (GB) | Memoria RAM en gigabytes |
| Disco | Capacidad de almacenamiento |
| Licencia | Estado de licencia (Sí/No) |
| IP | Dirección IP |
| Activo | Si el dispositivo está activo (Sí/No) |

## Ubicación de Archivos

Por defecto, los archivos se guardan en la carpeta `output/` con el formato:
- `inventario_YYYYMMDD_HHMMSS.csv`
- `inventario_YYYYMMDD_HHMMSS.xlsx`

El usuario puede elegir cualquier ubicación durante el proceso de exportación.

## Integración en el Código

### Módulo de Exportación

El módulo `src/logica/exportar_datos.py` proporciona las siguientes funciones:

```python
from logica.exportar_datos import exportar_dispositivos_completo
from sql.ejecutar_sql import connection

# Exportar a CSV
ruta_csv = exportar_dispositivos_completo(
    connection, 
    formato="csv", 
    incluir_inactivos=True
)

# Exportar a XLSX
ruta_xlsx = exportar_dispositivos_completo(
    connection, 
    formato="xlsx", 
    incluir_inactivos=True
)
```

### Funciones Disponibles

- `exportar_a_csv(datos, columnas, ruta_archivo)`: Exportación básica a CSV
- `exportar_a_xlsx(datos, columnas, ruta_archivo, nombre_hoja)`: Exportación con formato a XLSX
- `exportar_dispositivos_completo(conexion, formato, incluir_inactivos)`: Exportación completa desde DB
- `exportar_con_estado_actual(conexion, formato)`: Exportación con estado de conectividad

## Notas Técnicas

- El encoding CSV es UTF-8 con BOM para compatibilidad con Excel en Windows
- XLSX usa el paquete `openpyxl` para formato avanzado
- Los valores NULL en la DB se convierten a cadenas vacías en el export
- Los booleanos se convierten a "Sí"/"No" para mejor lectura
- Las columnas se ajustan automáticamente al contenido (max 50 caracteres)

## Solución de Problemas

### Error: "Paquete 'openpyxl' no está instalado"

Instala el paquete:
```powershell
pip install openpyxl
```

### El archivo CSV no abre correctamente en Excel

Asegúrate de que Excel esté configurado para detectar UTF-8. El archivo usa UTF-8 con BOM que debería abrir correctamente en versiones modernas de Excel.

### Los datos no están actualizados

Ejecuta una actualización/escaneo completo antes de exportar para asegurar que los datos estén sincronizados.
