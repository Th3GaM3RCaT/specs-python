import csv
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem
from PySide6.QtCore import QTimer, Qt
from ui.all_specs_ui import Ui_MainWindow
from datetime import datetime
from threading import Thread
import random
from logica_Hilo import Hilo

hilo = None

from pathlib import Path


def buscar_por_patron(dirpath, patron="optimized_scan_*.csv"):
    p = Path(dirpath)
    matches = list(p.glob(patron))
    m = None
    for m in matches:
        pass
    print(m)
    return m


def csv_a_lista_dicts(ruta_csv):
    datos = []
    with open(ruta_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for fila in reader:
            datos.append(dict(fila))
    return datos


def obtener_dispositivos_red():

    dispositivos = []
    datos = []
    datos = csv_a_lista_dicts(buscar_por_patron("."))
    for fila in datos:
        ip, mac = fila.items()
        dispositivos.append(
            {
                "nombre": f"Equipo-{datos.index(fila)+1}",
                "ip": ip[1],
                "mac": mac[1],
                "activo": random.choice([True, False]),
                "ultima": datetime.now().strftime("%H:%M:%S"),
            }
        )

    return dispositivos


class AllSpecs(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # 🚀 iniciar actualización periódica
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.actualizar_tabla_async)
        self.timer.start(60000)  # cada 1 minuto

        # primera carga inmediata
        self.actualizar_tabla_async()

    def actualizar_tabla_async(self):
        self.tableWidget.setEnabled(False)
        self.statusbar.showMessage("Escaneando red...")
        hilo = Thread(target=self._actualizar_tabla_worker)
        hilo.daemon = True
        hilo.start()

    def _actualizar_tabla_worker(self):
        try:
            scan()
            dispositivos = obtener_dispositivos_red()
            # actualizar GUI desde hilo principal
            QApplication.postEvent(self, ActualizarTablaEvent(dispositivos))
        except Exception as e:
            QApplication.postEvent(self, ActualizarTablaEvent([], str(e)))

    def customEvent(self, event):
        if isinstance(event, ActualizarTablaEvent):
            if event.error:
                self.statusbar.showMessage(f"Error: {event.error}")
            else:
                self.mostrar_dispositivos(event.dispositivos)
                self.statusbar.showMessage(
                    f"Última actualización: {datetime.now().strftime('%H:%M:%S')}"
                )
            self.tableWidget.setEnabled(True)

    def mostrar_dispositivos(self, dispositivos):
        self.tableWidget.setRowCount(len(dispositivos))
        for fila, d in enumerate(dispositivos):
            self.tableWidget.setItem(fila, 0, QTableWidgetItem(d.get("nombre", "")))
            self.tableWidget.setItem(fila, 1, QTableWidgetItem(d.get("ip", "")))
            self.tableWidget.setItem(fila, 2, QTableWidgetItem(d.get("mac", "")))

            estado_item = QTableWidgetItem("🟢" if d.get("activo") else "🔴")
            estado_item.setTextAlignment(Qt.AlignCenter)  # type: ignore
            self.tableWidget.setItem(fila, 3, estado_item)

            self.tableWidget.setItem(fila, 4, QTableWidgetItem(d.get("ultima", "")))


def scan():
    import datos.scan_ip_mac as scan_ip_mac

    global hilo
    hilo = Hilo(scan_ip_mac.main)
    hilo.start()


from PySide6.QtCore import QEvent


class ActualizarTablaEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, dispositivos, error=None):
        super().__init__(self.EVENT_TYPE)
        self.dispositivos = dispositivos
        self.error = error


if __name__ == "__main__":
    app = QApplication([])
    win = AllSpecs()
    win.show()
    app.exec()
##
# lista desplegable
# ventana emergente
# informacion al costado
# sumario al costado
#
#
# disposicion 60 40 para tabla e infomracion detallada
#
# informacion detallada permite seleccionar componente para ver debajo informacion tecnica
#
# cuadro de informacion tecnica puede cambiar por registros de cambios
# registros de cambios puede abrir una vista emergente con historial
#
#
# lo otro podria ser cambiar el modo de la aplicacion conservando la disposicion
# cambiar entre vista de dispositivos y vista de registros de cambios
#
#
#
# tener siempre en cuenta la estructura de la DB
# preguntarle a claude pasandole abundante contexto y la DB
#
# #
