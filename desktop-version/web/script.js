let configSettings = { maxConcurrent: 10, timeout: 20, minDelay: 2, maxDelay: 5 };
let downloadState = { caminhoDestino: null, formato: null, total: 0, progresso: { atual: 0, total: 0 } };
let modoAtual = 'txt';
let processando = false;
let errosCapitulos = new Map();
let progressLogExpanded = localStorage.getItem('progressLogExpanded') !== 'false';

const rotulosBotao = {
    txt: 'Baixar arquivos TXT',
    epub: 'Baixar livro EPUB',
    unificar: 'Unificar arquivos TXT'
};

function mostrarMensagem(elemento, tipo, titulo, detalhe = '') {
    elemento.replaceChildren();
    elemento.className = 'status-panel';
    if (!titulo) return;

    const mensagem = document.createElement('div');
    mensagem.className = `status-message status-${tipo}`;
    const cabecalho = document.createElement('strong');
    cabecalho.textContent = titulo;
    mensagem.append(cabecalho);

    if (detalhe) {
        const descricao = document.createElement('small');
        descricao.textContent = detalhe;
        mensagem.append(descricao);
    }

    elemento.append(mensagem);
}

function atualizarFonte() {
    const campoUrl = document.getElementById('url');
    const indicador = document.getElementById('sourceStatus');
    const valor = campoUrl.value.trim();

    indicador.removeAttribute('data-source');
    if (!valor) {
        indicador.textContent = 'A fonte será identificada quando você informar o link.';
        return;
    }

    let url;
    try {
        url = new URL(valor);
    } catch {
        indicador.dataset.source = 'unsupported';
        indicador.textContent = 'Informe uma URL completa começando com https://.';
        return;
    }

    const host = url.hostname.toLowerCase();
    if (!['http:', 'https:'].includes(url.protocol)) {
        indicador.dataset.source = 'unsupported';
        indicador.textContent = 'Use um endereço HTTP ou HTTPS válido.';
        return;
    }

    if (host === 'freewebnovel.com' || host === 'www.freewebnovel.com') {
        const partes = url.pathname.match(/^\/novel\/([^/]+)\/chapter-[^/]+\/?$/i);
        const slugsDeExemplo = new Set([
            'nome-da-obra', 'name-of-the-novel', 'novel-name',
            'your-novel', 'slug-da-obra', 'example'
        ]);
        if (!partes) {
            indicador.dataset.source = 'unsupported';
            indicador.textContent = 'Free Web Novel reconhecido, mas use o link de um capítulo: /novel/slug-real/chapter-1.';
        } else if (slugsDeExemplo.has(partes[1].toLowerCase())) {
            indicador.dataset.source = 'unsupported';
            indicador.textContent = "Este endereço usa 'nome-da-obra' como exemplo. Substitua pelo slug real da novel.";
        } else {
            indicador.dataset.source = 'supported';
            indicador.textContent = 'Free Web Novel reconhecido. O capítulo da URL serve como referência para o intervalo.';
        }
        return;
    }

    if (host === 'centralnovel.com' || host === 'www.centralnovel.com') {
        if (url.pathname.endsWith('-')) {
            indicador.dataset.source = 'supported';
            indicador.textContent = 'Central Novel reconhecido. O app limita a 3 downloads simultâneos e usa timeout mínimo de 60 segundos.';
        } else {
            indicador.dataset.source = 'unsupported';
            indicador.textContent = 'Central Novel reconhecido, mas a URL base deve terminar em hífen.';
        }
        return;
    }

    indicador.dataset.source = 'unsupported';
    indicador.textContent = 'Fonte não reconhecida. Por enquanto, use Central Novel ou Free Web Novel.';
}

function alterarModo(modoSelecionado) {
    modoAtual = modoSelecionado;
    const sectionDownloads = document.getElementById('sectionParametrosDownload');
    const sectionNomeArquivo = document.getElementById('sectionNomeArquivo');
    const nomeArquivoInput = document.getElementById('nomeArquivo');
    const labelNomeArquivo = document.getElementById('labelNomeArquivo');
    const filenameHelp = document.getElementById('filenameHelp');
    const btnPrincipal = document.getElementById('btnPrincipal');
    const destinationHelp = document.getElementById('destinationHelp');
    const camposDownload = document.querySelectorAll('#url, #capituloInicial, #capituloFinal');

    document.querySelectorAll('.tab-button').forEach((botao) => {
        const ativo = botao.dataset.value === modoSelecionado;
        botao.classList.toggle('active', ativo);
        botao.setAttribute('aria-pressed', String(ativo));
    });

    const precisaNome = modoSelecionado !== 'txt';
    sectionDownloads.hidden = modoSelecionado === 'unificar';
    sectionNomeArquivo.hidden = !precisaNome;
    nomeArquivoInput.required = precisaNome;
    camposDownload.forEach((campo) => {
        campo.required = modoSelecionado !== 'unificar';
        campo.disabled = modoSelecionado === 'unificar';
    });

    if (modoSelecionado === 'epub') {
        labelNomeArquivo.textContent = 'Nome do livro EPUB';
        nomeArquivoInput.placeholder = 'Ex.: captured_by_the_cold_detective';
        filenameHelp.textContent = 'Será criado um único livro EPUB com sumário e um capítulo por seção.';
        destinationHelp.textContent = 'O livro EPUB será gravado nesta pasta.';
    } else if (modoSelecionado === 'unificar') {
        labelNomeArquivo.textContent = 'Nome do arquivo TXT unificado';
        nomeArquivoInput.placeholder = 'Ex.: minha_novel_completa';
        filenameHelp.textContent = 'Os arquivos TXT da pasta serão combinados nesta ordem por nome.';
        destinationHelp.textContent = 'Selecione a pasta que contém os arquivos TXT que deseja mesclar.';
    } else {
        destinationHelp.textContent = 'Os arquivos TXT serão gravados nesta pasta.';
    }

    document.documentElement.style.setProperty(
        '--input-focus',
        modoSelecionado === 'epub' ? '#7040b8' :
                modoSelecionado === 'unificar' ? 'var(--color-unify)' : 'var(--color-txt)'
    );
    if (!processando) btnPrincipal.textContent = rotulosBotao[modoSelecionado];
}

function atualizarEstadoProcesso(ativo) {
    processando = ativo;
    document.getElementById('btnPrincipal').disabled = ativo;
    document.getElementById('btnSelecionarPasta').disabled = ativo;
    document.querySelectorAll('.tab-button').forEach((botao) => {
        botao.disabled = ativo;
    });
    document.querySelectorAll('#url, #capituloInicial, #capituloFinal, #nomeArquivo').forEach((campo) => {
        campo.disabled = ativo || (modoAtual === 'unificar' && campo.id !== 'nomeArquivo');
    });
    document.getElementById('btnPrincipal').textContent = ativo ? 'Processando…' : rotulosBotao[modoAtual];
}

function exibirPainelProgresso() {
    document.getElementById('stats').style.display = 'block';
    const container = document.getElementById('progressLogContainer');
    const toggle = document.getElementById('progressToggle');
    const botao = document.getElementById('progressToggleButton');

    container.classList.toggle('collapsed', !progressLogExpanded);
    toggle.classList.toggle('collapsed', !progressLogExpanded);
    botao.setAttribute('aria-expanded', String(progressLogExpanded));
}

function construirGradeProgresso(inicio, fim) {
    const corpo = document.createElement('tbody');
    for (let i = inicio; i <= fim; i++) {
        const numero = String(i).padStart(5, '0');
        const linha = document.createElement('tr');
        linha.id = `row-${numero}`;

        const capitulo = document.createElement('td');
        capitulo.textContent = `Cap. ${numero}`;
        const titulo = document.createElement('td');
        titulo.id = `title-${numero}`;
        titulo.textContent = 'Aguardando…';
        const status = document.createElement('td');
        status.id = `status-${numero}`;
        status.className = 'chapter-status';
        status.textContent = 'Na fila';

        linha.append(capitulo, titulo, status);
        corpo.append(linha);
    }

    const tabela = document.createElement('table');
    tabela.className = 'log-table';
    const cabecalho = document.createElement('thead');
    cabecalho.innerHTML = '<tr><th scope="col">Capítulo</th><th scope="col">Título do capítulo</th><th scope="col">Status</th></tr>';
    tabela.append(cabecalho, corpo);
    const boxProgresso = document.getElementById('progresso');
    boxProgresso.replaceChildren(tabela);
}

document.getElementById('formDownload').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    if (processando) return;

    const pastaBase = document.getElementById('caminhoDestino').value;
    const statusPainel = document.getElementById('unifierStatus');
    const linkDownload = document.getElementById('linkDownload');
    const nomeArquivo = document.getElementById('nomeArquivo').value.trim();
    const formato = modoAtual;

    mostrarMensagem(statusPainel, '', '');
    mostrarMensagem(linkDownload, '', '');

    if (!pastaBase) {
        mostrarMensagem(statusPainel, 'error', 'Selecione uma pasta de destino.', 'Use o botão “Selecionar pasta” para escolher um diretório.');
        document.getElementById('btnSelecionarPasta').focus();
        return;
    }

    if (formato === 'unificar') {
        if (!nomeArquivo) {
            mostrarMensagem(statusPainel, 'error', 'Informe o nome do arquivo final.');
            document.getElementById('nomeArquivo').focus();
            return;
        }
        atualizarEstadoProcesso(true);
        mostrarMensagem(statusPainel, 'info', 'Unificando arquivos…', 'Aguarde enquanto os TXT da pasta são combinados.');
        try {
            const resposta = await eel.unificar_txt_arquivos(pastaBase, nomeArquivo)();
            if (resposta.ok) {
                mostrarMensagem(statusPainel, 'success', 'Arquivos unificados.', resposta.caminho);
            } else {
                mostrarMensagem(statusPainel, 'error', 'Não foi possível unificar os arquivos.', resposta.msg);
            }
        } catch (erro) {
            mostrarMensagem(statusPainel, 'error', 'Erro ao unificar os arquivos.', String(erro));
        } finally {
            atualizarEstadoProcesso(false);
        }
        return;
    }

    const formulario = document.getElementById('formDownload');
    const campoUrl = document.getElementById('url');
    const campoInicio = document.getElementById('capituloInicial');
    const campoFim = document.getElementById('capituloFinal');
    const url = campoUrl.value.trim();
    const inicio = Number(campoInicio.value);
    const fim = Number(campoFim.value);

    atualizarFonte();
    if (document.getElementById('sourceStatus').dataset.source !== 'supported') {
        mostrarMensagem(statusPainel, 'error', 'Confira o link da fonte.', document.getElementById('sourceStatus').textContent);
        campoUrl.focus();
        return;
    }

    if (Number.isInteger(inicio) && Number.isInteger(fim) && inicio > fim) {
        mostrarMensagem(statusPainel, 'error', 'Intervalo de capítulos inválido.', 'O capítulo inicial deve ser menor ou igual ao capítulo final.');
        campoInicio.focus();
        return;
    }

    if (!formulario.reportValidity()) return;

    downloadState.caminhoDestino = pastaBase;
    downloadState.formato = formato;
    downloadState.total = fim - inicio + 1;
    downloadState.progresso.total = downloadState.total;
    downloadState.progresso.atual = 0;
    errosCapitulos = new Map();

    document.querySelector('.progress-track').setAttribute('aria-valuenow', '0');
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('progressPercentage').textContent = '0%';
    document.getElementById('statsSummary').textContent = `Preparando ${downloadState.total} capítulo(s)…`;
    document.getElementById('progressTitle').textContent = `Preparando capítulos ${inicio}–${fim}`;
    construirGradeProgresso(inicio, fim);
    progressLogExpanded = true;
    exibirPainelProgresso();

    atualizarEstadoProcesso(true);
    mostrarMensagem(linkDownload, 'info', 'Iniciando download…', 'A conexão pode levar alguns instantes; o progresso aparecerá abaixo.');

    try {
        saveDevSettings();
        const resposta = await eel.iniciar_download_desktop(
            url, inicio, fim, formato, nomeArquivo, configSettings, pastaBase
        )();

        if (!resposta.ok) {
            atualizarEstadoProcesso(false);
            document.getElementById('stats').style.display = 'none';
            mostrarMensagem(linkDownload, 'error', 'Não foi possível iniciar o download.', resposta.msg || 'Verifique os dados e tente novamente.');
        } else if (processando) {
            mostrarMensagem(linkDownload, 'info', 'Download em andamento.', `Destino: ${resposta.caminho}`);
        }
    } catch (erro) {
        atualizarEstadoProcesso(false);
        document.getElementById('stats').style.display = 'none';
        mostrarMensagem(linkDownload, 'error', 'Falha ao iniciar o download.', String(erro));
    }
});

function atualizarResumoProgresso(atual, total) {
    downloadState.progresso.atual = atual;
    downloadState.progresso.total = total;
    const porcentagem = total > 0 ? Math.round((atual / total) * 100) : 0;
    const falhas = errosCapitulos.size;
    const sucessos = Math.max(0, atual - falhas);

    document.querySelector('.progress-track').setAttribute('aria-valuenow', String(porcentagem));
    document.getElementById('progressBar').style.width = `${porcentagem}%`;
    document.getElementById('progressPercentage').textContent = `${porcentagem}%`;
    document.getElementById('statsSummary').textContent =
        `${atual} de ${total} capítulo(s) processados · ${sucessos} concluído(s) · ${falhas} com falha`;
    if (atual < total) {
        document.getElementById('progressTitle').textContent = `Baixando capítulos (${atual}/${total})`;
    }
}

eel.expose(receberProgresso);
function receberProgresso(tituloCapitulo, atual, total, numero_cap) {
    const numero = String(numero_cap).padStart(5, '0');
    const cellTitulo = document.getElementById(`title-${numero}`);
    const cellStatus = document.getElementById(`status-${numero}`);
    const erro = errosCapitulos.get(String(numero_cap));

    if (cellTitulo && cellStatus) {
        if (erro) {
            cellTitulo.textContent = `Falha: ${erro}`;
            cellTitulo.style.color = 'var(--color-danger)';
            cellStatus.textContent = 'Falha';
            cellStatus.style.color = 'var(--color-danger)';
        } else {
            cellTitulo.textContent = tituloCapitulo;
            cellTitulo.style.color = 'var(--text-main)';
            cellStatus.textContent = 'Concluído';
            cellStatus.style.color = 'var(--color-unify)';
        }
    }
    atualizarResumoProgresso(atual, total);
}

eel.expose(finalizarDownload);
function finalizarDownload(sucesso, caminhoFinal, erroProcesso = '') {
    atualizarEstadoProcesso(false);
    const total = downloadState.progresso.total;
    const atual = downloadState.progresso.atual;
    const falhas = errosCapitulos.size;

    if (erroProcesso) {
        document.getElementById('progressTitle').textContent = 'Processo não concluído';
        mostrarMensagem(
            document.getElementById('linkDownload'),
            'error',
            'Não foi possível concluir o arquivo.',
            `${erroProcesso} Destino: ${caminhoFinal}`
        );
        return;
    }

    if (sucesso && atual === total && falhas === 0) {
        document.getElementById('progressTitle').textContent = 'Download concluído';
        mostrarMensagem(document.getElementById('linkDownload'), 'success', 'Download concluído.', `Destino: ${caminhoFinal}`);
        return;
    }

    document.getElementById('progressTitle').textContent = 'Download finalizado com problemas';
    const detalhe = falhas > 0
        ? `${falhas} capítulo(s) com falha. Confira os detalhes na lista. Destino: ${caminhoFinal}`
        : `${atual} de ${total} capítulo(s) processados. Confira os arquivos e tente novamente. Destino: ${caminhoFinal}`;
    mostrarMensagem(document.getElementById('linkDownload'), 'warning', 'O download não foi concluído por completo.', detalhe);
}

eel.expose(atualizarStatusDownload);
function atualizarStatusDownload(mensagem) {
    document.getElementById('progressTitle').textContent = mensagem;
    mostrarMensagem(document.getElementById('linkDownload'), 'info', mensagem);
}

eel.expose(registrarErro);
function registrarErro(numero_cap, mensagem) {
    const numero = String(numero_cap).padStart(5, '0');
    errosCapitulos.set(String(numero_cap), mensagem);
    const cellStatus = document.getElementById(`status-${numero}`);
    const cellTitulo = document.getElementById(`title-${numero}`);
    if (cellStatus && cellTitulo) {
        cellStatus.textContent = 'Falha';
        cellStatus.style.color = 'var(--color-danger)';
        cellTitulo.textContent = `Falha: ${mensagem}`;
        cellTitulo.style.color = 'var(--color-danger)';
    }
}

function toggleProgressLog() {
    progressLogExpanded = !progressLogExpanded;
    const container = document.getElementById('progressLogContainer');
    const toggle = document.getElementById('progressToggle');
    container.classList.toggle('collapsed', !progressLogExpanded);
    toggle.classList.toggle('collapsed', !progressLogExpanded);
    document.getElementById('progressToggleButton').setAttribute('aria-expanded', String(progressLogExpanded));
    localStorage.setItem('progressLogExpanded', String(progressLogExpanded));
}

function lerConfiguracao(chave, valorPadrao, minimo, maximo, inteiro = false) {
    const valorSalvo = Number(localStorage.getItem(chave));
    let valor = Number.isFinite(valorSalvo) && localStorage.getItem(chave) !== null ? valorSalvo : valorPadrao;
    valor = Math.min(maximo, Math.max(minimo, valor));
    return inteiro ? Math.round(valor) : valor;
}

function saveDevSettings() {
    const minDelayInput = document.getElementById('minDelay');
    const maxDelayInput = document.getElementById('maxDelay');
    const minDelay = Math.min(10, Math.max(0, Number(minDelayInput.value) || 0));
    const maxDelay = Math.min(10, Math.max(minDelay, Number(maxDelayInput.value) || 0));
    maxDelayInput.value = String(maxDelay);

    configSettings = {
        maxConcurrent: Math.round(Math.min(50, Math.max(1, Number(document.getElementById('maxConcurrent').value) || 10))),
        timeout: Math.round(Math.min(120, Math.max(5, Number(document.getElementById('timeout').value) || 20))),
        minDelay,
        maxDelay
    };

    Object.entries(configSettings).forEach(([chave, valor]) => {
        localStorage.setItem(chave, String(valor));
        document.getElementById(chave).value = String(valor);
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    document.querySelectorAll('.tab-button').forEach((botao) => {
        botao.addEventListener('click', () => alterarModo(botao.dataset.value));
    });
    document.getElementById('url').addEventListener('input', atualizarFonte);
    document.getElementById('progressToggleButton').addEventListener('click', toggleProgressLog);
    document.getElementById('maxConcurrent').addEventListener('change', saveDevSettings);
    document.getElementById('timeout').addEventListener('change', saveDevSettings);
    document.getElementById('minDelay').addEventListener('change', saveDevSettings);
    document.getElementById('maxDelay').addEventListener('change', saveDevSettings);
    alterarModo('txt');

    try {
        const defaults = await eel.obter_config_padrao()();
        configSettings = {
            maxConcurrent: lerConfiguracao('maxConcurrent', defaults.maxConcurrent, 1, 50, true),
            timeout: lerConfiguracao('timeout', defaults.timeout, 5, 120, true),
            minDelay: lerConfiguracao('minDelay', defaults.minDelay, 0, 10),
            maxDelay: lerConfiguracao('maxDelay', defaults.maxDelay, 0, 10)
        };
        if (configSettings.minDelay > configSettings.maxDelay) {
            configSettings.maxDelay = configSettings.minDelay;
        }
        Object.entries(configSettings).forEach(([chave, valor]) => {
            document.getElementById(chave).value = String(valor);
        });
        saveDevSettings();
    } catch (erro) {
        mostrarMensagem(document.getElementById('linkDownload'), 'error', 'Não foi possível carregar as configurações.', String(erro));
        document.getElementById('btnPrincipal').disabled = true;
        return;
    }

    document.getElementById('btnSelecionarPasta').addEventListener('click', async () => {
        try {
            const pasta = await eel.selecionar_pasta()();
            if (pasta) {
                document.getElementById('caminhoDestino').value = pasta;
                document.getElementById('caminhoDestino').title = pasta;
                downloadState.caminhoDestino = pasta;
            }
        } catch (erro) {
            mostrarMensagem(document.getElementById('unifierStatus'), 'error', 'Não foi possível selecionar a pasta.', String(erro));
        }
    });
});
