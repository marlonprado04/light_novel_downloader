import os
import re
import random
import time
import zipfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import filedialog, Tk
import eel
import cloudscraper
from bs4 import BeautifulSoup
import requests

web_dir = os.path.join(os.path.dirname(__file__), 'web')
eel.init(web_dir)

session = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

# Variáveis globais configuráveis
MAX_CONCURRENT = 10
MAX_RETRIES = 4
TIMEOUT = 20
MIN_DELAY = 1.5
MAX_DELAY = 3.5

file_lock = threading.Lock()

def limpar_nome_arquivo(nome):
    return re.sub(r'[\\/*?:"<>|]', "", nome).replace('\n', ' ').strip()

def extrair_conteudo(soup):
    root = soup.find("div", class_="epcontent entry-content")
    if not root:
        return ""

    for extra in root.find_all(["script", "style", "ins", "div"], class_=re.compile(r"ads|social|shared", re.I)):
        extra.decompose()

    texto = root.get_text(separator="\n")
    linhas = [linha.strip() for linha in texto.split("\n") if linha.strip()]
    return "\n\n".join(linhas)

def baixar_pagina_desktop(url):
    for tentativa in range(MAX_RETRIES):
        try:
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            r = session.get(url, timeout=TIMEOUT)

            if r.status_code == 200:
                return r

            if r.status_code in (403, 429, 503):
                espera = min((2 ** tentativa) * 10, 60)
                print(f"\n[Aviso App] Bloqueio {r.status_code}. Esfriando por {espera}s...")
                time.sleep(espera)
                continue

            return r

        except requests.exceptions.RequestException:
            espera = min((2 ** tentativa) * 10, 60)
            print(f"\n[Aviso App] Falha de conexão. Tentando em {espera}s...")
            time.sleep(espera)

    return None

def baixar_capitulo_individual(url_base, cap, caminho_zip, total, estado_progresso, formato):
    cap_str = str(cap).replace('.5', '-') if '.5' in str(cap) else str(cap).replace('.0', '')
    url_completa = f"{url_base}{cap_str}"
    numero_cap = cap

    try:
        r = baixar_pagina_desktop(url_completa)

        if not r or r.status_code != 200:
            status = r.status_code if r else "Timeout/Null"
            raise Exception(f"Falha de acesso (HTTP {status})")

        soup = BeautifulSoup(r.text, "html.parser")
        titulo_el = soup.find("h1", class_="entry-title")
        serie_el = soup.find("div", class_="cat-series")

        if not titulo_el:
            raise Exception("Título não encontrado")

        titulo_capitulo = titulo_el.get_text().strip()
        titulo_nome = limpar_nome_arquivo(serie_el.get_text()) if serie_el else "Shadow Slave"

        match = re.search(r"Capítulo\s+([\d\-\.]+)", titulo_capitulo, re.IGNORECASE)
        numero_original = match.group(1) if match else str(cap_str)

        partes = numero_original.split("-")
        num_principal = partes[0].zfill(5)
        num_final = f"{num_principal}-{partes[1]}" if len(partes) > 1 else num_principal

        nome_arquivo = f"Capítulo {num_final} - {titulo_nome}.txt"
        conteudo = f"{titulo_capitulo}\n{titulo_nome}\n\n{extrair_conteudo(soup)}\n"

    except Exception as e:
        erro_msg = str(e)
        nome_arquivo = f"ERRO_{cap_str}.txt"
        conteudo = f"Erro ao baixar o capítulo {cap_str}: {erro_msg}"
        titulo_nome = "ERRO"
        eel.registrarErro(numero_cap, erro_msg)()

    with file_lock:
        if formato == "zip":
            with zipfile.ZipFile(caminho_zip, "a", zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr(nome_arquivo, conteudo)
        else:
            arquivo_path = os.path.join(caminho_zip, nome_arquivo)
            with open(arquivo_path, "w", encoding="utf-8") as f:
                f.write(conteudo)

        estado_progresso['atual'] += 1

    eel.receberProgresso(nome_arquivo, titulo_nome, estado_progresso['atual'], total, numero_cap)()

def thread_processamento(url_base, inicio, fim, caminho_zip, formato):
    capitulos = [i for i in range(inicio, fim + 1)]
    total = len(capitulos)
    estado_progresso = {'atual': 0, 'total': total}

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
        futures = [
            executor.submit(baixar_capitulo_individual, url_base, cap, caminho_zip, total, estado_progresso, formato)
            for cap in capitulos
        ]
        for future in as_completed(futures):
            pass

    eel.finalizarDownload(True, caminho_zip)()

@eel.expose
def iniciar_download_desktop(url_base, inicio, fim, formato, nome_arquivo_custom, config_settings):
    global MAX_CONCURRENT, TIMEOUT, MIN_DELAY, MAX_DELAY

    # Aplicar configurações do frontend
    MAX_CONCURRENT = int(config_settings.get('maxConcurrent', 10))
    TIMEOUT = int(config_settings.get('timeout', 20))
    MIN_DELAY = float(config_settings.get('minDelay', 1.5))
    MAX_DELAY = float(config_settings.get('maxDelay', 3.5))

    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    if formato == "zip":
        # Validar e limpar nome customizado
        if nome_arquivo_custom:
            nome_arquivo_custom = re.sub(r'[\\/*?:"<>|]', '', nome_arquivo_custom)
            nome_arquivo = f"{nome_arquivo_custom}.zip"
        else:
            nome_arquivo = f"capitulos_{int(time.time())}.zip"

        caminho_salvar = filedialog.asksaveasfilename(
            title="Salvar Arquivo ZIP",
            defaultextension=".zip",
            filetypes=[("Arquivos ZIP", "*.zip")],
            initialfile=nome_arquivo
        )

        if not caminho_salvar:
            root.destroy()
            return {"ok": False, "msg": "Operação cancelada."}

        with zipfile.ZipFile(caminho_salvar, "w", zipfile.ZIP_DEFLATED) as zipf:
            pass
    else:  # formato == "txt"
        pasta_salvar = filedialog.askdirectory(title="Selecionar Pasta para Salvar Capítulos")

        if not pasta_salvar:
            root.destroy()
            return {"ok": False, "msg": "Operação cancelada."}

        timestamp = int(time.time())
        caminho_salvar = os.path.join(pasta_salvar, f"capitulos_{timestamp}")
        os.makedirs(caminho_salvar, exist_ok=True)

    root.destroy()

    threading.Thread(
        target=thread_processamento,
        args=(url_base, int(inicio), int(fim), caminho_salvar, formato),
        daemon=True
    ).start()

    return {"ok": True, "caminho": caminho_salvar}

@eel.expose
def unificar_txt_arquivos(caminho_pasta, nome_saida):
    try:
        if not os.path.isdir(caminho_pasta):
            return {"ok": False, "msg": "Pasta inválida"}

        # Listar e ordenar arquivos TXT
        todos_arquivos = os.listdir(caminho_pasta)
        arquivos_txt = [arquivo for arquivo in todos_arquivos if arquivo.endswith(".txt")]
        arquivos_txt.sort()

        if not arquivos_txt:
            return {"ok": False, "msg": "Nenhum arquivo .txt encontrado na pasta"}

        # Criar arquivo unificado
        nome_arquivo = f"{nome_saida}.txt"
        arquivo_saida = os.path.join(caminho_pasta, nome_arquivo)

        with open(arquivo_saida, "w", encoding="utf-8") as saida:
            for idx, arquivo_txt in enumerate(arquivos_txt):
                caminho_arquivo = os.path.join(caminho_pasta, arquivo_txt)
                try:
                    with open(caminho_arquivo, "r", encoding="utf-8", errors="ignore") as arquivo:
                        conteudo = arquivo.read()
                        saida.write(conteudo)
                    if idx < len(arquivos_txt) - 1:
                        saida.write("\n" + "="*80 + "\n\n")
                except Exception as e:
                    print(f"Erro ao ler {arquivo_txt}: {e}")

        return {"ok": True, "caminho": arquivo_saida}

    except Exception as e:
        return {"ok": False, "msg": str(e)}

# Inicia a aplicação
eel.start('index.html', size=(1000, 800))
