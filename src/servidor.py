import glob
from sys import argv

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
from logica.logica_Hilo import Hilo

from ui.servidor_specs_window_ui import Ui_MainWindow
from logica import logica_servidor as ls

app = QApplication.instance()
if app is None:
    app = QApplication(argv)
archivos_json = glob.glob("*.json")


class MainWindow(QMainWindow, Ui_MainWindow):

    vbox = QVBoxLayout()

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.initUI()

    def initUI(self):
        global equipo_comboBox
        equipo_comboBox = self.equipo_comboBox
        equipo_comboBox.addItems(archivos_json)
        self.equipo_comboBox.activated.connect(self.check_index)

        global info_scrollArea
        info_scrollArea = self.info_scrollArea

        global modelo_textLabel
        modelo_textLabel = self.modelo_label

        global usuario_textLabel
        usuario_textLabel = self.usuario_label

        global mac_textLabel
        mac_textLabel = self.mac_label

        global actualizar_button
        actualizar_button = self.actualizar_pushButton
        actualizar_button.clicked.connect(self.iniciar_busqueda)

        global scan_button
        scan_button = self.scan_pushButton
        scan_button.clicked.connect(self.escanear)

        return

    def check_index(self, index):
        self.cargar_info(ls.abrir_json(self.equipo_comboBox.currentIndex()))

    def iniciar_busqueda(self):
        self.worker_anunciar = Hilo(ls.anunciar_ip)
        self.worker_anunciar.start()
        self.worker_consultar = Hilo(ls.consultar_informacion)
        self.worker_consultar.start()

    def escanear(self):
        import datos.scan_ip_mac as scan_ip_mac

        self.worker_escanear = Hilo(scan_ip_mac.main)
        self.worker_escanear.start()

    def cargar_info(self, informe=dict()):
        for keys, values in informe.items():
            object = QLabel(keys + ": " + str(values))
            object.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
                | Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
            MainWindow.vbox.addWidget(object)
        widget = QWidget()
        widget.setLayout(MainWindow.vbox)
        info_scrollArea.setWidget(widget)
        modelo_textLabel.setText(f"Modelo:  {informe.get("Model")}")
        usuario_textLabel.setText(f"Usuario:  {informe.get("Name")}")
        mac_textLabel.setText(f"MAC:      {informe.get("MAC Address")}")

        
    def customEvent(self, event):
            #if isinstance(event, ActualizarTablaEvent):
                if event.error:
                    self.statusbar.showMessage(f"Error: {event.error}")


if __name__ == "__main__":

    window = MainWindow()
    window.show()
    app.exec()
