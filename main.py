import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from src.ui.window import LeadHunterPro


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Palette Dark Theme Global
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(10, 10, 15))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Base, QColor(26, 26, 35))
    palette.setColor(QPalette.Text, QColor(255, 255, 255))
    app.setPalette(palette)

    window = LeadHunterPro()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
