import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

# ==================== AMBIENTE ====================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ==================== XPATHS ====================
XPATH_BUSCA = '/html/body/div[1]/div[2]/div[9]/div[3]/div[1]/div[1]/div/div[1]/form/input'
XPATH_SCROLL_PAINEL = '/html/body/div[1]/div[2]/div[9]/div[8]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]'
XPATH_SCROLL_RESULTADOS = '/html/body/div[1]/div[2]/div[9]/div[8]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[1]'
XPATH_TELEFONE = '/html/body/div[1]/div[2]/div[9]/div[8]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[7]/div[5]/button/div/div[2]/div[1]'

# Compartilhamento
XPATH_BTN_COMPARTILHAR = '/html/body/div[1]/div[2]/div[9]/div[8]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[4]/div[5]/button/span'
XPATH_BTN_COPIAR_LINK = '/html/body/div[1]/div[2]/div[1]/div/div[2]/div/div[2]/div/div/div/div[3]/div[2]/div[2]/button'
XPATH_BTN_VOLTAR = '/html/body/div[1]/div[2]/div[1]/div/div[2]/div/button/span'

# URLs
URL_MAPS = "https://www.google.com/maps"
