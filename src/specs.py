import sys
import socket
import time
from logica.logica_Hilo import Hilo

modo_tarea = "--tarea" in sys.argv

def escuchar_broadcast(port=None, on_message=None):
    """Escucha broadcasts UDP en el puerto especificado.
    
    Args:
        port (int): Puerto UDP donde escuchar broadcasts. Si es None, usa valor del .env
        on_message (callable): Callback que recibe (mensaje, direccion) cuando llega broadcast
    
    Note:
        Ejecuta en loop infinito hasta Ctrl+C. Ideal para modo daemon.
    """
    # Cargar puerto desde .env si no se especifica
    if port is None:
        try:
            from config.security_config import DISCOVERY_PORT
            port = DISCOVERY_PORT
        except ImportError:
            port = 37020  # Fallback
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', port))
    print(f"[ESCUCHA] Escuchando broadcasts en puerto {port}...")

    try:
        while True:
            data, addr = sock.recvfrom(1024)
            mensaje = data.decode(errors="ignore")
            print(f"[BROADCAST] Broadcast recibido de {addr[0]}: {mensaje}")
            
            if on_message:
                try:
                    on_message(mensaje, addr)
                except Exception as e:
                    print(f"[ERROR] Error en callback: {e}")
                    import traceback
                    traceback.print_exc()
    except KeyboardInterrupt:
        print("\n[STOP] Cliente detenido por usuario.")
    except Exception as e:
        print(f"Error en escucha: {e}")
        
    finally:
        sock.close()


if modo_tarea:
    # Modo tarea programada: ejecuta inmediatamente o espera broadcasts según configuración
    print("=" * 70)
    print("[MODO TAREA] Activado")
    print("=" * 70)
    
    from logica import logica_specs as lsp
    from datetime import datetime
    from pathlib import Path
    from json import load
    
    #consultar tarea, si no existe crear una nueva
    if lsp.configurar_tarea():
        lsp.configurar_tarea(0)
        print("[MODO TAREA] Nueva tarea programada creada.")
    
    # Verificar modo de operación (manual vs discovery)
    config_path = Path(__file__).parent.parent / "config" / "server_config.json"
    use_discovery = True
    
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = load(f)
                use_discovery = config.get("use_discovery", True)
        except Exception as e:
            print(f"[WARN] Error al leer configuracion: {e}")
    
    if not use_discovery:
        # MODO MANUAL: Ejecutar inmediatamente sin esperar broadcasts
        print("Modo configuracion manual detectado")
        print("Ejecutando recopilacion inmediata...\n")
        
        try:
            print(f"[START] Iniciando recopilacion de especificaciones...")
            print(f"[TIME] Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 1. Ejecutar informe (recopilar datos del sistema)
            print("\n1) Recopilando datos del sistema...")
            lsp.informe()
            print("   [OK] Datos recopilados exitosamente")
            
            # 2. Enviar datos al servidor
            print("\n2) Enviando datos al servidor...")
            lsp.enviar_a_servidor()
            print("   [OK] Datos enviados al servidor")
            
            print(f"\n[DONE] Proceso completado exitosamente")
            print(f"{'='*70}\n")
            
        except Exception as e:
            print(f"\n[ERROR] Error durante el proceso: {e}")
            import traceback
            traceback.print_exc()
            print(f"{'='*70}\n")
            sys.exit(1)
    else:
        # MODO DISCOVERY: Esperar broadcasts del servidor
        print("Esperando solicitud del servidor...")
        print("Presiona Ctrl+C para detener\n")
        
        # Cooldown para evitar multiples ejecuciones
        ultima_ejecucion = 0
        COOLDOWN_SEGUNDOS = 60  # Esperar 60 segundos entre ejecuciones
        
        def manejar_broadcast(mensaje, addr):
            """Callback que se ejecuta al recibir broadcast del servidor."""
            global ultima_ejecucion
            
            # Verificar si es el mensaje del servidor
            if "servidor specs" in mensaje.lower():
                servidor_ip = addr[0]
                print(f"\n{'='*70}")
                print(f"[DISCOVERY] Servidor detectado en {servidor_ip}")
                
                # Verificar cooldown
                tiempo_actual = time.time()
                if tiempo_actual - ultima_ejecucion < COOLDOWN_SEGUNDOS:
                    tiempo_restante = int(COOLDOWN_SEGUNDOS - (tiempo_actual - ultima_ejecucion))
                    print(f"[COOLDOWN] Esperar {tiempo_restante} segundos...")
                    print(f"{'='*70}\n")
                    return
                
                ultima_ejecucion = tiempo_actual
                
                print(f"[START] Iniciando recopilacion de especificaciones...")
                print(f"[TIME] Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                try:
                    # 1. Ejecutar informe (recopilar datos del sistema)
                    print("\n1) Recopilando datos del sistema...")
                    lsp.informe()
                    print("   [OK] Datos recopilados exitosamente")
                    
                    # 2. Enviar datos al servidor (pasando IP detectada)
                    print("\n2) Enviando datos al servidor...")
                    lsp.enviar_a_servidor(server_ip=servidor_ip)
                    print("   [OK] Datos enviados al servidor")
                    
                    print(f"\n[DONE] Proceso completado exitosamente")
                    print(f"{'='*70}\n")
                    
                except Exception as e:
                    print(f"\n[ERROR] Error durante el proceso: {e}")
                    import traceback
                    traceback.print_exc()
                    print(f"{'='*70}\n")
        
        # Ejecutar escucha con callback (puerto desde .env)
        escuchar_broadcast(on_message=manejar_broadcast)
else:
    # Modo GUI: interfaz gráfica
    from sys import argv
    from json import dump
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (QApplication, QLabel, QMainWindow,
                                   QPushButton, QScrollArea, QVBoxLayout,
                                   QWidget)
    from ui.specs_window_ui import Ui_MainWindow
    from logica import logica_specs as lsp

    app = QApplication(argv)
    class MainWindow(QMainWindow, Ui_MainWindow):
        """Ventana principal del cliente de especificaciones."""

        def __init__(self):
            super().__init__()
            self.setupUi(self)
            self.hilo_enviar = None
            self.hilo_informe = None
            self.hilo_infDirectX = None
            self.vbox = QVBoxLayout()
            self.initUI()
            
            # Configurar callback de estado para logica_specs
            lsp.set_status_callback(self.actualizar_estado)

        def actualizar_estado(self, mensaje):
            """Actualiza la barra de estado de forma thread-safe.
            
            Args:
                mensaje (str): Mensaje a mostrar en la statusbar
            """
            # showMessage es thread-safe en Qt
            self.statusbar.showMessage(mensaje, 5000)  # 5 segundos de timeout

        def initUI(self):
            """Inicializa señales y conexiones de la UI."""
            self.run_button.clicked.connect(self.iniciar_informe)
            self.send_button.clicked.connect(self.enviar)
            self.actionDetener_ejecuci_n.triggered.connect(lambda: lsp.configurar_tarea(2))
            self.actionProgramar_hora_de_ejecuci_n.triggered.connect(lambda: lsp.configurar_tarea(0))

        def informeDirectX(self):
            """Ejecuta reporte DirectX en background."""
            from datos.informeDirectX import get_from_inform
            self.hilo_infDirectX = Hilo(get_from_inform)
            self.hilo_infDirectX.error.connect(lambda e: self.statusbar.showMessage(f"Error: {e}"))
            self.hilo_infDirectX.start()
        
        def iniciar_informe(self):
            """Inicia recopilación de información del sistema."""
            self.statusbar.showMessage("Iniciando recopilación de especificaciones...", 3000)
            self.informeDirectX()
            self.run_button.setEnabled(False)
            self.hilo_informe = Hilo(lsp.informe)
            self.hilo_informe.terminado.connect(self.entregar_informe_seguro)
            self.hilo_informe.error.connect(lambda e: self.statusbar.showMessage(f"[ERROR] {e}", 5000))
            self.hilo_informe.start()
       
        def entregar_informe_seguro(self, resultado):
            """Actualiza UI con el informe generado (thread-safe)."""
            self.statusbar.showMessage("[OK] Especificaciones recopiladas exitosamente", 3000)
            self.entregar_informe(resultado)
            widget = QWidget()
            widget.setLayout(self.vbox)
            self.info_scrollArea.setWidget(widget)

        def entregar_informe(self, informe=dict()):
            """Muestra el informe en la interfaz."""
            for keys, values in informe.items():
                label = QLabel(f"{keys}: {values}")
                label.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByMouse
                    | Qt.TextInteractionFlag.TextSelectableByKeyboard
                )
                self.vbox.addWidget(label)
            self.send_button.setEnabled(True)

        def enviar(self):
            """Envía especificaciones al servidor."""
            self.statusbar.showMessage(" Preparando envío de datos...", 2000)
            self.send_button.setEnabled(False)
            with open("salida.json", "w", encoding="utf-8") as f:
                dump(lsp.new, f, indent=4)
            self.hilo_enviar = Hilo(lsp.enviar_a_servidor)
            self.hilo_enviar.terminado.connect(lambda: self.send_button.setEnabled(True))
            self.hilo_enviar.error.connect(lambda e: self.statusbar.showMessage(f" Error al enviar: {e}", 5000))
            self.hilo_enviar.start()

    def main():
        """Función principal para ejecutar la GUI."""
        if "--task" in argv:
            print("modo tarea")
        else:
            window = MainWindow()
            window.show()
            sys.exit(app.exec())
    
    # Ejecutar solo si es el script principal
    if __name__ == "__main__":
        main()
