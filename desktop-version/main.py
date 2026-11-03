import os
import re
import random
import html as html_lib
import logging
import shutil
import tempfile
import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import filedialog, Tk
import eel
import cloudscraper
from bs4 import BeautifulSoup
import requests
from chapters import (
    eh_freewebnovel,
    extrair_capitulo,
    formatar_conteudo_txt,
    formatar_nome_arquivo_capitulo,
    limpar_nome_arquivo,
    montar_url_capitulo,
    validar_url_fonte,
)

try:
    from ebooklib import epub
except ImportError:
    epub = None

web_dir = os.path.join(os.path.dirname(__file__), 'web')

session = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

DEFAULT_CONFIG = {"maxConcurrent": 10, "timeout": 20, "minDelay": 2, "maxDelay": 5}
MAX_CONCURRENT = DEFAULT_CONFIG["maxConcurrent"]
TIMEOUT = DEFAULT_CONFIG["timeout"]
MIN_DELAY = DEFAULT_CONFIG["minDelay"]
MAX_DELAY = DEFAULT_CONFIG["maxDelay"]

MAX_RETRIES = 4
CENTRALNOVEL_MAX_CONCURRENT = 3
CENTRALNOVEL_MIN_TIMEOUT = 60
file_lock = threading.Lock()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def descrever_falha_http(status):
    mensagens = {
        403: "A fonte recusou a requisição (HTTP 403). O site pode estar bloqueando o acesso temporariamente.",
        404: "Capítulo não encontrado (HTTP 404). Confira o endereço e o intervalo informado.",
        429: "Muitas requisições (HTTP 429). Aguarde antes de tentar novamente ou reduza os downloads simultâneos.",
        500: "Erro interno da fonte (HTTP 500). Tente novamente mais tarde.",
        502: "A fonte está temporariamente indisponível (HTTP 502). Tente novamente mais tarde.",
        503: "A fonte está temporariamente indisponível (HTTP 503). Tente novamente mais tarde.",
        504: "A fonte demorou para responder (HTTP 504). Aumente o tempo limite ou tente novamente.",
    }
    return mensagens.get(status, f"Falha HTTP {status}.")

def gerar_arquivo_epub(capitulos, caminho_saida, url_fonte):
    if epub is None:
        raise RuntimeError("A biblioteca EbookLib não está instalada. Instale com: pip install EbookLib")
    if not capitulos:
        raise ValueError("Nenhum capítulo válido foi baixado; o EPUB não foi criado.")

    capitulos = sorted(capitulos, key=lambda capitulo: capitulo.indice)
    titulo_livro = capitulos[0].obra
    idioma = "en" if eh_freewebnovel(url_fonte) else "pt"

    livro = epub.EpubBook()
    livro.set_identifier(uuid.uuid4().hex)
    livro.set_title(titulo_livro)
    livro.set_language(idioma)

    itens_capitulos = []
    for capitulo in capitulos:
        titulo_html = html_lib.escape(capitulo.titulo, quote=True)
        corpo_html = "\n".join(
            f"<p>{html_lib.escape(paragrafo, quote=True)}</p>"
            for paragrafo in capitulo.paragrafos
        )
        item = epub.EpubHtml(
            title=capitulo.titulo,
            file_name=f"chapter_{capitulo.indice:05d}.xhtml",
            lang=idioma,
        )
        item.content = f"<div><h1>{titulo_html}</h1>{corpo_html}</div>"
        livro.add_item(item)
        itens_capitulos.append(item)

    if not itens_capitulos:
        raise ValueError("Nenhum capítulo contém texto para adicionar ao EPUB.")

    livro.toc = tuple(itens_capitulos)
    livro.add_item(epub.EpubNcx())
    livro.add_item(epub.EpubNav())
    livro.spine = itens_capitulos

    pasta_saida = os.path.dirname(caminho_saida)
    descriptor, caminho_temporario = tempfile.mkstemp(
        prefix=".epub_", suffix=".tmp", dir=pasta_saida
    )
    os.close(descriptor)
    try:
        epub.write_epub(caminho_temporario, livro)
        os.replace(caminho_temporario, caminho_saida)
    finally:
        if os.path.exists(caminho_temporario):
            try:
                os.remove(caminho_temporario)
            except OSError:
                logging.exception("Não foi possível remover o EPUB temporário")

def baixar_pagina_desktop(url):
    ultima_resposta = None
    ultimo_erro = None

    for tentativa in range(MAX_RETRIES):
        try:
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            r = session.get(url, timeout=TIMEOUT)
            if r.status_code == 200:
                return r
            if r.status_code in (403, 429, 503):
                ultima_resposta = r
                espera = min((2 ** tentativa) * 10, 60)
                if tentativa < MAX_RETRIES - 1:
                    time.sleep(espera)
                continue
            return r
        except requests.exceptions.RequestException as e:
            ultimo_erro = e
            espera = min((2 ** tentativa) * 10, 60)
            if tentativa < MAX_RETRIES - 1:
                time.sleep(espera)

    if ultimo_erro:
        raise RuntimeError(
            f"Falha de conexão após {MAX_RETRIES} tentativas "
            f"({type(ultimo_erro).__name__}): {ultimo_erro}"
        ) from ultimo_erro
    if ultima_resposta:
        return ultima_resposta
    return None

def baixar_capitulo_individual(url_base, cap, caminho_destino, total, estado_progresso, formato):
    cap_str = str(cap).replace('.5', '-') if '.5' in str(cap) else str(cap).replace('.0', '')
    numero_cap = cap
    erro_capitulo = None

    try:
        url_completa = montar_url_capitulo(url_base, cap)
        r = baixar_pagina_desktop(url_completa)
        if r is None:
            raise RuntimeError("A fonte não respondeu após as tentativas de conexão.")
        if r.status_code != 200:
            status = r.status_code
            if status == 404 and eh_freewebnovel(url_completa):
                raise ValueError(
                    "Capítulo não encontrado (HTTP 404). Confira o slug real da obra e o número do capítulo."
                )
            raise RuntimeError(descrever_falha_http(status))

        soup = BeautifulSoup(r.text, "html.parser")
        capitulo = extrair_capitulo(soup, url_completa, numero_cap)
        titulo_log = capitulo.titulo
        nome_arquivo = formatar_nome_arquivo_capitulo(capitulo)
        conteudo = formatar_conteudo_txt(capitulo)

    except Exception as e:
        erro_msg = str(e)
        erro_capitulo = erro_msg
        nome_arquivo = f"ERRO_{cap_str}.txt"
        conteudo = f"Erro no capítulo {cap_str}: {erro_msg}"
        titulo_log = "ERRO"
        eel.registrarErro(numero_cap, erro_msg)()

    with file_lock:
        if formato == "epub" and erro_capitulo is None:
            estado_progresso["capitulos_epub"].append(capitulo)
        else:
            arquivo_path = os.path.join(caminho_destino, nome_arquivo)
            modo_abertura = "w" if nome_arquivo.startswith("ERRO_") else "x"
            with open(arquivo_path, modo_abertura, encoding="utf-8") as f:
                f.write(conteudo)
        estado_progresso['atual'] += 1

    eel.receberProgresso(titulo_log, estado_progresso['atual'], total, numero_cap)()

def thread_processamento(url_base, inicio, fim, caminho_final, formato):
    capitulos = [i for i in range(inicio, fim + 1)]
    total = len(capitulos)
    estado_progresso = {'atual': 0, 'total': total, 'capitulos_epub': []}
    caminho_capitulos = (
        os.path.dirname(caminho_final) if formato == "epub" else caminho_final
    )

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
        futures = {
            executor.submit(
                baixar_capitulo_individual, url_base, cap, caminho_capitulos, total, estado_progresso, formato
            ): cap
            for cap in capitulos
        }
        falhas_de_gravacao = 0
        for future in as_completed(futures):
            cap = futures[future]
            try:
                future.result()
            except Exception as e:
                falhas_de_gravacao += 1
                mensagem = f"Falha ao salvar o capítulo: {e}"
                logging.exception("Não foi possível salvar o capítulo %s", cap)
                eel.registrarErro(cap, mensagem)()
                with file_lock:
                    estado_progresso["atual"] += 1
                    atual = estado_progresso["atual"]
                eel.receberProgresso("ERRO", atual, total, cap)()

    erro_processo = ""
    if formato == "epub":
        if not estado_progresso["capitulos_epub"]:
            erro_processo = "Nenhum capítulo válido foi baixado; o EPUB não foi criado."
        else:
            eel.atualizarStatusDownload("Montando o livro EPUB...")()
            try:
                gerar_arquivo_epub(estado_progresso["capitulos_epub"], caminho_final, url_base)
            except Exception as e:
                logging.exception("Não foi possível gerar o EPUB")
                erro_processo = f"Falha ao gerar o EPUB: {e}"
                try:
                    os.remove(caminho_final)
                except FileNotFoundError:
                    pass
                except OSError:
                    logging.exception("Não foi possível remover o EPUB incompleto")

        if erro_processo and os.path.exists(caminho_final):
            try:
                os.remove(caminho_final)
            except OSError:
                logging.exception("Não foi possível remover o EPUB reservado sem conteúdo")

    eel.finalizarDownload(falhas_de_gravacao == 0 and not erro_processo, caminho_final, erro_processo)()

@eel.expose
def obter_config_padrao():
    return DEFAULT_CONFIG

@eel.expose
def selecionar_pasta():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    pasta = filedialog.askdirectory(title="Selecionar Pasta de Destino")
    root.destroy()
    return pasta

@eel.expose
def iniciar_download_desktop(url_base, inicio, fim, formato, nome_arquivo_custom, config_settings, pasta_salvar):
    global MAX_CONCURRENT, TIMEOUT, MIN_DELAY, MAX_DELAY

    try:
        validar_url_fonte(url_base)
        montar_url_capitulo(url_base, inicio)
        inicio = int(inicio)
        fim = int(fim)
        if inicio < 1 or fim < inicio:
            raise ValueError("Informe um intervalo válido: capítulo inicial positivo e final igual ou maior.")
    except (TypeError, ValueError) as e:
        return {"ok": False, "msg": str(e)}

    try:
        MAX_CONCURRENT = int(config_settings.get('maxConcurrent', DEFAULT_CONFIG['maxConcurrent']))
        TIMEOUT = int(config_settings.get('timeout', DEFAULT_CONFIG['timeout']))
        MIN_DELAY = float(config_settings.get('minDelay', DEFAULT_CONFIG['minDelay']))
        MAX_DELAY = float(config_settings.get('maxDelay', DEFAULT_CONFIG['maxDelay']))
        if not 1 <= MAX_CONCURRENT <= 50 or not 5 <= TIMEOUT <= 120:
            raise ValueError("Concorrência deve estar entre 1 e 50 e timeout entre 5 e 120 segundos.")
        if not 0 <= MIN_DELAY <= MAX_DELAY <= 10:
            raise ValueError("As esperas devem estar entre 0 e 10 segundos; a máxima não pode ser menor que a mínima.")
    except (AttributeError, TypeError, ValueError) as e:
        return {"ok": False, "msg": f"Configuração de rede inválida: {e}"}

    if not eh_freewebnovel(url_base):
        MAX_CONCURRENT = min(MAX_CONCURRENT, CENTRALNOVEL_MAX_CONCURRENT)
        TIMEOUT = max(TIMEOUT, CENTRALNOVEL_MIN_TIMEOUT)
        logging.info(
            "Central Novel: usando até %s downloads simultâneos e timeout de %s segundos",
            MAX_CONCURRENT,
            TIMEOUT,
        )

    if not pasta_salvar or not os.path.isdir(pasta_salvar):
        return {"ok": False, "msg": "Selecione uma pasta válida na interface."}

    if formato not in {"txt", "epub"}:
        return {"ok": False, "msg": "Formato de saída não suportado."}

    if formato == "epub":
        if epub is None:
            return {"ok": False, "msg": "EbookLib não está instalada. Instale com: pip install EbookLib"}

        extensao = ".epub"
        nome_limpo = re.sub(r'[\\/*?:"<>|]', '', str(nome_arquivo_custom)).strip()
        if nome_limpo.lower().endswith(extensao):
            nome_limpo = nome_limpo[:-len(extensao)].strip()
        if not nome_limpo:
            return {"ok": False, "msg": "Informe um nome válido para o arquivo EPUB."}

        caminho_salvar = os.path.join(pasta_salvar, f"{nome_limpo}{extensao}")
        try:
            with open(caminho_salvar, "x", encoding="utf-8"):
                pass
        except FileExistsError:
            return {"ok": False, "msg": "Já existe um arquivo .epub com esse nome. Escolha outro nome ou pasta."}
        except OSError as e:
            logging.exception("Não foi possível criar o arquivo EPUB")
            return {"ok": False, "msg": f"Não foi possível criar o arquivo EPUB: {e}"}
    else:
        # TXT chapters are saved directly in the selected folder.
        caminho_salvar = pasta_salvar

    thread = threading.Thread(
        target=thread_processamento,
        args=(url_base, int(inicio), int(fim), caminho_salvar, formato),
        daemon=True
    )
    try:
        thread.start()
    except RuntimeError as e:
        if formato == "epub":
            try:
                os.remove(caminho_salvar)
            except OSError:
                logging.exception("Não foi possível remover o arquivo de saída reservado")
        return {"ok": False, "msg": f"Não foi possível iniciar o processamento: {e}"}

    return {"ok": True, "caminho": caminho_salvar}

@eel.expose
def unificar_txt_arquivos(caminho_pasta, nome_saida):
    caminho_temporario = None
    arquivo_saida_criado = False
    arquivo_saida = None
    try:
        if not os.path.isdir(caminho_pasta):
            return {"ok": False, "msg": "Diretório inválido"}

        nome_limpo = re.sub(r'[\\/*?:"<>|]', '', str(nome_saida)).strip()
        if nome_limpo.lower().endswith(".txt"):
            nome_limpo = nome_limpo[:-4].strip()
        if not nome_limpo:
            return {"ok": False, "msg": "Informe um nome válido para o arquivo unificado."}

        nome_arquivo = f"{nome_limpo}.txt"
        arquivo_saida = os.path.join(caminho_pasta, nome_arquivo)
        if os.path.exists(arquivo_saida):
            return {"ok": False, "msg": "Já existe um arquivo com esse nome. Escolha outro nome."}

        todos_arquivos = os.listdir(caminho_pasta)
        arquivos_txt = [
            arq for arq in todos_arquivos
            if arq.lower().endswith(".txt") and arq.lower() != nome_arquivo.lower()
        ]
        arquivos_txt.sort()

        if not arquivos_txt:
            return {"ok": False, "msg": "Nenhum arquivo .txt encontrado para mesclar"}

        arquivos_com_erro = [arq for arq in arquivos_txt if arq.lower().startswith("erro_")]
        if arquivos_com_erro:
            return {
                "ok": False,
                "msg": (
                    f"Foram encontrados {len(arquivos_com_erro)} arquivo(s) ERRO_*.txt. "
                    "Corrija os capítulos com falha antes de unificar."
                ),
            }

        descriptor, caminho_temporario = tempfile.mkstemp(
            prefix=".unificacao_", suffix=".tmp", dir=caminho_pasta
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as saida:
            for idx, arq_txt in enumerate(arquivos_txt):
                caminho_arquivo = os.path.join(caminho_pasta, arq_txt)
                with open(caminho_arquivo, "r", encoding="utf-8") as entrada:
                    shutil.copyfileobj(entrada, saida)
                if idx < len(arquivos_txt) - 1:
                    saida.write("\n" + "=" * 80 + "\n\n")

        with open(arquivo_saida, "x", encoding="utf-8") as saida:
            arquivo_saida_criado = True
            with open(caminho_temporario, "r", encoding="utf-8") as entrada:
                shutil.copyfileobj(entrada, saida)

        arquivo_saida_criado = False
        return {"ok": True, "caminho": arquivo_saida}
    except (OSError, UnicodeError) as e:
        logging.exception("Não foi possível unificar os arquivos TXT")
        return {"ok": False, "msg": str(e)}
    finally:
        if arquivo_saida_criado and arquivo_saida and os.path.exists(arquivo_saida):
            try:
                os.remove(arquivo_saida)
            except OSError:
                logging.exception("Não foi possível remover o arquivo de unificação incompleto")
        if caminho_temporario and os.path.exists(caminho_temporario):
            try:
                os.remove(caminho_temporario)
            except OSError:
                logging.exception("Não foi possível remover o arquivo temporário de unificação")


def main():
    eel.init(web_dir)
    eel.start('index.html', size=(1000, 850))


if __name__ == "__main__":
    main()