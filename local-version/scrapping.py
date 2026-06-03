import requests
from bs4 import BeautifulSoup
import os
import re
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import zipfile
from tqdm import tqdm

BASE_URL = "https://centralnovel.com/shadow-slave-capitulo-"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0.0.0 Safari/537.36"
    )
}

MAX_CONCURRENT = 2
MAX_RETRIES = 5

session = requests.Session()
session.headers.update(HEADERS)


def limpar_nome_arquivo(nome):
    return re.sub(r'[\\/*?:"<>|]', "", nome).strip()


def extrair_conteudo(soup):
    root = soup.find("div", class_="epcontent entry-content")

    if not root:
        return ""

    for extra in root.find_all(
        ["script", "style", "ins", "div"],
        class_=re.compile(r"ads|social|shared", re.I),
    ):
        extra.decompose()

    texto = root.get_text(separator="\n")

    linhas = [
        linha.strip()
        for linha in texto.split("\n")
        if linha.strip()
    ]

    return "\n\n".join(linhas)


def baixar_pagina(url):
    for tentativa in range(MAX_RETRIES):

        try:
            time.sleep(random.uniform(2, 5))

            r = session.get(url, timeout=30)

            if r.status_code == 200:
                return r

            if r.status_code in (429, 503):
                espera = (2 ** tentativa) * 15

                print(
                    f"\nLimite atingido ({r.status_code}). "
                    f"Aguardando {espera}s..."
                )

                time.sleep(espera)
                continue

            return r

        except requests.exceptions.RequestException:

            espera = (2 ** tentativa) * 10

            print(
                f"\nFalha de conexão. "
                f"Tentando novamente em {espera}s..."
            )

            time.sleep(espera)

    return None


def fetch_capitulo(cap_id):

    url = f"{BASE_URL}{cap_id}"

    try:

        r = baixar_pagina(url)

        if not r:
            return (
                f"ERRO_{cap_id}.txt",
                f"Não foi possível acessar {url}"
            )

        if r.status_code != 200:
            return (
                f"ERRO_{cap_id}.txt",
                f"Erro HTTP {r.status_code} na URL: {url}"
            )

        soup = BeautifulSoup(r.text, "html.parser")

        titulo_el = soup.find("h1", class_="entry-title")
        serie_el = soup.find("div", class_="cat-series")

        if not titulo_el:
            return (
                f"ERRO_{cap_id}.txt",
                "Título não encontrado"
            )

        titulo = titulo_el.get_text().strip()

        serie = (
            limpar_nome_arquivo(serie_el.get_text())
            if serie_el
            else "Shadow Slave"
        )

        match = re.search(
            r"Capítulo\s+([\d\-\.]+)",
            titulo,
            re.IGNORECASE
        )

        numero_original = (
            match.group(1)
            if match
            else str(cap_id)
        )

        partes = numero_original.split("-")

        num_principal = partes[0].zfill(5)

        num_final = (
            f"{num_principal}-{partes[1]}"
            if len(partes) > 1
            else num_principal
        )

        nome_arquivo = limpar_nome_arquivo(
            f"Capitulo {num_final} - {serie}.txt"
        )

        conteudo_limpo = extrair_conteudo(soup)

        full_text = (
            f"{titulo}\n"
            f"{serie}\n\n"
            f"{conteudo_limpo}\n"
        )

        return (nome_arquivo, full_text)

    except Exception as e:

        return (
            f"ERRO_{cap_id}.txt",
            f"Erro inesperado: {str(e)}"
        )


def gerar_lista_capitulos(inicio, fim):
    return [str(cap) for cap in range(inicio, fim + 1)]


def main():

    try:
        inicio = int(input("Capítulo inicial: "))
        fim = int(input("Capítulo final: "))

    except ValueError:
        print("Por favor, insira números válidos.")
        return

    modo = input(
        "Salvar como (1 = TXT, 2 = ZIP): "
    ).strip()

    caps_para_baixar = gerar_lista_capitulos(
        inicio,
        fim
    )

    total = len(caps_para_baixar)

    resultados = []

    with ThreadPoolExecutor(
        max_workers=MAX_CONCURRENT
    ) as executor:

        futures = {
            executor.submit(fetch_capitulo, c): c
            for c in caps_para_baixar
        }

        with tqdm(
            total=total,
            desc="Baixando",
            unit="cap"
        ) as pbar:

            for future in as_completed(futures):

                res = future.result()

                if res:
                    resultados.append(res)

                pbar.update(1)

    resultados.sort(key=lambda x: x[0])

    if not resultados:
        print("Nenhum conteúdo foi baixado.")
        return

    if modo == "1":

        pasta = (
            input("Nome da pasta: ").strip()
            or "Capitulos_Download"
        )

        os.makedirs(
            pasta,
            exist_ok=True
        )

        for nome, conteudo in resultados:

            with open(
                os.path.join(pasta, nome),
                "w",
                encoding="utf-8"
            ) as f:

                f.write(conteudo)

        print(
            f"\nArquivos salvos em:\n"
            f"{os.path.abspath(pasta)}"
        )

    else:

        caminho_zip = (
            input("Nome do ZIP: ").strip()
            or "novels.zip"
        )

        if not caminho_zip.endswith(".zip"):
            caminho_zip += ".zip"

        with zipfile.ZipFile(
            caminho_zip,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zipf:

            for nome, conteudo in resultados:
                zipf.writestr(nome, conteudo)

        print(
            f"\nZIP gerado em:\n"
            f"{os.path.abspath(caminho_zip)}"
        )


if __name__ == "__main__":
    main()
