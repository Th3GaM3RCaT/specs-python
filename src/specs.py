from sys import argv

from json import dumps

modo_tarea = "--tarea" in argv


def escuchar_solicitudes(port=5256):
    """Cliente escucha solicitudes TCP del servidor.

    Args:
        port (int): Puerto TCP donde escuchar solicitudes del servidor

    Note:
        El servidor puede solicitar datos activamente conectándose a este puerto.
    """
    from logica.logica_specs import new

    print(f"[DAEMON] Cliente escuchando solicitudes en puerto {port}...")
    from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, timeout

    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server_socket.settimeout(1.0)

    try:
        server_socket.bind(("0.0.0.0", port))
        server_socket.listen(5)
        print(f"[OK] Escuchando en puerto {port}")
        print("[INFO] El servidor puede solicitar datos en cualquier momento")
        print("Presiona Ctrl+C para detener\n")

        request_count = 0

        while True:
            try:
                conn, addr = server_socket.accept()
                request_count += 1

                print(f"\n[SOLICITUD #{request_count}] Servidor conectado: {addr[0]}")

                try:
                    conn.settimeout(5)
                    data = conn.recv(1024).decode("utf-8").strip()

                    if data == "GET_SPECS":
                        print("[PROCESO] Recopilando especificaciones...")

                        # Usar función compartida que incluye informe + DirectX
                        from logica.logica_specs import preparar_datos_completos

                        preparar_datos_completos()

                        print("[OK] Datos recopilados")

                        json_data = dumps(new, ensure_ascii=False)
                        conn.sendall(json_data.encode("utf-8"))
                        print(f"[OK] Enviados {len(json_data)} bytes\n")

                    elif data == "PING":
                        response = {"status": "alive"}
                        conn.sendall(dumps(response).encode("utf-8"))
                        print("[OK] PING respondido\n")

                except Exception as e:
                    print(f"[ERROR] Error procesando: {e}\n")

                finally:
                    conn.close()

            except timeout:
                continue

    except KeyboardInterrupt:
        print("\n[STOP] Cliente detenido por usuario")
    finally:
        server_socket.close()


if modo_tarea:
    # Modo tarea: Cliente escucha solicitudes del servidor
    print("=" * 70)
    print("[MODO TAREA] Activado")
    print("=" * 70)

    from logica.logica_specs import configurar_tarea

    # Configurar tarea programada si no existe
    if configurar_tarea():
        configurar_tarea(0)
        print("[MODO TAREA] Nueva tarea programada creada.")

    # Escuchar solicitudes del servidor
    escuchar_solicitudes(port=5256)

else:
    # Modo GUI: interfaz gráfica
    from logica.logica_Hilo import Hilo
    from sys import argv
    from json import dump
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QApplication,
        QLabel,
        QMainWindow,
        QVBoxLayout,
        QWidget,
    )
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
            self.actionDetener_ejecuci_n.triggered.connect(
                lambda: lsp.configurar_tarea(2)
            )
            self.actionProgramar_hora_de_ejecuci_n.triggered.connect(
                lambda: lsp.configurar_tarea(0)
            )

        def informeDirectX(self):
            """Ejecuta reporte DirectX en background."""
            from datos.informeDirectX import get_from_inform

            self.hilo_infDirectX = Hilo(get_from_inform)
            self.hilo_infDirectX.error.connect(
                lambda e: self.statusbar.showMessage(f"Error: {e}")
            )
            self.hilo_infDirectX.start()

        def iniciar_informe(self):
            """Inicia recopilación de información del sistema."""
            self.statusbar.showMessage(
                "Iniciando recopilación de especificaciones...", 3000
            )
            self.informeDirectX()
            self.run_button.setEnabled(False)
            self.hilo_informe = Hilo(lsp.informe)
            self.hilo_informe.terminado.connect(self.entregar_informe_seguro)
            self.hilo_informe.error.connect(
                lambda e: self.statusbar.showMessage(f"[ERROR] {e}", 5000)
            )
            self.hilo_informe.start()

        def entregar_informe_seguro(self, resultado):
            """Actualiza UI con el informe generado (thread-safe)."""
            self.statusbar.showMessage(
                "[OK] Especificaciones recopiladas exitosamente", 3000
            )
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
            self.hilo_enviar.terminado.connect(
                lambda: self.send_button.setEnabled(True)
            )
            self.hilo_enviar.error.connect(
                lambda e: self.statusbar.showMessage(f" Error al enviar: {e}", 5000)
            )
            self.hilo_enviar.start()

    def main():
        """Función principal para ejecutar la GUI."""
        if "--tarea" in argv:
            print("modo tarea")
        else:
            window = MainWindow()
            window.show()
            from sys import exit

            exit(app.exec())

    # Ejecutar solo si es el script principal
    if __name__ == "__main__":
        main()
