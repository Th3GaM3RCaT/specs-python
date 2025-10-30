import sys
from datos import informeDirectX
from logica_Hilo import Hilo

modo_tarea = "--tarea" in sys.argv

import socket

def escuchar_broadcast(port=37020, on_message=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', port))
    print(f"Escuchando broadcast en puerto {port}...")

    try:
        while True:
            data, addr = sock.recvfrom(1024)  # Espera pasivamente
            mensaje = data.decode(errors="ignore")
            print(f"Mensaje recibido de {addr}: {mensaje}")
            
            if on_message:
                try:
                    on_message(mensaje, addr)
                except Exception as e:
                    print(f"Error en callback: {e}")
    except KeyboardInterrupt:
        print("Cliente detenido.")
        pass
    finally:
        sock.close()



if modo_tarea:
    import threading

    hilo = threading.Thread(target=escuchar_broadcast, daemon=True)
    hilo.start()
    hilo.join()
else:
    from sys import argv
    from json import dump

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (QApplication, QLabel, QMainWindow,
                                   QPushButton, QScrollArea, QVBoxLayout,
                                   QWidget)
    from ui.specs_window_ui import Ui_MainWindow
    

    nombre_tarea = "informe_de_dispositivo"

    app = QApplication(argv)
    scroll = QScrollArea()
    run_button = QPushButton()
    send_button = QPushButton()
    
    script_path = argv[0]
    print(script_path)
    new = {}
    hilo = None

    import logica_specs as lsp
    class MainWindow(QMainWindow, Ui_MainWindow):

        
        vbox = QVBoxLayout()

        def __init__(self):
            super().__init__()
            self.setupUi(self)
            self.initUI()
            self.hilo_enviar = None
            self.hilo_informe = None
            self.hilo_infDirectX = None

        def initUI(self):
            global run_button
            run_button = self.run_button
            run_button.clicked.connect(self.iniciar_informe)

            global send_button
            send_button = self.send_button
            send_button.clicked.connect(self.enviar)

            global scroll
            scroll = self.info_scrollArea

            global new
            new = lsp.new

            self.actionDetener_ejecuci_n.triggered.connect(lambda: lsp.configurar_tarea(2))

            self.actionProgramar_hora_de_ejecuci_n.triggered.connect(
                lambda: lsp.configurar_tarea(0)
            )
            
            return


        def informeDirectX(self):
            from datos.informeDirectX import get_from_inform
            self.hilo_infDirectX = Hilo(get_from_inform)
            self.hilo_infDirectX.error.connect(lambda e: self.statusbar.showMessage("Error:", e))
            self.hilo_infDirectX.start()
        
        def iniciar_informe(self):
            self.informeDirectX()
            run_button.setEnabled(False)
            self.hilo_informe = Hilo(lsp.informe)
            self.hilo_informe.terminado.connect(self.entregar_informe_seguro)
            self.hilo_informe.error.connect(lambda e: self.statusbar.showMessage("Error:", e))
            self.hilo_informe.start()
            
            
       
        def entregar_informe_seguro(self, resultado):
            self.entregar_informe(resultado)
            widget = QWidget()
            widget.setLayout(MainWindow.vbox)
            scroll.setWidget(widget)
            

        def entregar_informe(self,informe=dict()):
            for keys, values in informe.items():
                object = QLabel(keys + ": " + str(values))
                object.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByMouse
                    | Qt.TextInteractionFlag.TextSelectableByKeyboard
                )
                self.vbox.addWidget(object)
            send_button.setEnabled(True)


        def enviar(self):
            self.send_button.setEnabled(False)
            with open("salida.json", "w", encoding="utf-8") as f:
                dump(new, f, indent=4)
                self.hilo_enviar = Hilo(lsp.enviar_a_servidor)
            self.hilo_enviar.start()


    if __name__ == "__main__":
        if "--task" in argv:
            print("modo tarea")
        else:
            window = MainWindow()
            window.show()
            sys.exit(app.exec())
