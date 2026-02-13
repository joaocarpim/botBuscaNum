import time
import threading
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QListWidget,
    QSpacerItem, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor

# Imports do Projeto
from src.core.signals import Communicator
from src.core.worker import ScraperWorker
from src.ui.widgets import RoundedCard
from src.ui.styles import *


class LeadHunterPro(QMainWindow):
    def __init__(self):
        super().__init__()

        self.comm = Communicator()
        self.worker = ScraperWorker(self.comm)

        self.selected_niche = ""
        self.selected_qty = 10
        self.start_time = None
        self.pulse_state = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_active_time)

        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self.animate_pulse)

        self.init_ui()
        self.setup_signals()

    def init_ui(self):
        self.setWindowTitle("LeadHunter Maps PRO // Modular v2.1")
        self.setGeometry(100, 100, 950, 600)
        self.setStyleSheet(MAIN_WINDOW_STYLE)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        main_layout.addWidget(self.create_header())

        content = QHBoxLayout()
        content.addLayout(self.create_left_column(), 55)
        content.addLayout(self.create_right_column(), 45)
        main_layout.addLayout(content)

    def create_header(self):
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        icon = QLabel("⚡")
        icon.setStyleSheet("font-size: 32px; color: #FFA500;")
        layout.addWidget(icon)

        titles = QWidget()
        t_layout = QVBoxLayout(titles)
        t_layout.setContentsMargins(0, 0, 0, 0)
        t_layout.setSpacing(0)

        title = QLabel("LEADHUNTER MAPS")
        title.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #FFFFFF;")
        sub = QLabel("PROFESSIONAL EDITION 2.1 // MODULAR")
        sub.setStyleSheet(
            "font-size: 9px; color: #666666; letter-spacing: 1px;")
        t_layout.addWidget(title)
        t_layout.addWidget(sub)
        layout.addWidget(titles)

        layout.addStretch()

        # Status
        self.status_indicator = RoundedCard()
        self.status_indicator.setFixedSize(180, 50)
        s_layout = QHBoxLayout(self.status_indicator)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #FF4444; font-size: 20px;")
        s_layout.addWidget(self.status_dot)

        self.status_label = QLabel("DESCONECTADO")
        self.status_label.setStyleSheet(
            "color: #FF4444; font-size: 11px; font-weight: bold;")
        s_layout.addWidget(self.status_label)

        layout.addWidget(self.status_indicator)
        return header

    def create_left_column(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # Config Card
        setup_card = RoundedCard()
        s_layout = QVBoxLayout(setup_card)
        s_layout.setContentsMargins(20, 18, 20, 18)

        lbl = QLabel("◆ CONFIGURAÇÃO DE EXTRAÇÃO")
        lbl.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #00FF9C;")
        s_layout.addWidget(lbl)

        self.niche_input = QLineEdit()
        self.niche_input.setPlaceholderText("Digite o nicho alvo...")
        self.niche_input.setFixedHeight(38)
        self.niche_input.setStyleSheet(INPUT_STYLE)
        s_layout.addWidget(self.niche_input)

        # Quick Buttons
        q_layout = QHBoxLayout()
        for niche in ["Dentista", "Imobiliária", "Advogado"]:
            btn = QPushButton(niche)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(BTN_DEFAULT_STYLE)
            btn.clicked.connect(lambda c, n=niche: self.set_niche(n))
            q_layout.addWidget(btn)
        s_layout.addLayout(q_layout)

        # Quantity
        s_layout.addWidget(QLabel("META DE CONTATOS"))
        qty_layout = QHBoxLayout()
        for qty in [10, 20, 50]:
            btn = QPushButton(str(qty))
            btn.setFixedSize(60, 32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #0A0A0F; color: #FFFFFF; border: 1px solid #333; border-radius: 8px; font-weight: bold;
                }
                QPushButton:hover { border: 1px solid #00FF9C; color: #00FF9C; }
            """)
            btn.clicked.connect(lambda c, q=qty: self.set_qty(q))
            qty_layout.addWidget(btn)
        qty_layout.addStretch()
        s_layout.addLayout(qty_layout)

        layout.addWidget(setup_card)

        # Action Button
        self.search_btn = QPushButton("🔍 BUSCAR CONTATOS")
        self.search_btn.setFixedHeight(50)
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setStyleSheet(BTN_ACTION_STYLE)
        self.search_btn.clicked.connect(self.start_extraction)
        layout.addWidget(self.search_btn)

        # Contacts List
        list_card = RoundedCard()
        l_layout = QVBoxLayout(list_card)
        l_layout.setContentsMargins(0, 0, 0, 0)

        # List Header
        lh = QWidget()
        lh.setFixedHeight(45)
        lh.setStyleSheet(
            "background: #0A0A0F; border-radius: 15px; border-bottom-left-radius: 0; border-bottom-right-radius: 0;")
        lh_layout = QHBoxLayout(lh)
        lh_layout.addWidget(QLabel("◉ CONTATOS EXTRAÍDOS"))
        lh_layout.addStretch()

        copy_btn = QPushButton("📋 COPIAR")
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet(BTN_DEFAULT_STYLE)
        copy_btn.clicked.connect(self.copy_contacts)
        lh_layout.addWidget(copy_btn)

        l_layout.addWidget(lh)

        self.contacts_list = QListWidget()
        self.contacts_list.setStyleSheet(LIST_STYLE)
        l_layout.addWidget(self.contacts_list)

        layout.addWidget(list_card)
        return layout

    def create_right_column(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # Metrics
        m_card = RoundedCard()
        m_layout = QVBoxLayout(m_card)
        m_layout.setContentsMargins(20, 18, 20, 18)
        m_layout.addWidget(QLabel("◎ MÉTRICAS"))

        self.time_metric = self.create_metric("⏱ TEMPO", "00:00:00")
        m_layout.addWidget(self.time_metric)
        self.extracted_metric = self.create_metric("✦ EXTRAÍDOS", "0")
        m_layout.addWidget(self.extracted_metric)

        layout.addWidget(m_card)

        # Console
        t_card = RoundedCard()
        t_layout = QVBoxLayout(t_card)
        t_layout.setContentsMargins(0, 0, 0, 0)

        th = QWidget()
        th.setFixedHeight(45)
        th.setStyleSheet(
            "background: #0A0A0F; border-radius: 15px; border-bottom-left-radius: 0; border-bottom-right-radius: 0;")
        thl = QHBoxLayout(th)
        thl.addWidget(QLabel("✦ TERMINAL"))
        t_layout.addWidget(th)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet(CONSOLE_STYLE)
        t_layout.addWidget(self.console)

        layout.addWidget(t_card)
        return layout

    def create_metric(self, label, val):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(QLabel(label))
        l.addStretch()
        v = QLabel(val)
        v.setObjectName(f"val_{label}")
        v.setStyleSheet(
            "background: #00FF9C; color: #000; border-radius: 10px; padding: 5px 10px; font-weight: bold;")
        l.addWidget(v)
        return w

    def setup_signals(self):
        self.comm.log_signal.connect(self.append_log)
        self.comm.phone_signal.connect(self.add_phone)
        self.comm.counter_signal.connect(self.update_count)
        self.comm.status_signal.connect(self.update_status)

    def set_niche(self, n):
        self.selected_niche = n
        self.niche_input.setText(n)

    def set_qty(self, q):
        self.selected_qty = q
        self.append_log(f"Meta: {q}")

    def append_log(self, msg):
        self.console.append(msg)
        self.console.moveCursor(QTextCursor.End)

    def add_phone(self, phone):
        self.contacts_list.addItem(phone)

    def update_count(self, n):
        for child in self.extracted_metric.findChildren(QLabel):
            if "val_" in child.objectName():
                child.setText(str(n))

    def update_status(self, status):
        self.status_label.setText(status)
        if status == "CONECTADO":
            self.status_dot.setStyleSheet("color: #00FF9C;")
            self.status_label.setStyleSheet("color: #00FF9C;")
            self.search_btn.setEnabled(False)
            self.search_btn.setStyleSheet(BTN_DISABLED_STYLE)
            self.start_time = time.time()
            self.timer.start(1000)
            self.pulse_timer.start(500)
        else:
            self.status_dot.setStyleSheet("color: #FF4444;")
            self.status_label.setStyleSheet("color: #FF4444;")
            self.search_btn.setEnabled(True)
            self.search_btn.setStyleSheet(BTN_ACTION_STYLE)
            self.timer.stop()
            self.pulse_timer.stop()

    def update_active_time(self):
        if self.start_time:
            elapsed = int(time.time() - self.start_time)
            t_str = time.strftime('%H:%M:%S', time.gmtime(elapsed))
            for child in self.time_metric.findChildren(QLabel):
                if "val_" in child.objectName():
                    child.setText(t_str)

    def animate_pulse(self):
        self.pulse_state = not self.pulse_state
        c = "#00FF9C" if self.pulse_state else "#00D17F"
        self.status_dot.setStyleSheet(f"color: {c}; font-size: 20px;")

    def start_extraction(self):
        niche = self.niche_input.text() or self.selected_niche
        if not niche:
            self.append_log("❌ Digite um nicho!")
            return

        self.contacts_list.clear()
        self.console.clear()

        t = threading.Thread(target=self.worker.start_scraping, args=(
            niche, self.selected_qty), daemon=True)
        t.start()

    def copy_contacts(self):
        items = [self.contacts_list.item(i).text()
                 for i in range(self.contacts_list.count())]
        QApplication.clipboard().setText("\n".join(items))
        self.append_log("✅ Copiado!")

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()
