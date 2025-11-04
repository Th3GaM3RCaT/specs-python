# 🔄 Flujo de Comunicación Cliente-Servidor - Specs Python

## 📡 Arquitectura de Red

```
┌──────────────────────────────────────────────────────────────────────┐
│                        RED LOCAL (LAN)                               │
│                    10.100.0.0/16 - 10.119.0.0/16                     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐                        ┌──────────────────┐     │
│  │   SERVIDOR      │                        │   CLIENTE 1      │     │
│  │  (servidor.py)  │                        │  (specs.py)      │     │
│  │                 │                        │                  │     │
│  │  Puerto 5255    │◄─────── TCP ───────────│  TCP Client      │     │
│  │  (TCP Server)   │      Datos JSON        │                  │     │
│  │                 │                        │                  │     │
│  │  Puerto 37020   │──── UDP Broadcast ────►│  Puerto 37020    │     │
│  │  (UDP Sender)   │  "servidor specs"      │  (UDP Listener)  │     │
│  └─────────────────┘       cada 10s         └──────────────────┘     │
│                                                                      │
│                            ┌──────────────────┐                      │
│                            │   CLIENTE 2      │                      │
│                            │  (specs.py)      │                      │
│                            │  --tarea         │                      │
│                            │                  │                      │
│                            │  Puerto 37020    │                      │
│                            │  (UDP Listener)  │                      │
│                            └──────────────────┘                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔀 Flujo de Secuencia Completo

### **Escenario 1: Modo GUI (Cliente Interactivo)**

```
USUARIO         CLIENTE (GUI)           SERVIDOR
   │                 │                      │
   │                 │    ┌─────────────────┤ main() inicia
   │                 │    │                 │
   │                 │    │ Thread 1:       │ TCP Server
   │                 │    │ Listen 5255     │ (recibe datos)
   │                 │    │                 │
   │                 │    │ Thread 2:       │ Broadcast Loop
   │                 │    │ cada 10s ──────►┤ sendto(37020)
   │                 │    │ "servidor specs"│
   │                 │    └─────────────────┤
   │  1. Click       │                      │
   │  "Enviar" ──────►                      │
   │                 │                      │
   │                 │ 2. enviar_a_servidor()
   │                 │    bind(37020)       │
   │                 │    timeout=5s        │
   │                 │                      │
   │                 │ 3. recvfrom() ───────│
   │                 │    espera broadcast  │
   │                 │                      │
   │                 │◄─────────────────────┤ 4. Broadcast recibido
   │                 │  "servidor specs"    │    addr=(IP_SERVER, ...)
   │                 │                      │
   │                 │ 5. informe()         │
   │                 │    - WMI, psutil     │
   │                 │    - dxdiag          │
   │                 │    - software        │
   │                 │                      │
   │                 │ 6. generate_auth_token()
   │                 │    new["auth_token"] │
   │                 │                      │
   │                 │ 7. TCP connect ──────►
   │                 │    (IP_SERVER:5255)  │
   │                 │                      │
   │                 │ 8. sendall(JSON) ───►┤ 9. consultar_informacion()
   │                 │                      │    - verify_auth_token()
   │                 │                      │    - is_ip_allowed()
   │                 │                      │    - sanitize_field()
   │                 │                      │
   │                 │                      │ 10. Guardar en DB
   │                 │                      │     - parsear_datos_dispositivo()
   │                 │                      │     - sql.setDevice()
   │                 │                      │     - sql.setActive()
   │                 │                      │
   │                 │◄─────────────────────┤ 11. conn.close()
   │                 │                      │
   │◄─── "Enviado" ──┤                      │
   │                 │                      │
```

---

### **Escenario 2: Modo Tarea (Cliente Daemon)**

```
SISTEMA         CLIENTE (--tarea)         SERVIDOR
   │                 │                      │
   │ 1. Startup      │                      │
   │  (Windows Run)  │                      │
   │  specs.py --tarea                      │
   │                 │                      │
   │                 │ 2. escuchar_broadcast()
   │                 │    bind(37020)       │
   │                 │    while True: ─────►┤ Loop infinito
   │                 │    recvfrom()        │
   │                 │                      │
   │                 │                      │ 3. Broadcast cada 10s
   │                 │◄─────────────────────┤    sendto(37020)
   │                 │  "servidor specs"    │
   │                 │                      │
   │                 │ 4. manejar_broadcast()
   │                 │    - Verificar cooldown (60s)
   │                 │    - ultima_ejecucion check
   │                 │                      │
   │                 │ 5. informe()         │
   │                 │    Recopilar datos   │
   │                 │                      │
   │                 │ 6. enviar_a_servidor()
   │                 │    + auth_token      │
   │                 │                      │
   │                 │ 7. TCP connect ──────►
   │                 │    sendall(JSON) ───►┤ 8. Procesar y guardar
   │                 │                      │
   │                 │◄─────────────────────┤ 9. close()
   │                 │                      │
   │                 │ 10. Cooldown 60s     │
   │                 │     (ignorar broadcasts)
   │                 │                      │
   │                 │                      │ 11. Broadcast siguiente
   │                 │◄─────────────────────┤    (después de 10s)
   │                 │  "servidor specs"    │
   │                 │                      │
   │                 │ 12. ⏳ Cooldown activo
   │                 │     No ejecutar      │
   │                 │                      │
   │                 │     ... espera ...   │
   │                 │                      │
   │                 │ 13. Cooldown expirado│
   │                 │     (después de 60s) │
   │                 │                      │
   │                 │◄─────────────────────┤ 14. Broadcast
   │                 │                      │
   │                 │ 15. REPETIR desde paso 4
   │                 │                      │
```

---

## 🔌 Tabla de Puertos y Protocolos

| Puerto | Protocolo | Dirección | Propósito | Usado Por |
|--------|-----------|-----------|-----------|-----------|
| **37020** | UDP | Broadcast → Todos | Discovery (servidor anuncia IP) | Servidor (sender) |
| **37020** | UDP | 0.0.0.0 (bind) | Escucha broadcasts | Cliente (listener) |
| **5255** | TCP | Server IP | Envío de datos JSON | Cliente → Servidor |
| **5255** | TCP | 0.0.0.0 (bind) | Recepción de datos | Servidor (listener) |

---

## ⏱️ Timeouts y Timings

| Operación | Timeout/Intervalo | Propósito |
|-----------|-------------------|-----------|
| **Broadcast del servidor** | Cada 10 segundos | Anunciar disponibilidad continuamente |
| **Cliente espera broadcast** | 5 segundos | Timeout para detectar servidor |
| **Cooldown cliente tarea** | 60 segundos | Evitar múltiples ejecuciones consecutivas |
| **Conexión TCP** | CONNECTION_TIMEOUT (30s) | Prevenir conexiones colgadas |
| **Token autenticación** | 5 minutos | Ventana de validez del token |

---

## 🔐 Capa de Seguridad

```
┌───────────────────────────────────────────────────────────────┐
│                    VALIDACIONES DE SEGURIDAD                  │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  1  IP Whitelist                                              │
│     │ is_ip_allowed(client_ip)                │               │
│     ┌─────────────────────────────────────────┐               │
│     │ ALLOWED_SUBNETS = [                     │               │
│     │   "10.100.0.0/16",                      │               │
│     │   "10.119.0.0/16",                      │               │
│     │   "127.0.0.1/32"                        │               │
│     │ ]                                       │               │
│     └─────────────────────────────────────────┘               │
│                         ↓                                     │
│                    ✅ Permitida / ❌ Bloqueada               │
│                                                               │
│  2  Rate Limiting                                             │
│     ┌─────────────────────────────────────────┐               │
│     │ connections_per_ip[IP] <= 3             │               │
│     │ MAX_CONNECTIONS_PER_IP = 3              │               │
│     └─────────────────────────────────────────┘               │
│                         ↓                                     │
│                    ✅ Aceptar / ❌ Rechazar                  │
│                                                               │
│  3 Token Authentication                                       │
│     ┌─────────────────────────────────────────┐               │
│     │ token = json_data.get("auth_token")     │               │
│     │ verify_auth_token(token)                │               │
│     │   - HMAC-SHA256                         │               │
│     │   - Timestamp-based (5 min window)      │               │
│     └─────────────────────────────────────────┘               │
│                         ↓                                     │
│                    ✅ Válido / ❌ Inválido                   │
│                                                               │
│  4 Buffer Overflow Protection                                 │
│     ┌─────────────────────────────────────────┐               │
│     │ len(buffer) <= MAX_BUFFER_SIZE          │               │
│     │ MAX_BUFFER_SIZE = 10 MB                 │               │
│     └─────────────────────────────────────────┘               │
│                         ↓                                     │
│                    ✅ Procesar / ❌ Cerrar                   │
│                                                               │
│  5 Input Sanitization                                         │
│     ┌─────────────────────────────────────────┐               │
│     │ serial = sanitize_field(data)           │               │
│     │   - Truncar a 1024 chars                │               │
│     │   - Remover caracteres de control       │               │
│     └─────────────────────────────────────────┘               │
│                         ↓                                     │
│                     Guardar en DB                             │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## 🚨 Manejo de Errores

| Error | Descripción | Acción |
|-------|-------------|--------|
| **Timeout discovery** | Cliente no recibe broadcast en 5s | Mostrar error, pedir reintentar |
| **Token inválido** | Token no verifica o expirado | Rechazar conexión, log warning |
| **IP bloqueada** | IP fuera de ALLOWED_SUBNETS | Cerrar conexión inmediatamente |
| **Buffer overflow** | JSON > 10 MB | Cerrar conexión, log attack |
| **ConnectionResetError** | Cliente cierra abruptamente | Limpiar recursos, log evento |
| **Rate limit** | > 3 conexiones de misma IP | Rechazar nueva conexión |

---

## 📝 Ejemplo de Logs

### **Servidor**
```
✓ Thread de anuncios iniciado
✓ Servidor TCP escuchando en 10.100.5.10:5255
✓ Sistema listo - Esperando clientes...

📡 Broadcast enviado a 255.255.255.255:37020
📡 Broadcast enviado a 255.255.255.255:37020
conectando por ('10.100.5.15', 52341)
✓ Token válido desde 10.100.5.15
Procesando datos del dispositivo: ABC123XYZ
✓ Datos del dispositivo ABC123XYZ guardados exitosamente
cerrando conexion
desconectado: ('10.100.5.15', 52341)

📊 Broadcasts enviados: 6 (clientes conectados: 0)
```

### **Cliente Modo GUI**
```
🔍 Buscando servidor (escuchando broadcasts en puerto 37020)...
Servidor encontrado: 10.100.5.10
✓ Token de autenticación agregado
🔌 Conectando al servidor 10.100.5.10:5255...
✓ Datos enviados correctamente al servidor
```

### **Cliente Modo Tarea**
```
======================================================================
🤖 MODO TAREA ACTIVADO
======================================================================
Esperando solicitud del servidor...
Presiona Ctrl+C para detener

✓ Escuchando broadcasts en puerto 37020...
📡 Broadcast recibido de 10.100.5.10: servidor specs

======================================================================
🎯 Servidor detectado en 10.100.5.10
📊 Iniciando recopilación de especificaciones...
⏰ Hora: 2025-11-04 14:30:15

1️⃣ Recopilando datos del sistema...
   ✓ Datos recopilados exitosamente

2️⃣ Enviando datos al servidor...
🔍 Buscando servidor (escuchando broadcasts en puerto 37020)...
Servidor encontrado: 10.100.5.10
✓ Token de autenticación agregado
🔌 Conectando al servidor 10.100.5.10:5255...
✓ Datos enviados correctamente al servidor
   ✓ Datos enviados al servidor

✅ Proceso completado exitosamente
======================================================================
```

---

## 🎯 Testing Rápido

### **Test 1: Verificar Servidor**
```bash
# Terminal 1
python servidor.py

# Debe mostrar:
# ✓ Thread de anuncios iniciado
# ✓ Servidor TCP escuchando en <IP>:5255
# 📡 Broadcast enviado...
```

### **Test 2: Cliente GUI**
```bash
# Terminal 2
python specs.py

# Click botón "Enviar"
# Debe mostrar:
# 🔍 Buscando servidor...
# Servidor encontrado: <IP>
# ✓ Datos enviados correctamente
```

### **Test 3: Cliente Tarea**
```bash
# Terminal 3
python specs.py --tarea

# Debe mostrar:
# 🤖 MODO TAREA ACTIVADO
# ✓ Escuchando broadcasts...
# (esperar 10 segundos máximo)
# 📡 Broadcast recibido...
# ✅ Proceso completado exitosamente
```

---

## 🔍 Troubleshooting

| Problema | Causa Probable | Solución |
|----------|----------------|----------|
| Cliente no encuentra servidor | Firewall bloquea puerto 37020 UDP | Agregar regla firewall |
| "Token inválido" | SHARED_SECRET diferente | Verificar mismo secreto en ambos |
| "IP bloqueada" | IP no en ALLOWED_SUBNETS | Agregar subnet a security_config.py |
| Timeout después de 5s | Servidor no ejecutándose | Iniciar servidor primero |
| Cliente tarea no responde | Cooldown activo (60s) | Esperar 1 minuto entre ejecuciones |
| "Buffer overflow" | JSON > 10 MB | Datos corruptos, revisar dxdiag |
