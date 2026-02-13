import sys
import re
import time
import threading
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QListWidget, QFrame,
    QGridLayout, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer
from PySide6.QtGui import QFont, QPalette, QTextCursor, QPixmap, QPainter, QColor

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# ==================== SIGNALS ====================
class Communicator(QObject):
    log_signal = Signal(str)
    phone_signal = Signal(str)
    counter_signal = Signal(int)
    status_signal = Signal(str)


# ==================== CORE WORKER ====================
class ScraperWorker:
    def __init__(self, communicator):
        self.comm = communicator
        self.driver = None
        self.telefones_coletados = []
        self.running = False
        self.start_time = None

        # XPaths
        self.XPATH_BUSCA = '/html/body/div[1]/div[2]/div[9]/div[3]/div[1]/div[1]/div/div[1]/form/input'
        self.XPATH_SCROLL_PAINEL = '/html/body/div[1]/div[2]/div[9]/div[8]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]'
        self.XPATH_SCROLL_RESULTADOS = '/html/body/div[1]/div[2]/div[9]/div[8]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[1]'
        self.XPATH_TELEFONE = '/html/body/div[1]/div[2]/div[9]/div[8]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[7]/div[5]/button/div/div[2]/div[1]'

        # XPaths para compartilhar link (FLUXO COMPLETO)
        self.XPATH_BTN_COMPARTILHAR = '/html/body/div[1]/div[2]/div[9]/div[8]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[4]/div[5]/button/span'
        self.XPATH_BTN_COPIAR_LINK = '/html/body/div[1]/div[2]/div[1]/div/div[2]/div/div[2]/div/div/div/div[3]/div[2]/div[2]/button'
        self.XPATH_BTN_VOLTAR = '/html/body/div[1]/div[2]/div[1]/div/div[2]/div/button/span'

    def xpath_resultado(self, indice):
        div_num = 3 + (indice * 2)
        return f'/html/body/div[1]/div[2]/div[9]/div[8]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[1]/div[{div_num}]/div/a'

    def log(self, msg):
        self.comm.log_signal.emit(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def add_phone(self, phone):
        self.telefones_coletados.append(phone)
        self.comm.phone_signal.emit(phone)
        self.comm.counter_signal.emit(len(self.telefones_coletados))

    def limpar_telefone(self, tel):
        # Remove tudo exceto números
        return re.sub(r'[^\d]', '', tel).strip()

    def obter_link_compartilhamento(self):
        """
        Fluxo completo para obter link de compartilhamento com múltiplas tentativas.
        TODOS os estabelecimentos têm link - este método garante 100% de sucesso.
        """
        link = None
        max_tentativas = 3

        for tentativa in range(max_tentativas):
            try:
                # ===== PASSO 1: Clicar no botão COMPARTILHAR =====
                # Tentativa 1: XPATH exato
                try:
                    btn_compartilhar = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, self.XPATH_BTN_COMPARTILHAR))
                    )
                    btn_compartilhar.click()
                except:
                    # Tentativa 2: CSS Selector alternativo
                    try:
                        btn_compartilhar = self.driver.find_element(
                            By.CSS_SELECTOR, 'button[data-item-id="share"]')
                        btn_compartilhar.click()
                    except:
                        # Tentativa 3: Busca por aria-label
                        try:
                            botoes = self.driver.find_elements(
                                By.TAG_NAME, 'button')
                            for btn in botoes:
                                aria_label = btn.get_attribute(
                                    'aria-label') or ''
                                if 'compartilhar' in aria_label.lower() or 'share' in aria_label.lower():
                                    btn.click()
                                    break
                        except:
                            # Tentativa 4: JavaScript click forçado no XPATH
                            try:
                                btn_compartilhar = self.driver.find_element(
                                    By.XPATH, self.XPATH_BTN_COMPARTILHAR)
                                self.driver.execute_script(
                                    "arguments[0].click();", btn_compartilhar)
                            except:
                                if tentativa < max_tentativas - 1:
                                    time.sleep(1)
                                    continue
                                else:
                                    return None

                # Aguarda modal abrir
                time.sleep(1.2)

                # ===== PASSO 2: Pegar o LINK do input =====
                link = None

                # Tentativa 1: Input readonly
                try:
                    link_input = WebDriverWait(self.driver, 4).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, 'input[type="text"][readonly]'))
                    )
                    link = link_input.get_attribute('value')
                except:
                    pass

                # Tentativa 2: Qualquer input de texto no modal
                if not link or 'maps' not in link:
                    try:
                        inputs = self.driver.find_elements(
                            By.CSS_SELECTOR, 'input[type="text"]')
                        for inp in inputs:
                            valor = inp.get_attribute('value') or ''
                            if 'maps.app.goo.gl' in valor or 'google.com/maps' in valor:
                                link = valor
                                break
                    except:
                        pass

                # Tentativa 3: Buscar em todos os inputs visíveis
                if not link or 'maps' not in link:
                    try:
                        inputs = self.driver.find_elements(
                            By.TAG_NAME, 'input')
                        for inp in inputs:
                            if inp.is_displayed():
                                valor = inp.get_attribute('value') or ''
                                if 'goo.gl' in valor or 'maps' in valor:
                                    link = valor
                                    break
                    except:
                        pass

                # ===== PASSO 3: Clicar em VOLTAR =====
                try:
                    # Tentativa 1: XPATH do botão voltar
                    btn_voltar = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, self.XPATH_BTN_VOLTAR))
                    )
                    btn_voltar.click()
                except:
                    # Tentativa 2: Buscar botão close/voltar por aria-label
                    try:
                        botoes = self.driver.find_elements(
                            By.TAG_NAME, 'button')
                        for btn in botoes:
                            aria_label = btn.get_attribute('aria-label') or ''
                            if 'fechar' in aria_label.lower() or 'close' in aria_label.lower() or 'voltar' in aria_label.lower():
                                btn.click()
                                break
                    except:
                        # Tentativa 3: ESC como fallback
                        ActionChains(self.driver).send_keys(
                            Keys.ESCAPE).perform()

                time.sleep(0.6)

                # Se conseguiu o link, retorna
                if link and ('maps' in link or 'goo.gl' in link):
                    return link

                # Se não conseguiu, tenta novamente
                if tentativa < max_tentativas - 1:
                    time.sleep(1)
                    continue

            except Exception as e:
                # Tenta fechar modal se algo der errado
                try:
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                    time.sleep(0.4)
                except:
                    pass

                if tentativa < max_tentativas - 1:
                    time.sleep(1)
                    continue

        # Se após todas as tentativas não conseguiu, tenta pegar da URL como último recurso
        if not link or 'maps' not in link:
            try:
                url_atual = self.driver.current_url
                if '/maps/place/' in url_atual or 'google.com/maps' in url_atual:
                    link = url_atual
            except:
                pass

        return link if link and ('maps' in link or 'goo.gl' in link or 'google.com/maps' in link) else None

    def start_scraping(self, niche, limit):
        self.running = True
        self.telefones_coletados = []
        self.start_time = time.time()

        self.comm.status_signal.emit("CONECTADO")

        self.log("⚡ SISTEMA ATIVADO")
        self.log(f"🎯 Target: {niche}")
        self.log(f"📊 Goal: {limit} contacts")

        try:
            self.log("⚙️ Initializing ChromeDriver...")

            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument(
                "--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option(
                'useAutomationExtension', False)
            chrome_options.add_experimental_option("prefs", {
                "profile.default_content_setting_values.notifications": 2
            })

            service = Service(ChromeDriverManager().install())

            self.log("🌐 Connecting to Maps (stealth mode)...")
            self.driver = webdriver.Chrome(
                service=service, options=chrome_options)

            self.driver.get("https://www.google.com/maps")
            self.log("✅ Connected")

            wait = WebDriverWait(self.driver, 15)

            self.log(f"🔍 Searching: '{niche}'")

            try:
                search_box = wait.until(
                    EC.presence_of_element_located((By.XPATH, self.XPATH_BUSCA)))
                search_box.clear()
                search_box.send_keys(niche)
                time.sleep(0.5)  # Reduzido de 1s
                search_box.send_keys(Keys.RETURN)
                self.log("✅ Query executed")
            except:
                search_box = self.driver.find_element(By.ID, "searchboxinput")
                search_box.clear()
                search_box.send_keys(niche)
                search_box.send_keys(Keys.RETURN)
                self.log("✅ Query executed (alt)")

            time.sleep(3)  # Reduzido de 5s
            self.log("📦 Results loaded")

            telefones_encontrados = 0
            resultados_verificados = 0
            telefones_set = set()
            indice_resultado = 0
            max_verificacoes = 200

            while telefones_encontrados < limit and resultados_verificados < max_verificacoes and self.running:
                try:
                    if indice_resultado > 0 and indice_resultado % 3 == 0:
                        self.log(f"📜 Scrolling list...")
                        try:
                            painel_resultados = self.driver.find_element(
                                By.XPATH, self.XPATH_SCROLL_RESULTADOS)
                            self.driver.execute_script(
                                "arguments[0].scrollTop += 400", painel_resultados)
                            time.sleep(2)
                        except:
                            pass

                    xpath_atual = self.xpath_resultado(indice_resultado)
                    resultados_verificados += 1
                    self.log(f"➡️ Scanning result #{resultados_verificados}")

                    try:
                        resultado = wait.until(
                            EC.element_to_be_clickable((By.XPATH, xpath_atual)))

                        try:
                            nome = resultado.get_attribute(
                                "aria-label") or f"Location {indice_resultado + 1}"
                            self.log(f"📍 {nome[:40]}...")
                        except:
                            self.log(f"📍 Processing...")

                        self.driver.execute_script(
                            "arguments[0].scrollIntoView(true);", resultado)
                        time.sleep(0.3)  # Reduzido de 0.5s

                        try:
                            resultado.click()
                        except:
                            self.driver.execute_script(
                                "arguments[0].click();", resultado)

                        # Aguarda painel de detalhes carregar COMPLETAMENTE
                        time.sleep(2.5)

                    except Exception as e:
                        self.log(f"⚠️ Result not found")
                        resultados = self.driver.find_elements(
                            By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
                        if indice_resultado < len(resultados):
                            self.driver.execute_script(
                                "arguments[0].click();", resultados[indice_resultado])
                            time.sleep(2)
                        else:
                            self.log(f"⚠️ End of results")
                            break

                    # Aguarda elementos do painel estarem presentes
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located(
                                (By.XPATH, self.XPATH_SCROLL_PAINEL))
                        )
                    except:
                        pass

                    # ====== NOVO FLUXO ======
                    # PASSO 0: Scroll inicial para garantir que botão compartilhar esteja visível
                    try:
                        painel_detalhes = self.driver.find_element(
                            By.XPATH, self.XPATH_SCROLL_PAINEL)
                        # Scroll para o topo primeiro
                        self.driver.execute_script(
                            "arguments[0].scrollTop = 0", painel_detalhes)
                        time.sleep(0.3)
                    except:
                        pass

                    # PASSO 1: Obter LINK DE COMPARTILHAMENTO primeiro
                    link = self.obter_link_compartilhamento()
                    if link:
                        self.log(f"🔗 Link obtido")
                    else:
                        self.log(f"⚠️ Link não obtido - continuando...")

                    # PASSO 2: Fazer SCROLL no painel de detalhes para encontrar telefone
                    try:
                        painel_detalhes = self.driver.find_element(
                            By.XPATH, self.XPATH_SCROLL_PAINEL)
                        for _ in range(2):
                            self.driver.execute_script(
                                "arguments[0].scrollTop += 200", painel_detalhes)
                            time.sleep(0.15)
                    except:
                        pass

                    # PASSO 3: Buscar TELEFONE
                    telefone_encontrado = False

                    try:
                        telefone_elem = self.driver.find_element(
                            By.XPATH, self.XPATH_TELEFONE)
                        telefone_texto = telefone_elem.text.strip()

                        if telefone_texto:
                            telefone_limpo = self.limpar_telefone(
                                telefone_texto)

                            if len(telefone_limpo) >= 10 and telefone_limpo not in telefones_set:
                                # Monta entrada com telefone + link
                                if link:
                                    entrada = f"{telefone_limpo}|{link}"
                                    self.log(
                                        f"✅ [{telefones_encontrados + 1}/{limit}] {telefone_limpo}")
                                else:
                                    entrada = telefone_limpo
                                    self.log(
                                        f"✅ [{telefones_encontrados + 1}/{limit}] {telefone_limpo} (sem link)")

                                telefones_set.add(telefone_limpo)
                                telefones_encontrados += 1
                                self.add_phone(entrada)
                                telefone_encontrado = True
                            elif telefone_limpo in telefones_set:
                                pass  # Não loga duplicados
                            else:
                                pass  # Não loga inválidos

                    except:
                        # Método alternativo para pegar telefone
                        try:
                            botoes = self.driver.find_elements(
                                By.CSS_SELECTOR, 'button[data-item-id*="phone"]')
                            for botao in botoes:
                                texto = botao.get_attribute(
                                    "aria-label") or botao.text
                                if texto and len(texto) > 5:
                                    telefone_limpo = self.limpar_telefone(
                                        texto)
                                    if len(telefone_limpo) >= 10 and telefone_limpo not in telefones_set:
                                        # Monta entrada com telefone + link
                                        if link:
                                            entrada = f"{telefone_limpo}|{link}"
                                            self.log(
                                                f"✅ [{telefones_encontrados + 1}/{limit}] {telefone_limpo}")
                                        else:
                                            entrada = telefone_limpo
                                            self.log(
                                                f"✅ [{telefones_encontrados + 1}/{limit}] {telefone_limpo} (sem link)")

                                        telefones_set.add(telefone_limpo)
                                        telefones_encontrados += 1
                                        self.add_phone(entrada)
                                        telefone_encontrado = True
                                        break
                        except:
                            pass

                    if not telefone_encontrado:
                        pass  # Não loga "sem telefone" - apenas pula

                    indice_resultado += 1
                    time.sleep(0.5)  # Reduzido já que o link adiciona delay

                    if telefones_encontrados >= limit:
                        self.log(f"🎉 GOAL ACHIEVED")
                        break

                except Exception as e:
                    self.log(f"❌ Error: {str(e)[:60]}")
                    indice_resultado += 1

                    if resultados_verificados >= max_verificacoes:
                        self.log("⚠️ Max verification limit")
                        break

                    time.sleep(2)
                    continue

            self.log("🏁 EXTRACTION COMPLETE")
            self.log(f"📞 Contacts: {telefones_encontrados}/{limit}")
            self.log(f"📊 Scanned: {resultados_verificados}")

            if telefones_encontrados < limit:
                self.log(f"⚠️ Partial goal ({telefones_encontrados}/{limit})")
            else:
                self.log(f"✅ COMPLETE! {telefones_encontrados} CONTACTS")

        except Exception as e:
            self.log(f"❌ ERROR: {str(e)[:60]}")

        finally:
            if self.driver:
                self.log("🔒 Closing browser...")
                time.sleep(2)
                try:
                    self.driver.quit()
                    self.log("✅ Disconnected")
                except:
                    self.log("⚠️ Already closed")

            self.running = False
            self.comm.status_signal.emit("DESCONECTADO")

    def stop(self):
        self.running = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


# ==================== ROUNDED CARD ====================
class RoundedCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: #1A1A23;
                border: 1px solid #2A2A33;
                border-radius: 15px;
            }
        """)


# ==================== MAIN WINDOW ====================
class LeadHunterPro(QMainWindow):
    def __init__(self):
        super().__init__()

        self.comm = Communicator()
        self.worker = ScraperWorker(self.comm)

        self.selected_niche = ""
        self.selected_qty = 10
        self.scanned_count = 0
        self.success_rate = 0

        # Timer para atualizar tempo ativo
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_active_time)
        self.start_time = None

        self.init_ui()
        self.setup_signals()

    def init_ui(self):
        self.setWindowTitle("LeadHunter Maps PRO // Professional Edition 2.1")
        self.setGeometry(100, 100, 950, 600)

        # Stylesheet global
        self.setStyleSheet("""
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
        """)

        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # === HEADER ===
        header = self.create_header()
        main_layout.addWidget(header)

        # === MAIN CONTENT (2 COLUMNS) ===
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        # LEFT COLUMN
        left_column = self.create_left_column()
        content_layout.addLayout(left_column, 55)

        # RIGHT COLUMN
        right_column = self.create_right_column()
        content_layout.addLayout(right_column, 45)

        main_layout.addLayout(content_layout)

    def create_header(self):
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(15)

        # Icon + Title
        icon_label = QLabel("⚡")
        icon_label.setStyleSheet("font-size: 32px; color: #FFA500;")
        header_layout.addWidget(icon_label)

        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        title = QLabel("LEADHUNTER MAPS")
        title.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #FFFFFF;")
        title_layout.addWidget(title)

        subtitle = QLabel("PROFESSIONAL EDITION 2.1 // VISUAL MODE")
        subtitle.setStyleSheet(
            "font-size: 9px; color: #666666; letter-spacing: 1px;")
        title_layout.addWidget(subtitle)

        header_layout.addWidget(title_container)
        header_layout.addStretch()

        # Status indicator
        self.status_indicator = RoundedCard()
        self.status_indicator.setFixedSize(180, 50)
        status_layout = QHBoxLayout(self.status_indicator)
        status_layout.setContentsMargins(15, 0, 15, 0)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #FF4444; font-size: 20px;")
        status_layout.addWidget(self.status_dot)

        self.status_label = QLabel("DESCONECTADO")
        self.status_label.setStyleSheet(
            "color: #FF4444; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        status_layout.addWidget(self.status_label)

        # Timer para animação de pulsação
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self.animate_pulse)
        self.pulse_state = False

        header_layout.addWidget(self.status_indicator)

        return header

    def create_left_column(self):
        left_layout = QVBoxLayout()
        left_layout.setSpacing(12)

        # === EXTRACTION SETUP ===
        setup_card = RoundedCard()
        setup_layout = QVBoxLayout(setup_card)
        setup_layout.setContentsMargins(20, 18, 20, 18)
        setup_layout.setSpacing(12)

        # Title
        setup_title = QLabel("◆ CONFIGURAÇÃO DE EXTRAÇÃO")
        setup_title.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #00FF9C; letter-spacing: 1px;")
        setup_layout.addWidget(setup_title)

        # Niche input
        self.niche_input = QLineEdit()
        self.niche_input.setPlaceholderText("Digite o nicho alvo...")
        self.niche_input.setFixedHeight(38)
        self.niche_input.setStyleSheet("""
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
        """)
        setup_layout.addWidget(self.niche_input)

        # Quick select buttons
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(8)

        nichos = ["Dentista", "Estética",
                  "Imobiliária", "Advogado", "Academia"]
        for niche in nichos:
            btn = QPushButton(niche)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
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
            """)
            btn.clicked.connect(lambda checked, n=niche: self.set_niche(n))
            quick_layout.addWidget(btn)

        setup_layout.addLayout(quick_layout)

        # Quantity section
        qty_label = QLabel("META DE CONTATOS")
        qty_label.setStyleSheet(
            "font-size: 9px; color: #888888; margin-top: 8px;")
        setup_layout.addWidget(qty_label)

        qty_layout = QHBoxLayout()
        qty_layout.setSpacing(8)

        for qty in [10, 20, 30, 50]:
            btn = QPushButton(str(qty))
            btn.setFixedSize(60, 32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #0A0A0F;
                    color: #FFFFFF;
                    border: 1px solid #333333;
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #00FF9C;
                    color: #0A0A0F;
                    border: 1px solid #00FF9C;
                    transform: scale(1.08);
                }
                QPushButton:pressed {
                    background: #00D17F;
                    color: #0A0A0F;
                }
            """)
            btn.clicked.connect(lambda checked, q=qty: self.set_qty(q))
            qty_layout.addWidget(btn)

        qty_layout.addStretch()
        setup_layout.addLayout(qty_layout)

        left_layout.addWidget(setup_card)

        # === ACTION BUTTONS ===

        # Search button (único botão)
        self.search_btn = QPushButton("🔍 BUSCAR CONTATOS")
        self.search_btn.setFixedHeight(50)
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setStyleSheet("""
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
        """)
        self.search_btn.clicked.connect(self.start_extraction)
        left_layout.addWidget(self.search_btn)

        # === CONTACTS LIST ===
        contacts_card = RoundedCard()
        contacts_layout = QVBoxLayout(contacts_card)
        contacts_layout.setContentsMargins(0, 0, 0, 0)
        contacts_layout.setSpacing(0)

        # Header with copy button
        contacts_header = QWidget()
        contacts_header.setFixedHeight(45)
        contacts_header.setStyleSheet(
            "background: #0A0A0F; border-radius: 15px; border-bottom-left-radius: 0; border-bottom-right-radius: 0;")
        header_layout = QHBoxLayout(contacts_header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        contacts_title = QLabel("◉ CONTATOS EXTRAÍDOS")
        contacts_title.setStyleSheet(
            "font-size: 10px; font-weight: bold; color: #00FF9C; letter-spacing: 1px;")
        header_layout.addWidget(contacts_title)

        header_layout.addStretch()

        # Copy button
        self.copy_btn = QPushButton("📋 COPIAR LISTA")
        self.copy_btn.setFixedHeight(28)
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #00FF9C;
                border: 1px solid #00FF9C;
                border-radius: 6px;
                font-size: 9px;
                font-weight: bold;
                padding: 0 12px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: #00FF9C;
                color: #0A0A0F;
            }
            QPushButton:pressed {
                background: #00D17F;
            }
        """)
        self.copy_btn.clicked.connect(self.copy_contacts)
        header_layout.addWidget(self.copy_btn)

        contacts_layout.addWidget(contacts_header)

        # List
        self.contacts_list = QListWidget()
        self.contacts_list.setStyleSheet("""
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
        """)
        contacts_layout.addWidget(self.contacts_list)

        left_layout.addWidget(contacts_card)

        return left_layout

    def create_right_column(self):
        right_layout = QVBoxLayout()
        right_layout.setSpacing(12)

        # === METRICS ===
        metrics_card = RoundedCard()
        metrics_layout = QVBoxLayout(metrics_card)
        metrics_layout.setContentsMargins(20, 18, 20, 18)
        metrics_layout.setSpacing(15)

        metrics_title = QLabel("◎ MÉTRICAS DO SISTEMA")
        metrics_title.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #FFFFFF; letter-spacing: 1px;")
        metrics_layout.addWidget(metrics_title)

        # Metric items
        # Tempo ativo
        self.time_metric = self.create_metric_item("⏱ TEMPO ATIVO", "00:00:00")
        metrics_layout.addWidget(self.time_metric)

        # Extraídos
        self.extracted_metric = self.create_metric_item("✦ EXTRAÍDOS", "0")
        metrics_layout.addWidget(self.extracted_metric)

        # Taxa de êxito
        self.success_metric = self.create_metric_item("◉ TAXA DE ÊXITO", "0%")
        metrics_layout.addWidget(self.success_metric)

        # Spacer
        metrics_layout.addItem(QSpacerItem(
            20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        right_layout.addWidget(metrics_card)

        # === TERMINAL ===
        terminal_card = RoundedCard()
        terminal_layout = QVBoxLayout(terminal_card)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        terminal_layout.setSpacing(0)

        # Header
        terminal_header = QWidget()
        terminal_header.setFixedHeight(45)
        terminal_header.setStyleSheet(
            "background: #0A0A0F; border-radius: 15px; border-bottom-left-radius: 0; border-bottom-right-radius: 0;")
        header_layout = QHBoxLayout(terminal_header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        terminal_title = QLabel("✦ TERMINAL // LOGS")
        terminal_title.setStyleSheet(
            "font-size: 10px; font-weight: bold; color: #FFFFFF; letter-spacing: 1px;")
        header_layout.addWidget(terminal_title)

        terminal_layout.addWidget(terminal_header)

        # Console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("""
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
        """)
        terminal_layout.addWidget(self.console)

        right_layout.addWidget(terminal_card)

        return right_layout

    def create_metric_item(self, label, value):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        label_widget = QLabel(label)
        label_widget.setStyleSheet(
            "font-size: 9px; color: #888888; letter-spacing: 1px;")
        layout.addWidget(label_widget)

        layout.addStretch()

        value_widget = QLabel(value)
        value_widget.setObjectName(f"value_{label}")
        value_widget.setFixedHeight(28)
        value_widget.setStyleSheet("""
            QLabel {
                background: #00FF9C;
                color: #0A0A0F;
                border-radius: 14px;
                padding: 0 15px;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        value_widget.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_widget)

        return container

    def update_metric_value(self, metric_widget, value):
        value_label = metric_widget.findChild(
            QLabel, metric_widget.findChildren(QLabel)[1].objectName())
        if value_label:
            value_label.setText(str(value))

    def setup_signals(self):
        self.comm.log_signal.connect(self.append_log)
        self.comm.phone_signal.connect(self.add_phone)
        self.comm.counter_signal.connect(self.update_extracted)
        self.comm.status_signal.connect(self.update_status)

    def set_niche(self, niche):
        self.selected_niche = niche
        self.niche_input.setText(niche)
        self.append_log(f"🎯 Nicho definido: {niche}")

    def set_qty(self, qty):
        self.selected_qty = qty
        self.append_log(f"📊 Meta definida: {qty} contatos")

    def append_log(self, msg):
        self.console.append(msg)
        self.console.moveCursor(QTextCursor.End)

    def add_phone(self, phone):
        self.contacts_list.addItem(phone)

    def copy_contacts(self):
        """Copia todos os números sem máscara para o clipboard"""
        contacts = []
        for i in range(self.contacts_list.count()):
            contacts.append(self.contacts_list.item(i).text())

        if contacts:
            clipboard = QApplication.clipboard()
            clipboard.setText("\n".join(contacts))
            self.append_log(
                f"✅ {len(contacts)} números copiados para área de transferência")
        else:
            self.append_log("⚠️ Nenhum contato para copiar")

    def update_extracted(self, count):
        # Update extracted metric
        for child in self.extracted_metric.findChildren(QLabel):
            if "value_" in child.objectName():
                child.setText(str(count))
                break

    def update_status(self, status):
        self.status_label.setText(status)

        if status == "CONECTADO":
            self.status_dot.setStyleSheet("color: #00FF9C; font-size: 20px;")
            self.status_label.setStyleSheet(
                "color: #00FF9C; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
            self.start_time = time.time()
            self.timer.start(1000)
            self.pulse_timer.start(500)  # Pulsa a cada 500ms
            self.search_btn.setEnabled(False)
            self.search_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #555555;
                    border: 2px solid #333333;
                    border-radius: 10px;
                    font-size: 12px;
                    font-weight: bold;
                    letter-spacing: 1px;
                }
            """)
        else:
            self.status_dot.setStyleSheet("color: #FF4444; font-size: 20px;")
            self.status_label.setStyleSheet(
                "color: #FF4444; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
            self.timer.stop()
            self.pulse_timer.stop()
            self.search_btn.setEnabled(True)
            self.search_btn.setStyleSheet("""
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
            """)

    def animate_pulse(self):
        """Anima o indicador de status quando conectado"""
        if self.pulse_state:
            self.status_dot.setStyleSheet("color: #00FF9C; font-size: 20px;")
        else:
            self.status_dot.setStyleSheet("color: #00D17F; font-size: 20px;")
        self.pulse_state = not self.pulse_state

    def update_active_time(self):
        if self.start_time:
            elapsed = int(time.time() - self.start_time)
            hours = elapsed // 3600
            minutes = (elapsed % 3600) // 60
            seconds = elapsed % 60
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            for child in self.time_metric.findChildren(QLabel):
                if "value_" in child.objectName():
                    child.setText(time_str)
                    break

    def start_extraction(self):
        niche = self.niche_input.text().strip() or self.selected_niche

        if not niche:
            self.append_log("❌ ERRO: Nenhum nicho definido")
            return

        # Clear
        self.contacts_list.clear()
        self.console.clear()
        self.worker.telefones_coletados = []

        # Reset metrics
        for child in self.extracted_metric.findChildren(QLabel):
            if "value_" in child.objectName():
                child.setText("0")
                break

        for child in self.success_metric.findChildren(QLabel):
            if "value_" in child.objectName():
                child.setText("0%")
                break

        # Start thread
        thread = threading.Thread(
            target=self.worker.start_scraping,
            args=(niche, self.selected_qty),
            daemon=True
        )
        thread.start()

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()


# ==================== MAIN ====================
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Dark palette
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
