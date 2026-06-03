from flask import Flask, render_template, request, send_file
from bs4 import BeautifulSoup
import requests
import io
import zipfile

app = Flask(__name__)

def limpar_nome_arquivo(nome):
    return nome.replace("/", "_").replace("?", "").replace("\n", " ").replace(":", " -").strip()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/baixar', methods=['POST'])
def baixar():
    url_base = request.form['url']
    capitulo_inicial = float(request.form['capituloInicial'])
    capitulo_final = float(request.form['capituloFinal'])

    arquivos = []

    while capitulo_inicial <= capitulo_final:
        cap_inicial = (
            str(capitulo_inicial).replace(".5", "-")
            if ".5" in str(capitulo_inicial)
            else str(capitulo_inicial).replace(".0", "")
        )
        url_completa = f"{url_base}{cap_inicial}"
        try:
            requisicao = requests.get(url_completa)
            requisicao.raise_for_status()
            html = requisicao.text
            soup = BeautifulSoup(html, "html.parser")

            titulo_capitulo_element = soup.find("h1", {"class": "entry-title"})
            if not titulo_capitulo_element:
                capitulo_inicial += 1
                continue

            titulo_capitulo = titulo_capitulo_element.get_text()
            titulo_nome_element = soup.find("div", {"class": "cat-series"})
            if not titulo_nome_element:
                capitulo_inicial += 1
                continue

            titulo_nome = limpar_nome_arquivo(titulo_nome_element.get_text())
            indice = titulo_capitulo.find("Capítulo")

            if indice == -1:
                capitulo_inicial += 1
                continue

            capitulo = titulo_capitulo[indice:].replace("/", "_")
            numero_capitulo = capitulo.replace("Capítulo", "").strip()
            capitulo = limpar_nome_arquivo(f"Capítulo {numero_capitulo.zfill(5)}")

            conteudo = titulo_capitulo + "\n" + titulo_nome + "\n\n"
            content_html = soup.find("div", {"class": "epcontent entry-content"})
            for paragrafo in content_html.find_all("p"):
                conteudo += paragrafo.get_text() + "\n\n"

            arquivos.append((f"{capitulo} - {titulo_nome}.txt", conteudo))
        except:
            pass
        capitulo_inicial += 1

    # Sempre retorna um ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for nome, conteudo in arquivos:
            zip_file.writestr(nome, conteudo)
    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name="capitulos.zip",
        mimetype='application/zip'
    )

if __name__ == '__main__':
    app.run(debug=True)
