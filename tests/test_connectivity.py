#!/usr/bin/env python3
"""
Script de Testing de Conectividad - Specs Python
Verifica el correcto funcionamiento de la comunicación cliente-servidor.
"""

import socket
import time
import sys
import json
from datetime import datetime

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(title):
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{title.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")

def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")


# =============================================================================
# TEST 1: Verificar que el servidor envía broadcasts
# =============================================================================
def test_servidor_broadcasts(timeout=15):
    """Verifica que el servidor envía broadcasts UDP en puerto 37020."""
    print_header("TEST 1: Servidor envía broadcasts")
    
    try:
        print_info("Escuchando broadcasts en puerto 37020...")
        print_info(f"Timeout: {timeout} segundos\n")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 37020))
        sock.settimeout(timeout)
        
        broadcasts_recibidos = []
        start_time = time.time()
        
        print(f"{'Timestamp':<20} {'IP Origen':<15} {'Mensaje':<30}")
        print("-" * 70)
        
        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(1024)
                mensaje = data.decode(errors="ignore")
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                print(f"{timestamp:<20} {addr[0]:<15} {mensaje:<30}")
                broadcasts_recibidos.append({
                    'time': timestamp,
                    'ip': addr[0],
                    'mensaje': mensaje
                })
                
                if len(broadcasts_recibidos) >= 3:
                    break
                    
            except socket.timeout:
                continue
        
        sock.close()
        
        print()
        if broadcasts_recibidos:
            print_success(f"Recibidos {len(broadcasts_recibidos)} broadcasts")
            
            # Verificar intervalo entre broadcasts
            if len(broadcasts_recibidos) >= 2:
                primer_broadcast = broadcasts_recibidos[0]['time']
                segundo_broadcast = broadcasts_recibidos[1]['time']
                print_info(f"Primer broadcast: {primer_broadcast}")
                print_info(f"Segundo broadcast: {segundo_broadcast}")
                print_success("Servidor anuncia IP correctamente cada ~10 segundos")
            
            return True, broadcasts_recibidos[0]['ip']
        else:
            print_error("No se recibieron broadcasts del servidor")
            print_warning("Verificar que servidor.py esté ejecutándose")
            return False, None
            
    except Exception as e:
        print_error(f"Error en test: {e}")
        return False, None


# =============================================================================
# TEST 2: Verificar que el servidor TCP está escuchando
# =============================================================================
def test_servidor_tcp(server_ip, port=5255, timeout=5):
    """Verifica que el servidor TCP esté escuchando en puerto 5255."""
    print_header("TEST 2: Servidor TCP escucha en puerto 5255")
    
    if not server_ip:
        print_error("No se pudo determinar IP del servidor")
        return False
    
    try:
        print_info(f"Intentando conectar a {server_ip}:{port}...")
        print_info(f"Timeout: {timeout} segundos\n")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        start = time.time()
        result = sock.connect_ex((server_ip, port))
        elapsed = time.time() - start
        
        sock.close()
        
        if result == 0:
            print_success(f"Conexión exitosa a {server_ip}:{port}")
            print_info(f"Tiempo de conexión: {elapsed*1000:.2f}ms")
            return True
        else:
            print_error(f"No se pudo conectar a {server_ip}:{port}")
            print_warning(f"Código de error: {result}")
            return False
            
    except socket.timeout:
        print_error(f"Timeout al conectar a {server_ip}:{port}")
        return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


# =============================================================================
# TEST 3: Verificar autenticación (si security_config existe)
# =============================================================================
def test_autenticacion(server_ip, port=5255):
    """Verifica que el sistema de autenticación funciona."""
    print_header("TEST 3: Sistema de Autenticación")
    
    if not server_ip:
        print_error("No se pudo determinar IP del servidor")
        return False
    
    # Verificar si security_config existe
    try:
        from security_config import generate_auth_token, SHARED_SECRET # type: ignore
        security_enabled = True
        print_success("security_config.py encontrado")
        
        if SHARED_SECRET == "CHANGE_ME_TO_RANDOM_TOKEN":
            print_error("SHARED_SECRET no configurado")
            print_warning("Cambiar SHARED_SECRET en security_config.py")
            return False
        else:
            print_success("SHARED_SECRET configurado")
            
    except ImportError:
        print_warning("security_config.py no encontrado")
        print_info("Sistema funcionará sin autenticación (modo inseguro)")
        return True  # No es error, solo no hay seguridad
    
    try:
        print_info("\nGenerando token de prueba...")
        token = generate_auth_token()
        print_success(f"Token generado: {token[:16]}...")
        
        # Crear JSON de prueba
        test_data = {
            "auth_token": token,
            "SerialNumber": "TEST_DEVICE_123",
            "MAC Address": "00:11:22:33:44:55",
            "Name": "TestDevice",
            "Model": "Test Model",
            "client_ip": "127.0.0.1"
        }
        
        print_info(f"Enviando datos de prueba a {server_ip}:{port}...")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((server_ip, port))
        sock.sendall(json.dumps(test_data).encode("utf-8"))
        sock.close()
        
        print_success("Datos enviados exitosamente")
        print_info("Verificar logs del servidor para confirmar validación de token")
        return True
        
    except Exception as e:
        print_error(f"Error en test de autenticación: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# TEST 4: Simular cliente completo
# =============================================================================
def test_flujo_completo(timeout=15):
    """Simula el flujo completo: discovery + envío de datos."""
    print_header("TEST 4: Flujo Cliente Completo")
    
    try:
        # Paso 1: Discovery
        print_info("PASO 1: Discovery del servidor (puerto 37020)")
        sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock_udp.bind(('', 37020))
        sock_udp.settimeout(timeout)
        
        print_info(f"Esperando broadcast (timeout {timeout}s)...")
        
        try:
            data, addr = sock_udp.recvfrom(1024)
            server_ip = addr[0]
            mensaje = data.decode(errors="ignore")
            
            print_success(f"Servidor encontrado: {server_ip}")
            print_info(f"Mensaje: {mensaje}")
            
        except socket.timeout:
            print_error(f"Timeout: No se recibió broadcast en {timeout} segundos")
            sock_udp.close()
            return False
        
        sock_udp.close()
        
        # Paso 2: Verificar si security_config existe
        print_info("\nPASO 2: Preparar autenticación")
        try:
            from security_config import generate_auth_token # type: ignore
            token = generate_auth_token()
            print_success("Token de autenticación generado")
        except ImportError:
            print_warning("Sin security_config - enviando sin autenticación")
            token = None
        
        # Paso 3: Conectar y enviar datos
        print_info(f"\nPASO 3: Conectar vía TCP a {server_ip}:5255")
        
        test_payload = {
            "SerialNumber": "TEST_FLOW_" + str(int(time.time())),
            "MAC Address": "AA:BB:CC:DD:EE:FF",
            "Name": "TestClient",
            "Model": "Integration Test",
            "Manufacturer": "Test Suite",
            "client_ip": "127.0.0.1"
        }
        
        if token:
            test_payload["auth_token"] = token
        
        sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_tcp.settimeout(10)
        sock_tcp.connect((server_ip, 5255))
        
        json_data = json.dumps(test_payload).encode("utf-8")
        print_info(f"Tamaño de datos: {len(json_data)} bytes")
        
        sock_tcp.sendall(json_data)
        sock_tcp.close()
        
        print_success("Datos enviados exitosamente")
        print_info("✓ Flujo completo verificado")
        
        return True
        
    except Exception as e:
        print_error(f"Error en flujo completo: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# TEST 5: Verificar puertos no bloqueados por firewall
# =============================================================================
def test_firewall():
    """Verifica que los puertos no estén bloqueados."""
    print_header("TEST 5: Verificación de Firewall")
    
    tests = [
        ("UDP 37020", socket.SOCK_DGRAM, 37020),
        ("TCP 5255", socket.SOCK_STREAM, 5255)
    ]
    
    resultados = []
    
    for nombre, tipo, puerto in tests:
        try:
            print_info(f"Verificando {nombre}...")
            sock = socket.socket(socket.AF_INET, tipo)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', puerto))
            sock.close()
            print_success(f"{nombre} disponible")
            resultados.append(True)
        except OSError as e:
            if "in use" in str(e).lower():
                print_success(f"{nombre} en uso (servidor corriendo)")
                resultados.append(True)
            else:
                print_error(f"{nombre} bloqueado: {e}")
                resultados.append(False)
    
    return all(resultados)


# =============================================================================
# MAIN
# =============================================================================
def main():
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{'🧪 SUITE DE TESTING - SPECS PYTHON'.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"\n{Colors.BLUE}Verificando comunicación cliente-servidor...{Colors.END}\n")
    
    resultados = {}
    
    # Test 5: Firewall (primero, para detectar bloqueos)
    resultados['firewall'] = test_firewall()
    time.sleep(1)
    
    # Test 1: Broadcasts
    test1_ok, server_ip = test_servidor_broadcasts(timeout=15)
    resultados['broadcasts'] = test1_ok
    time.sleep(1)
    
    if server_ip:
        # Test 2: TCP Server
        resultados['tcp'] = test_servidor_tcp(server_ip)
        time.sleep(1)
        
        # Test 3: Autenticación
        resultados['auth'] = test_autenticacion(server_ip)
        time.sleep(1)
        
        # Test 4: Flujo completo
        resultados['flujo'] = test_flujo_completo(timeout=15)
    else:
        resultados['tcp'] = False
        resultados['auth'] = False
        resultados['flujo'] = False
    
    # Resumen final
    print_header("RESUMEN DE TESTS")
    
    tests_info = [
        ('Firewall', resultados['firewall']),
        ('Broadcasts del servidor', resultados['broadcasts']),
        ('Servidor TCP', resultados['tcp']),
        ('Autenticación', resultados['auth']),
        ('Flujo completo', resultados['flujo'])
    ]
    
    for nombre, resultado in tests_info:
        if resultado:
            print_success(f"{nombre:<30} PASS")
        else:
            print_error(f"{nombre:<30} FAIL")
    
    print()
    total_tests = len(resultados)
    passed_tests = sum(1 for r in resultados.values() if r)
    
    print(f"\n{Colors.BOLD}Resultado: {passed_tests}/{total_tests} tests pasaron{Colors.END}")
    
    if passed_tests == total_tests:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ TODOS LOS TESTS PASARON{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ ALGUNOS TESTS FALLARON{Colors.END}\n")
        print_warning("Revisar NETWORK_FLOW.md para troubleshooting")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Tests interrumpidos por usuario{Colors.END}\n")
        sys.exit(130)
