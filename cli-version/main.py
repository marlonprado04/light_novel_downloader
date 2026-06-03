import cloudscraper
from bs4 import BeautifulSoup
import os
import re
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import zipfile
from tqdm import tqdm
import requests 
import threading

BASE_URL = "https://centralnovel.com/shadow-slave-capitulo-"

# Cria uma sessão estável simulando o Chrome
session = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

MAX_CONCURRENT = 10
MAX_RETRIES = 4
MIN_DELAY = 2
MAX_DELAY = 5
file_lock = threading.Lock()

def limpar_nome_arquivo(nome):
    return re.sub(r'[\\/*?:"<>|]', "", nome).strip()

def extrair_conteudo(soup):
    root = soup.find("div", class_="epcontent entry-content")
    if not root:
        return ""
    for extra in root.find_all(["script", "style", "ins", "div"], class_=re.compile(r"ads|social|shared", re.I)):
        extra.decompose()
    texto = root.get_text(separator="\n")
    return "\n\n".join([linha.strip() for linha in texto.split("\n") if linha.strip()])

def baixar_pagina(url):
    for tentativa in range(MAX_RETRIES):
        try:
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            r = session.get(url, timeout=20)
            if r.status_code == 200:
                return r
            if r.status_code in (403, 429, 503):
                espera = min((2 ** tentativa) * 10, 60)
                tqdm.write(f"-> Bloqueio {r.status_code} na URL: {url.split('-')[-1]}. Esperando {espera}s...")
                time.sleep(espera)
                continue
            return r
        except requests.exceptions.RequestException:
            tqdm.write("-> Falha de conexão. Tentando novamente...")
            time.sleep(10)
    return None

def fetch_capitulo(cap_id):
    url = f"{BASE_URL}{cap_id}"
    try:
        r = baixar_pagina(url)
        if not r or r.status_code != 200:
            return (f"ERRO_{cap_id}.txt", f"Erro ao acessar {url}")
        
        soup = BeautifulSoup(r.text, "html.parser")
        titulo_el = soup.find("h1", class_="entry-title")
        serie_el = soup.find("div", class_="cat-series")
        titulo = titulo_el.get_text().strip() if titulo_el else f"Capitulo {cap_id}"
        serie = limpar_nome_arquivo(serie_el.get_text()) if serie_el else "Shadow Slave"
        
        match = re.search(r"(\d+)", str(cap_id))
        num = match.group(1).zfill(5) if match else str(cap_id)
        
        nome_arquivo = limpar_nome_arquivo(f"Capitulo {num} - {serie}.txt")
        conteudo = f"{titulo}\n\n{extrair_conteudo(soup)}\n"
        return (nome_arquivo, conteudo)
    except Exception as e:
        return (f"ERRO_{cap_id}.txt", str(e))

def unificar_arquivos():
    pasta = input("Digite o caminho da pasta com os arquivos .txt: ").strip()
    if not os.path.exists(pasta):
        print("Pasta não encontrada.")
        return
    
    saida = input("Nome do arquivo final (ex: livro_completo.txt): ").strip()
    arquivos = [f for f in os.listdir(pasta) if f.endswith(".txt")]
    
    # Ordena mantendo a lógica numérica
    arquivos.sort(key=lambda f: [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', f)])
    
    with open(saida, "w", encoding="utf-8") as outfile:
        for fname in tqdm(arquivos, desc="Unificando"):
            with open(os.path.join(pasta, fname), "r", encoding="utf-8") as infile:
                outfile.write(infile.read() + "\n" + "="*40 + "\n\n")
    print(f"Sucesso! Arquivo gerado: {saida}")

def main():
    print("1 = Baixar (TXT Individual)")
    print("2 = Baixar (ZIP)")
    print("3 = Unificar pasta TXT")
    
    opcao = input("Escolha uma opção: ").strip()

    if opcao == "3":
        unificar_arquivos()
        return

    inicio = int(input("Capítulo inicial: "))
    fim = int(input("Capítulo final: "))
    
    if opcao == "1":
        pasta = input("Pasta para salvar: ").strip() or "Capitulos"
        os.makedirs(pasta, exist_ok=True)
    else:
        caminho_zip = input("Nome do arquivo ZIP: ").strip() or "novels.zip"
        if not caminho_zip.endswith(".zip"): caminho_zip += ".zip"

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
        futures = {executor.submit(fetch_capitulo, c): c for c in range(inicio, fim + 1)}
        for future in tqdm(as_completed(futures), total=(fim - inicio + 1), desc="Processando"):
            nome, conteudo = future.result()
            with file_lock:
                if opcao == "1":
                    with open(os.path.join(pasta, nome), "w", encoding="utf-8") as f:
                        f.write(conteudo)
                else:
                    with zipfile.ZipFile(caminho_zip, "a", zipfile.ZIP_DEFLATED) as zipf:
                        zipf.writestr(nome, conteudo)

    print("\nConcluído!")

if __name__ == "__main__":
    main()
