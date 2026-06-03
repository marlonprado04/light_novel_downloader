import os
from ebooklib import epub

# Solicita o caminho da pasta e o nome do arquivo EPUB
pasta = input("Digite o caminho da pasta: ").strip()
nome_arquivo = input("Digite o nome do arquivo EPUB (sem extensão): ")

# Converte o caminho para absoluto e verifica se é válido
caminho_absoluto = os.path.abspath(pasta)
if not os.path.isdir(caminho_absoluto):
    print("Caminho inválido.")
else:
    # Lista e filtra os arquivos .txt na pasta
    todos_arquivos = os.listdir(caminho_absoluto)
    arquivos_txt = sorted([arquivo for arquivo in todos_arquivos if arquivo.endswith(".txt")])

    if not arquivos_txt:
        print("Não foram encontrados arquivos .txt na pasta.")
    else:
        # Cria um novo livro EPUB
        livro = epub.EpubBook()
        livro.set_title(nome_arquivo)
        livro.set_language("pt")

        # Adiciona metadados 
        livro.add_author("Autor Desconhecido")

        # Lista de capítulos para adicionar ao índice
        capitulos = []
        itens_navegacao = []  # Lista para manter os links do índice

        # Adiciona um capítulo de índice ao início do livro
        indice_conteudo = "<h1>Índice</h1><ul>"
        for i, arquivo_txt in enumerate(arquivos_txt):
            capitulo_nome = f"Capítulo {i + 1:03}"  # Exibe o número do capítulo com três dígitos
            indice_conteudo += f'<li><a href="capitulo_{i + 1}.xhtml">{capitulo_nome}</a></li>'
        indice_conteudo += "</ul>"

        capitulo_indice = epub.EpubHtml(title="Índice", file_name="indice.xhtml", content=indice_conteudo)
        livro.add_item(capitulo_indice)
        capitulos.append(capitulo_indice)
        itens_navegacao.append(epub.Link('indice.xhtml', 'Índice', 'indice'))

        # Processa cada arquivo .txt como um capítulo
        for i, arquivo_txt in enumerate(arquivos_txt):
            with open(os.path.join(caminho_absoluto, arquivo_txt), "r", encoding="utf-8") as arquivo:
                conteudo = arquivo.read()
                conteudo_html = f"<h1>Capítulo {i + 1:03}</h1><p>{conteudo.replace('\n', '<br>')}</p>"
                
                capitulo = epub.EpubHtml(title=f"Capítulo {i + 1:03}", file_name=f"capitulo_{i + 1}.xhtml", content=conteudo_html)
                capitulo.id = f"capitulo_{i + 1}"  # Define o ID único para o capítulo
                livro.add_item(capitulo)
                capitulos.append(capitulo)
                itens_navegacao.append(capitulo)  # Adiciona o capítulo à navegação

        # Define a estrutura de navegação do índice
        livro.toc = tuple(itens_navegacao)

        # Define os itens obrigatórios do EPUB (CSS padrão e navegação)
        livro.add_item(epub.EpubNcx())
        livro.add_item(epub.EpubNav())

        # Adiciona um CSS simples (opcional)
        style = 'h1 { text-align: center; } p { margin: 1em 0; }'
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
        livro.add_item(nav_css)

        # Define o EPUB com o CSS
        livro.spine = ['nav', capitulo_indice] + capitulos

        # Grava o EPUB
        epub.write_epub(f"{nome_arquivo}.epub", livro)
        print(f"Arquivo EPUB '{nome_arquivo}.epub' criado com sucesso.")
