from PySide6.QtCore import QObject, QThread, Signal


class Hilo(QObject):
    """Ejecuta función en hilo separado para no bloquear UI."""

    terminado = Signal(object)
    error = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._qthread = QThread()
        self.moveToThread(self._qthread)
        self._qthread.started.connect(self._run)
        self._qthread.finished.connect(self._qthread.deleteLater)

    def _run(self):
        try:
            resultado = self.func(*self.args, **self.kwargs)
            self.terminado.emit(resultado)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._qthread.quit()

    def start(self):
        self._qthread.start()


class HiloConProgreso(QObject):
    """Hilo con señal de progreso para actualizar UI en tiempo real"""

    terminado = Signal(object)
    error = Signal(str)
    progreso = Signal(object)  # Emite datos de progreso (ip, estado, index, total, etc)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._qthread = QThread()
        self.moveToThread(self._qthread)
        self._qthread.started.connect(self._run)
        self._qthread.finished.connect(self._qthread.deleteLater)

    def _run(self):
        try:
            # La función debe aceptar un callback de progreso
            resultado = self.func(
                *self.args, callback_progreso=self.progreso.emit, **self.kwargs
            )
            self.terminado.emit(resultado)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._qthread.quit()

    def start(self):
        self._qthread.start()
