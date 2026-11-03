import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class Capitulo:
    indice: int
    numero: str
    titulo: str
    nome_capitulo: str
    obra: str
    paragrafos: tuple[str, ...]


def limpar_nome_arquivo(nome: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", nome).replace("\n", " ").strip()


def eh_freewebnovel(url: str) -> bool:
    try:
        host = urlsplit(url).hostname or ""
    except ValueError:
        return False
    return host.lower() in {"freewebnovel.com", "www.freewebnovel.com"}


def validar_url_fonte(url: str) -> None:
    try:
        partes = urlsplit(url.strip())
        host = (partes.hostname or "").lower()
    except ValueError as erro:
        raise ValueError("O endereço informado não é uma URL válida.") from erro

    if partes.scheme not in {"http", "https"} or not host:
        raise ValueError("Informe uma URL completa começando com https://.")

    caminho = partes.path.rstrip("/")
    if host in {"freewebnovel.com", "www.freewebnovel.com"}:
        match = re.fullmatch(r"/novel/([^/]+)/chapter-[\w.-]+", caminho, re.IGNORECASE)
        if not match:
            raise ValueError(
                "Cole o link de um capítulo real do Free Web Novel, no formato "
                "https://freewebnovel.com/novel/slug-real/chapter-1."
            )
        slugs_de_exemplo = {
            "nome-da-obra", "name-of-the-novel", "novel-name",
            "your-novel", "slug-da-obra", "example",
        }
        if match.group(1).lower() in slugs_de_exemplo:
            raise ValueError(
                "O endereço ainda contém um slug de exemplo. Troque 'nome-da-obra' "
                "pelo nome real da obra na URL do Free Web Novel."
            )
        return

    if host in {"centralnovel.com", "www.centralnovel.com"}:
        if not re.search(
            r".+-(?:\d+)?$", partes.path.rstrip("/")
        ):
            raise ValueError(
                "Informe a URL do Central Novel terminada em hífen ou o link de um capítulo."
            )
        return

    raise ValueError("Fonte não suportada. Use Central Novel ou Free Web Novel.")


def montar_url_capitulo(url_base: str, capitulo: int) -> str:
    url_base = url_base.strip()
    validar_url_fonte(url_base)
    cap_str = str(capitulo).replace(".5", "-") if ".5" in str(capitulo) else str(capitulo).replace(".0", "")

    partes = urlsplit(url_base)
    caminho = partes.path.rstrip("/")
    if not eh_freewebnovel(url_base):
        tem_barra_final = partes.path.endswith("/")
        if caminho.endswith("-"):
            caminho = f"{caminho}{cap_str}"
        else:
            caminho = re.sub(r"-\d+$", f"-{cap_str}", caminho)
        if tem_barra_final:
            caminho = f"{caminho}/"
        return urlunsplit((partes.scheme, partes.netloc, caminho, partes.query, partes.fragment))

    match = re.search(r"/chapter-(?:\d+(?:\.\d+)?|-)?$", caminho, re.IGNORECASE)
    if not match:
        raise ValueError(
            "Para o Free Web Novel, informe o link de um capítulo, como "
            "https://freewebnovel.com/novel/nome-da-obra/chapter-1."
        )

    caminho = f"{caminho[:match.start()]}/chapter-{cap_str}"
    return urlunsplit((partes.scheme, partes.netloc, caminho, partes.query, partes.fragment))


def _limpar_texto_html(elemento) -> str:
    texto = re.sub(r"\s+", " ", elemento.get_text(" ", strip=True)).strip()
    return re.sub(r"\s+([,.;:!?…])", r"\1", texto)


def _extrair_paragrafos(soup: BeautifulSoup) -> tuple[str, ...]:
    root = soup.find("div", class_="epcontent entry-content")
    if not root:
        root = soup.find("div", id="article")
    if not root:
        return ()

    for extra in root.find_all(
        ["script", "style", "ins", "div"],
        class_=re.compile(r"ads|social|shared", re.I),
    ):
        extra.decompose()
    if root.get("id") == "article":
        titulo_interno = root.find(["h1", "h2", "h3", "h4"])
        if titulo_interno:
            titulo_interno.decompose()

    paragrafos = tuple(
        texto
        for elemento in root.find_all("p")
        if (texto := _limpar_texto_html(elemento))
    )
    if paragrafos:
        return paragrafos

    texto = root.get_text(separator="\n")
    return tuple(
        linha
        for linha in (re.sub(r"\s+", " ", parte).strip() for parte in texto.splitlines())
        if linha
    )


def _extrair_numero_e_subtitulo(titulo_bruto: str, numero_padrao: int) -> tuple[str, str]:
    match = re.search(
        r"\b(?:cap[ií]tulo|chapter)\s*([\d]+(?:[.-][\d]+)?)",
        titulo_bruto,
        re.IGNORECASE,
    )
    if not match:
        return str(numero_padrao), ""
    subtitulo = titulo_bruto[match.end():].strip(" \t\r\n:：–—-")
    return match.group(1), subtitulo


def _extrair_capitulo_centralnovel(
    soup: BeautifulSoup, indice: int, paragrafos: tuple[str, ...]
) -> Capitulo:
    titulo_el = soup.find("h1", class_="entry-title")
    if not titulo_el:
        raise ValueError("O título do capítulo não foi encontrado na página do Central Novel.")

    titulo_bruto = _limpar_texto_html(titulo_el)
    numero, subtitulo = _extrair_numero_e_subtitulo(titulo_bruto, indice)
    match_numero = re.search(
        r"\b(?:cap[ií]tulo|chapter)\s*[\d]+(?:[.-][\d]+)?",
        titulo_bruto,
        re.IGNORECASE,
    )
    obra = titulo_bruto[:match_numero.start()].strip(" \t\r\n:：–—-") if match_numero else ""
    titulo_el = soup.find("div", class_="cat-series")
    nome_capitulo = _limpar_texto_html(titulo_el) if titulo_el else subtitulo
    nome_capitulo = nome_capitulo or f"Capítulo {numero}"
    return Capitulo(
        indice=indice,
        numero=numero,
        titulo=f"Capítulo {numero}: {nome_capitulo}",
        nome_capitulo=nome_capitulo,
        obra=limpar_nome_arquivo(obra) or "Central Novel",
        paragrafos=paragrafos,
    )


def _extrair_capitulo_freewebnovel(
    soup: BeautifulSoup, indice: int, paragrafos: tuple[str, ...]
) -> Capitulo:
    titulo_el = soup.find("span", class_="chapter")
    if not titulo_el:
        raise ValueError("O título do capítulo não foi encontrado na página do Free Web Novel.")

    titulo_bruto = _limpar_texto_html(titulo_el)
    numero, subtitulo = _extrair_numero_e_subtitulo(titulo_bruto, indice)
    obra_el = soup.select_one("h1.tit a") or soup.find("h1", class_="tit")
    obra = _limpar_texto_html(obra_el) if obra_el else "Free Web Novel"
    nome_capitulo = subtitulo or f"Chapter {numero}"
    return Capitulo(
        indice=indice,
        numero=numero,
        titulo=f"Chapter {numero}: {subtitulo}" if subtitulo else nome_capitulo,
        nome_capitulo=limpar_nome_arquivo(subtitulo) or f"Chapter {numero}",
        obra=limpar_nome_arquivo(obra),
        paragrafos=paragrafos,
    )


def extrair_capitulo(soup: BeautifulSoup, url: str, indice: int) -> Capitulo:
    paragrafos = _extrair_paragrafos(soup)
    if not paragrafos:
        raise ValueError("O texto do capítulo não foi encontrado na página.")
    if eh_freewebnovel(url):
        return _extrair_capitulo_freewebnovel(soup, indice, paragrafos)
    return _extrair_capitulo_centralnovel(soup, indice, paragrafos)


def formatar_numero_arquivo(numero: str) -> str:
    match = re.fullmatch(r"(\d+)(.*)", numero)
    if not match:
        return limpar_nome_arquivo(numero)
    return f"{match.group(1).zfill(5)}{match.group(2)}"


def formatar_nome_arquivo_capitulo(capitulo: Capitulo) -> str:
    numero = formatar_numero_arquivo(capitulo.numero)
    titulo = limpar_nome_arquivo(capitulo.nome_capitulo)
    obra = limpar_nome_arquivo(capitulo.obra)
    trecho_titulo = f" - {titulo}" if titulo else ""
    return f"Capítulo {numero}{trecho_titulo} - {obra}.txt"


def formatar_conteudo_txt(capitulo: Capitulo) -> str:
    paragrafos = "\n\n".join(capitulo.paragrafos)
    return f"{capitulo.titulo}\n{capitulo.obra}\n\n{paragrafos}\n"
