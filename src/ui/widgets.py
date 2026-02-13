from PySide6.QtWidgets import QFrame
from src.ui.styles import ROUNDED_CARD_STYLE


class RoundedCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(ROUNDED_CARD_STYLE)
