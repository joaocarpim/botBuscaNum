import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Imports internos
from src.config import *


class ScraperWorker:
    def __init__(self, communicator):
        self.comm = communicator
        self.driver = None
        self.telefones_coletados = []
        self.running = False
        self.start_time = None

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
        return re.sub(r'[^\d]', '', tel).strip()

    def obter_link_compartilhamento(self):
        """Fluxo completo para obter link de compartilhamento."""
        link = None
        max_tentativas = 3

        for tentativa in range(max_tentativas):
            try:
                # ===== PASSO 1: Clicar no botão COMPARTILHAR =====
                try:
                    btn_compartilhar = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, XPATH_BTN_COMPARTILHAR))
                    )
                    btn_compartilhar.click()
                except:
                    # Tentativas de fallback (CSS, JS)
                    try:
                        btn = self.driver.find_element(
                            By.CSS_SELECTOR, 'button[data-item-id="share"]')
                        btn.click()
                    except:
                        try:
                            self.driver.execute_script(
                                "document.querySelector('button[aria-label*=\"ompartilhar\"]').click();")
                        except:
                            if tentativa < max_tentativas - 1:
                                time.sleep(1)
                                continue
                            else:
                                return None

                time.sleep(1.2)

                # ===== PASSO 2: Pegar o LINK =====
                try:
                    inputs = self.driver.find_elements(By.TAG_NAME, 'input')
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
                    btn_voltar = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, XPATH_BTN_VOLTAR))
                    )
                    btn_voltar.click()
                except:
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()

                time.sleep(0.6)

                if link and ('maps' in link or 'goo.gl' in link):
                    return link

            except Exception:
                try:
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                except:
                    pass
                time.sleep(1)

        # Fallback final: URL atual
        if not link:
            try:
                curr = self.driver.current_url
                if '/maps/place/' in curr:
                    link = curr
            except:
                pass

        return link

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
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"])

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(
                service=service, options=chrome_options)

            self.log("🌐 Connecting to Maps...")
            self.driver.get(URL_MAPS)
            self.log("✅ Connected")

            wait = WebDriverWait(self.driver, 15)
            self.log(f"🔍 Searching: '{niche}'")

            try:
                search_box = wait.until(
                    EC.presence_of_element_located((By.XPATH, XPATH_BUSCA)))
                search_box.clear()
                search_box.send_keys(niche)
                time.sleep(0.5)
                search_box.send_keys(Keys.RETURN)
            except:
                self.log("❌ Erro no campo de busca")
                return

            time.sleep(3)
            self.log("📦 Results loaded")

            telefones_encontrados = 0
            resultados_verificados = 0
            telefones_set = set()
            indice_resultado = 0
            max_verificacoes = 200

            while telefones_encontrados < limit and resultados_verificados < max_verificacoes and self.running:
                try:
                    # Scroll no painel lateral
                    if indice_resultado > 0 and indice_resultado % 3 == 0:
                        try:
                            painel = self.driver.find_element(
                                By.XPATH, XPATH_SCROLL_RESULTADOS)
                            self.driver.execute_script(
                                "arguments[0].scrollTop += 400", painel)
                            time.sleep(2)
                        except:
                            pass

                    xpath_atual = self.xpath_resultado(indice_resultado)
                    resultados_verificados += 1
                    self.log(f"➡️ Scanning #{resultados_verificados}")

                    try:
                        resultado = wait.until(
                            EC.element_to_be_clickable((By.XPATH, xpath_atual)))
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView(true);", resultado)
                        time.sleep(0.3)

                        try:
                            resultado.click()
                        except:
                            self.driver.execute_script(
                                "arguments[0].click();", resultado)

                        time.sleep(2.5)  # Espera carregar detalhes

                    except:
                        self.log(f"⚠️ Fim da lista ou erro de clique")
                        break

                    # Novo Fluxo: Pega link, depois scroll, depois telefone

                    # 1. Link
                    link = self.obter_link_compartilhamento()

                    # 2. Scroll Detalhes
                    try:
                        painel_detalhes = self.driver.find_element(
                            By.XPATH, XPATH_SCROLL_PAINEL)
                        self.driver.execute_script(
                            "arguments[0].scrollTop += 200", painel_detalhes)
                    except:
                        pass

                    # 3. Telefone
                    telefone_encontrado = False
                    try:
                        tel_elem = self.driver.find_element(
                            By.XPATH, XPATH_TELEFONE)
                        tel_txt = tel_elem.text.strip()
                        if tel_txt:
                            tel_limpo = self.limpar_telefone(tel_txt)
                            if len(tel_limpo) >= 10 and tel_limpo not in telefones_set:
                                entrada = f"{tel_limpo}|{link}" if link else tel_limpo
                                self.log(
                                    f"✅ [{telefones_encontrados+1}/{limit}] {tel_limpo}")
                                telefones_set.add(tel_limpo)
                                self.add_phone(entrada)
                                telefones_encontrados += 1
                                telefone_encontrado = True
                    except:
                        pass

                    indice_resultado += 1
                    time.sleep(0.5)

                except Exception as e:
                    self.log(f"❌ Erro loop: {str(e)[:50]}")
                    break

            self.log("🏁 EXTRACTION COMPLETE")
            self.log(f"📞 Total: {telefones_encontrados}/{limit}")

        except Exception as e:
            self.log(f"❌ CRITICAL ERROR: {str(e)}")
        finally:
            if self.driver:
                self.log("🔒 Closing browser...")
                try:
                    self.driver.quit()
                except:
                    pass
            self.running = False
            self.comm.status_signal.emit("DESCONECTADO")

    def stop(self):
        self.running = False
        if self.driver:
            try:
                self.driver.quit()
            except: pass