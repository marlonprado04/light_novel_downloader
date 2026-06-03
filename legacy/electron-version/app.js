const express = require('express');
const axios = require('axios');
const cheerio = require('cheerio');
const archiver = require('archiver');
const path = require('path');
const http = require('http');
const { Server } = require('socket.io');
const pLimit = require('p-limit').default;

const app = express();
const server = http.createServer(app);
const io = new Server(server);

app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public'))); // Serve arquivos estáticos

function limparNomeArquivo(nome) {
    return nome.replace(/\//g, "_")
        .replace(/\?/g, "")
        .replace(/\n/g, " ")
        .replace(/:/g, " -")
        .trim();
}

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

const MAX_CONCURRENT = 5; // Limite de downloads simultâneos

io.on('connection', (socket) => {
    socket.on('iniciar_download', async (data) => {
        let urlBase = data.url;
        let capituloInicial = parseFloat(data.inicio);
        let capituloFinal = parseFloat(data.fim);
        let arquivos = [];
        let total = capituloFinal - capituloInicial + 1;
        let baixados = 0;
        const limit = pLimit(MAX_CONCURRENT);
        let tasks = [];

        for (let cap = capituloInicial; cap <= capituloFinal; cap++) {
            tasks.push(limit(async () => {
                let capInicial = String(cap).includes('.5')
                    ? String(cap).replace('.5', '-')
                    : String(cap).replace('.0', '');
                let urlCompleta = `${urlBase}${capInicial}`;
                try {
                    const resposta = await axios.get(urlCompleta);
                    const html = resposta.data;
                    const $ = cheerio.load(html);

                    const tituloCapituloElement = $('h1.entry-title');
                    if (!tituloCapituloElement.length) return;
                    const tituloCapitulo = tituloCapituloElement.text();
                    const tituloNomeElement = $('div.cat-series');
                    if (!tituloNomeElement.length) return;
                    const tituloNome = limparNomeArquivo(tituloNomeElement.text());
                    const indice = tituloCapitulo.indexOf('Capítulo');
                    if (indice === -1) return;
                    let capitulo = tituloCapitulo.substring(indice).replace(/\//g, "_");
                    let numeroCapitulo = capitulo.replace('Capítulo', '').trim();
                    capitulo = limparNomeArquivo(`Capítulo ${numeroCapitulo.padStart(5, '0')}`);
                    let conteudo = `${tituloCapitulo}\n${tituloNome}\n\n`;
                    const contentHtml = $('div.epcontent.entry-content');
                    contentHtml.find('p').each((i, el) => {
                        conteudo += $(el).text() + '\n\n';
                    });
                    arquivos.push([`${capitulo} - ${tituloNome}.txt`, conteudo]);
                    baixados++;
                    socket.emit('progresso', {
                        capitulo: capitulo,
                        nome: tituloNome,
                        atual: baixados,
                        total: total
                    });
                } catch (e) {
                    socket.emit('erro', {
                        capitulo: capInicial
                    });
                }
            }));
        }

        await Promise.all(tasks);

        // Sempre retorna um ZIP
        const archive = archiver('zip', { zlib: { level: 9 } });
        let chunks = [];
        archive.on('data', chunk => chunks.push(chunk));
        archive.on('end', () => {
            const buffer = Buffer.concat(chunks);
            const url = `/downloads/arquivos_${Date.now()}.zip`;
            const fs = require('fs');
            const downloadsDir = path.join(__dirname, 'public', 'downloads');
            if (!fs.existsSync(downloadsDir)) fs.mkdirSync(downloadsDir);
            fs.writeFileSync(path.join(downloadsDir, path.basename(url)), buffer);
            socket.emit('download_finalizado', { url });
        });
        for (const [nome, conteudo] of arquivos) {
            archive.append(conteudo, { name: nome });
        }
        archive.finalize();
    });
});

const PORT = 5000;
server.listen(PORT, () => {
    console.log(`Servidor rodando em http://localhost:${PORT}`);
});