# SpecsNet - Sistema de Inventario de Hardware en Red

Sistema cliente-servidor para Windows que recopila automáticamente especificaciones de hardware y software de equipos en red.

**[📖 Para documentación completa, ver README_TECNICO.md](README_TECNICO.md)**

---

## Requisitos Previos

- **Sistema Operativo**: Windows 10/11
- **Python**: 3.13 o superior
- **Red**: Equipos en misma LAN o con conectividad TCP directa

---

## Instalación

```powershell
# 1. Clonar repositorio
git clone https://github.com/Th3GaM3RCaT/specs-python.git
cd specs-python

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar seguridad (opcional)
Copy-Item config\security_config.example.py config\security_config.py
# Editar config\security_config.py y configurar SHARED_SECRET
```

---

## Compilación (Distribución)

### Generar Ejecutables

```powershell
# Compilar cliente
.\scripts\build_cliente.ps1

# Compilar servidor
.\scripts\build_servidor.ps1
```

**Salida**: 
- `dist/SpecsNet-Cliente/SpecsNet-Cliente.exe`
- `dist/SpecsNet-Servidor/SpecsNet-Servidor.exe`

### Distribuir

1. Comprimir carpeta completa `dist/SpecsNet-Cliente/` (incluye DLLs)
2. Descomprimir en equipos destino
3. Ejecutar `SpecsNet-Cliente.exe`

**Firewall**: Clientes deben permitir entrada TCP en puerto `5256`

---

## Uso Rápido

### 1. Iniciar Servidor (Equipo Central)

```powershell
# Desde código fuente
python run_servidor.py

# Desde ejecutable
.\dist\SpecsNet-Servidor\SpecsNet-Servidor.exe
```

- Inicia interfaz gráfica de gestión
- Escucha en puerto 5255 (legacy) y solicita datos en puerto 5256

### 2. Iniciar Cliente Daemon (Cada Equipo)

```powershell
# Desde código fuente
python run_cliente.py

# Desde ejecutable
.\dist\SpecsNet-Cliente\SpecsNet-Cliente.exe
```

- Se ejecuta en segundo plano (modo daemon)
- Escucha en puerto 5256
- Responde automáticamente a solicitudes del servidor

### 3. Escanear Red

**Desde interfaz del servidor:**
1. Click en **"Actualizar"** o **"Escanear Red"**
2. Esperar que el escaneo complete
3. La tabla mostrará todos los dispositivos descubiertos
4. Dispositivos con cliente activo mostrarán información completa

---

## Datos Recopilados

**Hardware**: Serial, modelo, CPU, GPU, RAM (módulos individuales), discos  
**Sistema**: Nombre equipo, usuario, MAC, IP, licencia Windows  
**Software**: Aplicaciones instaladas, diagnóstico DirectX

---

## Puertos Utilizados

| Puerto | Uso | Componente |
|--------|-----|------------|
| `5256` | Daemon escucha solicitudes | **Clientes** |
| `5255` | Recepción pasiva (legacy) | Servidor |

---

## Troubleshooting

**Cliente daemon no arranca**:
```powershell
netstat -an | findstr 5256  # Verificar puerto disponible
```

**Servidor no obtiene datos**:
- Confirmar cliente daemon ejecutándose
- Verificar firewall permite entrada TCP puerto 5256 en cliente

**Escaneo no detecta dispositivos**:
- Verificar equipos responden a ping
- Confirmar red permite tráfico ICMP

---

## Documentación Técnica

**[Ver README_TECNICO.md](README_TECNICO.md)** para:
- Arquitectura completa del sistema
- Estructura de base de datos
- Desarrollo y debugging
- Guías detalladas de compilación
- Patrones de seguridad implementados

---

## Licencia

[MIT License](LICENSE) - Uso comercial, modificación y distribución permitidos.