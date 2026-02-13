MAIN_WINDOW_STYLE = """
    QMainWindow {
        background: #0A0A0F;
    }
    QWidget {
        background: transparent;
        color: #FFFFFF;
        font-family: 'Segoe UI', Arial;
    }
    QLabel {
        background: transparent;
    }
"""

ROUNDED_CARD_STYLE = """
    QFrame {
        background: #1A1A23;
        border: 1px solid #2A2A33;
        border-radius: 15px;
    }
"""

INPUT_STYLE = """
    QLineEdit {
        background: #0A0A0F;
        color: #FFFFFF;
        border: 1px solid #00FF9C;
        border-radius: 8px;
        padding: 0 15px;
        font-size: 11px;
    }
    QLineEdit:focus {
        border: 2px solid #00FF9C;
    }
"""

BTN_DEFAULT_STYLE = """
    QPushButton {
        background: transparent;
        color: #00FF9C;
        border: 1px solid #00FF9C;
        border-radius: 6px;
        font-size: 9px;
        font-weight: bold;
        padding: 0 12px;
    }
    QPushButton:hover {
        background: #00FF9C;
        color: #0A0A0F;
        transform: scale(1.05);
    }
    QPushButton:pressed {
        background: #00D17F;
        color: #0A0A0F;
    }
"""

BTN_ACTION_STYLE = """
    QPushButton {
        background: transparent;
        color: #00FF9C;
        border: 2px solid #00FF9C;
        border-radius: 10px;
        font-size: 12px;
        font-weight: bold;
        letter-spacing: 1px;
    }
    QPushButton:hover {
        background: rgba(0, 255, 156, 0.15);
        border: 2px solid #00FFB3;
    }
    QPushButton:pressed {
        background: rgba(0, 255, 156, 0.25);
    }
"""

BTN_DISABLED_STYLE = """
    QPushButton {
        background: transparent;
        color: #555555;
        border: 2px solid #333333;
        border-radius: 10px;
        font-size: 12px;
        font-weight: bold;
        letter-spacing: 1px;
    }
"""

LIST_STYLE = """
    QListWidget {
        background: #1A1A23;
        color: #AAAAAA;
        border: none;
        border-radius: 0;
        border-bottom-left-radius: 15px;
        border-bottom-right-radius: 15px;
        padding: 15px;
        font-size: 9px;
        font-family: 'Consolas', monospace;
        line-height: 1.6;
    }
    QListWidget::item {
        padding: 6px 8px;
        border-radius: 6px;
        margin: 2px 0;
        color: #CCCCCC;
    }
    QListWidget::item:selected {
        background: #00FF9C;
        color: #0A0A0F;
    }
    QListWidget::item:hover {
        background: rgba(0, 255, 156, 0.1);
    }
"""

CONSOLE_STYLE = """
    QTextEdit {
        background: #000000;
        color: #00FF9C;
        border: none;
        border-radius: 0;
        border-bottom-left-radius: 15px;
        border-bottom-right-radius: 15px;
        padding: 15px;
        font-family: 'Courier New', monospace;
        font-size: 9px;
        line-height: 1.4;
    }
"""
