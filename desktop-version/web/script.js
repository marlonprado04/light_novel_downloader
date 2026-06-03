// Variáveis globais de configuração
let configSettings = {
    maxConcurrent: localStorage.getItem('maxConcurrent') || 10,
    timeout: localStorage.getItem('timeout') || 20,
    minDelay: localStorage.getItem('minDelay') || 1.5,
    maxDelay: localStorage.getItem('maxDelay') || 3.5
};

let downloadState = {
    caminhoDestino: null,
    formato: null,
    total: 0,
    progresso: {
        atual: 0,
        total: 0
    }
};

let progressLogExpanded = localStorage.getItem('progressLogExpanded') !== 'false';

// Toggle filename field visibility
function toggleFilenameField() {
    const formato = document.querySelector('input[name="formato"]:checked').value;
    const filenameField = document.getElementById('filenameField');
    if (formato === 'zip') {
        filenameField.classList.add('visible');
        filenameField.style.display = 'flex';
    } else {
        filenameField.classList.remove('visible');
        filenameField.style.display = 'none';
    }
}

// Toggle progress log visibility
function toggleProgressLog() {
    const container = document.getElementById('progressLogContainer');
    const toggle = document.getElementById('progressToggle');
    const isCollapsed = container.classList.contains('collapsed');

    if (isCollapsed) {
        container.classList.remove('collapsed');
        toggle.classList.remove('collapsed');
        progressLogExpanded = true;
    } else {
        container.classList.add('collapsed');
        toggle.classList.add('collapsed');
        progressLogExpanded = false;
    }

    localStorage.setItem('progressLogExpanded', progressLogExpanded);
}

// Toggle developer panel
function toggleDevPanel() {
    const devContent = document.getElementById('devContent');
    const devToggle = document.querySelector('.dev-toggle');
    devContent.classList.toggle('show');
    devToggle.classList.toggle('open');
}

// Salvar configurações do painel dev
function saveDevSettings() {
    configSettings.maxConcurrent = document.getElementById('maxConcurrent').value;
    configSettings.timeout = document.getElementById('timeout').value;
    configSettings.minDelay = document.getElementById('minDelay').value;
    configSettings.maxDelay = document.getElementById('maxDelay').value;

    localStorage.setItem('maxConcurrent', configSettings.maxConcurrent);
    localStorage.setItem('timeout', configSettings.timeout);
    localStorage.setItem('minDelay', configSettings.minDelay);
    localStorage.setItem('maxDelay', configSettings.maxDelay);

    // Visual feedback
    showSaveNotice();
}

function showSaveNotice() {
    let notice = document.querySelector('.settings-notice');
    if (!notice) return;

    const originalText = notice.innerHTML;
    notice.innerHTML = '✓ Configurações salvas!';
    notice.style.backgroundColor = '#c8e6c9';

    setTimeout(() => {
        notice.innerHTML = originalText;
        notice.style.backgroundColor = '#e8f5e9';
    }, 2000);
}

// Update progress title with current count
function updateProgressTitle() {
    const title = document.getElementById('progressTitle');
    if (title) {
        const atual = downloadState.progresso.atual;
        const total = downloadState.progresso.total;
        title.textContent = `📊 Progresso do Download (${atual}/${total})`;
    }
}

document.getElementById('formDownload').addEventListener('submit', async (e) => {
    e.preventDefault();

    const url = document.getElementById('url').value;
    const inicio = parseInt(document.getElementById('capituloInicial').value);
    const fim = parseInt(document.getElementById('capituloFinal').value);
    const formato = document.querySelector('input[name="formato"]:checked').value;
    const nomeArquivo = document.getElementById('nomeArquivo').value.trim();

    const linkDownload = document.getElementById('linkDownload');

    linkDownload.innerHTML = 'Aguardando seleção de pasta de destino...';

    // Salvar configurações antes de iniciar
    saveDevSettings();

    // Chama a função exposta no Python
    const resposta = await eel.iniciar_download_desktop(url, inicio, fim, formato, nomeArquivo, configSettings)();

    if (resposta.ok) {
        downloadState.caminhoDestino = resposta.caminho;
        downloadState.formato = formato;
        downloadState.total = fim - inicio + 1;
        downloadState.progresso.total = fim - inicio + 1;
        downloadState.progresso.atual = 0;

        linkDownload.innerHTML = '<strong>Download em andamento...</strong>';
        atualizarTabelaProgresso(inicio, fim);
        mostrarProgressBar();

        // Restaurar estado da tabela de progresso
        const container = document.getElementById('progressLogContainer');
        if (progressLogExpanded) {
            container.classList.remove('collapsed');
            document.getElementById('progressToggle').classList.remove('collapsed');
        } else {
            container.classList.add('collapsed');
            document.getElementById('progressToggle').classList.add('collapsed');
        }

        // Mostrar botão unificador se for TXT
        if (formato === 'txt') {
            document.getElementById('unifierContainer').style.display = 'block';
        } else {
            document.getElementById('unifierContainer').style.display = 'none';
        }
    } else {
        linkDownload.innerHTML = `<span style="color:red;">${resposta.msg || 'Erro ao iniciar.'}</span>`;
    }
});

function mostrarProgressBar() {
    document.getElementById('stats').style.display = 'block';

    // Adicionar listener ao header para toggle
    const header = document.getElementById('progressHeader');
    header.removeEventListener('click', toggleProgressLog);
    header.addEventListener('click', toggleProgressLog);
}

function atualizarTabelaProgresso(inicio, fim) {
    const listaProgresso = document.getElementById('progresso');

    let html = '<table class="progress-table"><thead><tr><th>Cap</th><th>Título</th><th>Status</th></tr></thead><tbody id="progress-body">';

    for (let i = inicio; i <= fim; i++) {
        const num = String(i).padStart(5, '0');
        html += `<tr id="row-${num}"><td>${num}</td><td id="title-${num}">-</td><td id="status-${num}" title="">⏳</td></tr>`;
    }

    html += '</tbody></table>';
    listaProgresso.innerHTML = html;
}

eel.expose(receberProgresso);
function receberProgresso(capitulo, nome, atual, total, numero_cap) {
    const num = String(numero_cap).padStart(5, '0');
    const titleCell = document.getElementById(`title-${num}`);
    const statusCell = document.getElementById(`status-${num}`);

    if (titleCell) {
        titleCell.textContent = nome;
        statusCell.textContent = '✓';
        statusCell.style.color = 'green';
        statusCell.title = 'Baixado com sucesso';
    }

    atualizarProgresso(atual, total);
}

function atualizarProgresso(atual, total) {
    downloadState.progresso.atual = atual;
    downloadState.progresso.total = total;

    const porcentagem = Math.round((atual / total) * 100);
    const progressBar = document.getElementById('progressBar');
    const statsSummary = document.getElementById('statsSummary');
    const progressPercentage = document.getElementById('progressPercentage');

    progressBar.style.width = porcentagem + '%';
    progressBar.textContent = porcentagem + '%';
    progressPercentage.textContent = porcentagem + '%';

    statsSummary.innerHTML = `<strong>${atual}/${total} capítulos (${porcentagem}%)</strong>`;

    updateProgressTitle();
}

eel.expose(finalizarDownload);
function finalizarDownload(sucesso, caminhoFinal) {
    const linkDownload = document.getElementById('linkDownload');
    if (sucesso) {
        linkDownload.innerHTML = `<span style="color:green; font-weight:bold;">✓ Sucesso! Salvo em:<br><small>${caminhoFinal}</small></span>`;
    } else {
        linkDownload.innerHTML = '<span style="color:red; font-weight:bold;">✗ Erro durante o empacotamento.</span>';
    }
}

eel.expose(registrarErro);
function registrarErro(numero_cap, mensagem) {
    const num = String(numero_cap).padStart(5, '0');
    const statusCell = document.getElementById(`status-${num}`);

    if (statusCell) {
        statusCell.textContent = '✗';
        statusCell.style.color = 'red';
        statusCell.title = 'Erro: ' + mensagem;
    }
}

// Função para unificar arquivos TXT
document.addEventListener('DOMContentLoaded', function() {
    const unifierBtn = document.getElementById('unifierBtn');
    if (unifierBtn) {
        unifierBtn.addEventListener('click', unificarArquivos);
    }
});

async function unificarArquivos() {
    if (!downloadState.caminhoDestino || downloadState.formato !== 'txt') {
        alert('Selecione uma pasta com arquivos TXT primeiro');
        return;
    }

    const nomeUnificado = prompt('Nome do arquivo unificado:', 'capitulos_unificados');
    if (!nomeUnificado) return;

    const unifierBtn = document.getElementById('unifierBtn');
    const unifierStatus = document.getElementById('unifierStatus');

    unifierBtn.disabled = true;
    unifierStatus.innerHTML = '⏳ Unificando arquivos...';

    try {
        const resposta = await eel.unificar_txt_arquivos(downloadState.caminhoDestino, nomeUnificado)();
        if (resposta.ok) {
            unifierStatus.className = 'unifier-success';
            unifierStatus.innerHTML = `✓ Sucesso! Arquivo unificado:<br><small>${resposta.caminho}</small>`;
        } else {
            unifierStatus.className = 'unifier-error';
            unifierStatus.innerHTML = `✗ Erro: ${resposta.msg}`;
        }
    } catch (error) {
        unifierStatus.className = 'unifier-error';
        unifierStatus.innerHTML = `✗ Erro: ${error}`;
    } finally {
        unifierBtn.disabled = false;
    }
}

// Carregar configurações ao iniciar
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('maxConcurrent').value = configSettings.maxConcurrent;
    document.getElementById('timeout').value = configSettings.timeout;
    document.getElementById('minDelay').value = configSettings.minDelay;
    document.getElementById('maxDelay').value = configSettings.maxDelay;
    toggleFilenameField();
});
