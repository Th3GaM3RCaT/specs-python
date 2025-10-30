from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsView,
)

app = QApplication([])

scene = QGraphicsScene()
view = QGraphicsView(scene)
view.setRenderHint(view.renderHints() | QPainter.RenderHint.Antialiasing)

# Nodo 1 y nodo 2
nodo1 = QGraphicsEllipseItem(0, 0, 50, 50)
nodo1.setBrush(QColor("#4FC3F7"))
nodo2 = QGraphicsEllipseItem(150, 100, 50, 50)
nodo2.setBrush(QColor("#81C784"))

# Conexión entre ellos
linea = QGraphicsLineItem(25, 25, 175, 125)
linea.setPen(QPen(Qt.GlobalColor.black, 2))

scene.addItem(linea)
scene.addItem(nodo1)
scene.addItem(nodo2)

view.setWindowTitle("Mapa de red estilo Qt6")
view.resize(400, 300)
view.show()
app.exec()
