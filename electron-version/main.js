const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const axios = require("axios");
const cheerio = require("cheerio");
const archiver = require("archiver");

function limparNomeArquivo(nome) {
  return nome.replace(/\//g, "_")
    .replace(/\?/g, "")
    .replace(/\n/g, " ")
    .replace(/:/g, " -")
    .trim();
}

function createWindow() {
  const preloadPath = path.join(app.getAppPath(), 'public', 'preload.js');
  const win = new BrowserWindow({
    width: 1000,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: preloadPath
    },
  });

  // Carrega o frontend diretamente do arquivo local
  win.loadFile(path.join(app.getAppPath(), 'public', 'index.html'));
}

// Garante instância única do app
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    // Se o usuário tentar abrir outra janela, focar a existente
    const win = BrowserWindow.getAllWindows()[0];
    if (win) {
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  });

  app.whenReady().then(() => {
    let windowCriada = false;
    // Não chama mais startNodeServer
    if (!windowCriada) {
      createWindow();
      windowCriada = true;
    }
    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0 && !windowCriada) {
        createWindow();
        windowCriada = true;
      }
    });
  });
}

app.on("window-all-closed", () => {
  // Não precisa mais matar nodeProcess
  if (process.platform !== "darwin") {
    app.quit();
  }
});

// IPC: download capítulos
ipcMain.handle('baixar-capitulos', async (event, { url, inicio, fim }) => {
  let arquivos = [];
  for (let cap = inicio; cap <= fim; cap++) {
    let capInicial = String(cap).includes('.5')
      ? String(cap).replace('.5', '-')
      : String(cap).replace('.0', '');
    let urlCompleta = `${url}${capInicial}`;
    try {
      const resposta = await axios.get(urlCompleta);
      const html = resposta.data;
      const $ = cheerio.load(html);
      const tituloCapituloElement = $('h1.entry-title');
      if (!tituloCapituloElement.length) continue;
      const tituloCapitulo = tituloCapituloElement.text();
      const tituloNomeElement = $('div.cat-series');
      if (!tituloNomeElement.length) continue;
      const tituloNome = limparNomeArquivo(tituloNomeElement.text());
      const indice = tituloCapitulo.indexOf('Capítulo');
      if (indice === -1) continue;
      let capitulo = tituloCapitulo.substring(indice).replace(/\//g, "_");
      let numeroCapitulo = capitulo.replace('Capítulo', '').trim();
      capitulo = limparNomeArquivo(`Capítulo ${numeroCapitulo.padStart(5, '0')}`);
      let conteudo = `${tituloCapitulo}\n${tituloNome}\n\n`;
      const contentHtml = $('div.epcontent.entry-content');

      // 1. Caso padrão: existe <p>
      if (contentHtml.find('p').length > 0) {
        contentHtml.find('p').each((i, el) => {
          conteudo += $(el).text().trim() + '\n\n';
        });
      
      } else {
        // 2. Caso alternativo: div com <br>
        const rawHtml = contentHtml.html();
      
        if (rawHtml) {
          const texto = rawHtml
            .replace(/<br\s*\/?>/gi, '\n')   // converte <br> em quebra de linha
            .replace(/<\/?[^>]+(>|$)/g, '') // remove outras tags HTML
            .replace(/\n\s*\n/g, '\n\n')    // normaliza espaçamento
            .trim();
          conteudo += texto + '\n\n';
        }
      }
      arquivos.push([`${capitulo} - ${tituloNome}.txt`, conteudo]);
    } catch (e) {
      arquivos.push([`ERRO_${capInicial}.txt`, `Erro ao baixar capítulo ${capInicial}`]);
    }
  }
  // Salvar ZIP
  const { filePath } = await dialog.showSaveDialog({
    title: 'Salvar ZIP',
    defaultPath: `capitulos_${Date.now()}.zip`,
    filters: [{ name: 'ZIP', extensions: ['zip'] }]
  });
  if (!filePath) return { ok: false };
  return await new Promise((resolve, reject) => {
    const output = fs.createWriteStream(filePath);
    const archive = archiver('zip', { zlib: { level: 9 } });
    archive.pipe(output);
    for (const [nome, conteudo] of arquivos) {
      archive.append(conteudo, { name: nome });
    }
    archive.finalize();
    output.on('close', () => resolve({ ok: true, filePath }));
    archive.on('error', err => reject({ ok: false, err }));
  });
});

ipcMain.handle('baixar-capitulos-com-progresso', async (event, { url, inicio, fim }) => {
  const pLimit = require('p-limit').default; // Corrigido: usar .default para compatibilidade com Electron build
  const MAX_CONCURRENT = 10; // Ajuste conforme desejado
  let arquivos = [];
  let total = fim - inicio + 1;
  let baixados = 0;
  const limit = pLimit(MAX_CONCURRENT);
  let tasks = [];
  for (let cap = inicio; cap <= fim; cap++) {
    tasks.push(limit(async () => {
      let capInicial = String(cap).includes('.5')
        ? String(cap).replace('.5', '-')
        : String(cap).replace('.0', '');
      let urlCompleta = `${url}${capInicial}`;
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
        event.sender.send('progresso-capitulo', {
          capitulo,
          nome: tituloNome,
          atual: baixados,
          total
        });
      } catch (e) {
        arquivos.push([`ERRO_${capInicial}.txt`, `Erro ao baixar capítulo ${capInicial}`]);
        baixados++;
        event.sender.send('progresso-capitulo', {
          capitulo: capInicial,
          nome: 'ERRO',
          atual: baixados,
          total
        });
      }
    }));
  }
  await Promise.all(tasks);
  // Ordena os arquivos pelo número do capítulo antes de zipar
  arquivos.sort((a, b) => {
    // Extrai número do capítulo do nome do arquivo
    const getNum = (nome) => {
      const match = nome.match(/Capítulo (\d+)/);
      return match ? parseInt(match[1], 10) : 0;
    };
    return getNum(a[0]) - getNum(b[0]);
  });
  // Salvar ZIP
  const { filePath } = await dialog.showSaveDialog({
    title: 'Salvar ZIP',
    defaultPath: `capitulos_${Date.now()}.zip`,
    filters: [{ name: 'ZIP', extensions: ['zip'] }]
  });
  if (!filePath) {
    event.sender.send('baixar-capitulos-finalizado', { ok: false });
    return { ok: false };
  }
  await new Promise((resolve, reject) => {
    const output = fs.createWriteStream(filePath);
    const archive = archiver('zip', { zlib: { level: 9 } });
    archive.pipe(output);
    for (const [nome, conteudo] of arquivos) {
      archive.append(conteudo, { name: nome });
    }
    archive.finalize();
    output.on('close', resolve);
    archive.on('error', reject);
  });
  event.sender.send('baixar-capitulos-finalizado', { ok: true, filePath });
  return { ok: true, filePath };
});
