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
import requests # Garantir a captura de erros de rede

# Inicializa o Eel apontando para a pasta 'web'
eel.init('web')

# Configuração do Scraper idêntica ao CLI de sucesso
session = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

MAX_CONCURRENT = 10
MAX_RETRIES = 4

# Lock vital para evitar que o Windows trave ao escrever no ZIP em paralelo
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
    """ Mecanismo de retry robusto herdado da CLI """
    for tentativa in range(MAX_RETRIES):
        try:
            # Mantendo o tempo de segurança da CLI que deu 100% de sucesso
            time.sleep(random.uniform(1.5, 3.5))
            r = session.get(url, timeout=20)

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

def baixar_capitulo_individual(url_base, cap, caminho_zip, total, estado_progresso):
    cap_str = str(cap).replace('.5', '-') if '.5' in str(cap) else str(cap).replace('.0', '')
    url_completa = f"{url_base}{cap_str}"
    
    try:
        r = baixar_pagina_desktop(url_completa)
        
        if not r or r.status_code != 200:
            status = r.status_code if r else "Timeout/Null"
            raise Exception(f"Falha de acesso (Status: {status})")
            
        soup = BeautifulSoup(r.text, "html.parser")
        titulo_el = soup.find("h1", class_="entry-title")
        serie_el = soup.find("div", class_="cat-series")
        
        if not titulo_el:
            raise Exception("Título não encontrado na página")
            
        titulo_capitulo = titulo_el.get_text().strip()
        # Fallback seguro caso o site oculte a tag da série em algum capítulo
        titulo_nome = limpar_nome_arquivo(serie_el.get_text()) if serie_el else "Shadow Slave"
        
        match = re.search(r"Capítulo\s+([\d\-\.]+)", titulo_capitulo, re.IGNORECASE)
        numero_original = match.group(1) if match else str(cap_str)
        
        partes = numero_original.split("-")
        num_principal = partes[0].zfill(5)
        num_final = f"{num_principal}-{partes[1]}" if len(partes) > 1 else num_principal
        
        nome_arquivo = f"Capítulo {num_final} - {titulo_nome}.txt"
        conteudo = f"{titulo_capitulo}\n{titulo_nome}\n\n{extrair_conteudo(soup)}\n"
        
    except Exception as e:
        nome_arquivo = f"ERRO_{cap_str}.txt"
        conteudo = f"Erro ao baixar o capítulo {cap_str}: {str(e)}"
        titulo_nome = "ERRO"

    # Escrita segura forçada por LOCK (Idêntico ao CLI)
    with file_lock:
        with zipfile.ZipFile(caminho_zip, "a", zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr(nome_arquivo, conteudo)
        
        # Incremento do progresso protegido dentro do Lock
        estado_progresso['atual'] += 1
    
    # Envia a atualização em tempo real para o Front-end HTML/JS
    eel.receberProgresso(nome_arquivo, titulo_nome, estado_progresso['atual'], total)()

def thread_processamento(url_base, inicio, fim, caminho_zip):
    capitulos = [i for i in range(inicio, fim + 1)]
    total = len(capitulos)
    estado_progresso = {'atual': 0}
    
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
        futures = [
            executor.submit(baixar_capitulo_individual, url_base, cap, caminho_zip, total, estado_progresso) 
            for cap in capitulos
        ]
        for future in as_completed(futures):
            pass 
            
    eel.finalizarDownload(True, caminho_zip)()

@eel.expose
def iniciar_download_desktop(url_base, inicio, fim):
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True) 
    
    caminho_salvar = filedialog.asksaveasfilename(
        title="Salvar Arquivo ZIP",
        defaultextension=".zip",
        filetypes=[("Arquivos ZIP", "*.zip")],
        initialfile=f"capitulos_{int(time.time())}.zip"
    )
    root.destroy()
    
    if not caminho_salvar:
        return {"ok": False, "msg": "Operação cancelada."}
        
    with zipfile.ZipFile(caminho_salvar, "w", zipfile.ZIP_DEFLATED) as zipf:
        pass
        
    threading.Thread(
        target=thread_processamento, 
        args=(url_base, int(inicio), int(fim), caminho_salvar), 
        daemon=True
    ).start()
    
    return {"ok": True}

# Inicia a aplicação
eel.start('index.html', size=(1000, 800))