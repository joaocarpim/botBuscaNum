from PySide6.QtCore import QObject, Signal


class Communicator(QObject):
    log_signal = Signal(str)
    phone_signal = Signal(str)
    counter_signal = Signal(int)
    status_signal = Signal(str)
