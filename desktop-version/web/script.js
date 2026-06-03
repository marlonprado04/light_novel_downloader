let configSettings = { maxConcurrent: null, timeout: null, minDelay: null, maxDelay: null };
let downloadState = { caminhoDestino: null, formato: null, total: 0, progresso: { atual: 0, total: 0 } };
let progressLogExpanded = localStorage.getItem('progressLogExpanded') !== 'false';

// Função mestre que reestrutura a UI nativamente dependendo da ação escolhida
function alterarModo(modoSelecionado) {
    // 1. Atualiza as abas visuais
    document.querySelectorAll('.tab-button').forEach(btn => {
        if(btn.getAttribute('data-value') === modoSelecionado) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // 2. Sincroniza o input radio oculto
    if (modoSelecionado === 'txt') document.getElementById('radioTxt').checked = true;
    if (modoSelecionado === 'zip') document.getElementById('radioZip').checked = true;
    if (modoSelecionado === 'unificar') document.getElementById('radioUnificar').checked = true;

    // 3. Gerencia referências de elementos DOM
    const sectionDownloads = document.getElementById('sectionParametrosDownload');
    const sectionNomeArquivo = document.getElementById('sectionNomeArquivo');
    const labelNomeArquivo = document.getElementById('labelNomeArquivo');
    const nomeArquivoInput = document.getElementById('nomeArquivo');
    const btnPrincipal = document.getElementById('btnPrincipal');
    const statusPainel = document.getElementById('unifierStatus');
    const rootStyles = document.documentElement;

    statusPainel.innerHTML = ''; // Limpa mensagens residuais
    document.getElementById('stats').style.display = 'none'; // Esconde painel de progresso antigo

    // 4. Adaptação Dinâmica de Estrutura, Cores e Labels
    if (modoSelecionado === 'txt') {
        sectionDownloads.style.display = 'flex';
        sectionNomeArquivo.style.display = 'none';
        nomeArquivoInput.required = false;

        btnPrincipal.textContent = 'Baixar Capítulos Individuais';
        rootStyles.style.setProperty('--input-focus', 'var(--color-txt)');
        btnPrincipal.style.backgroundColor = 'var(--color-txt)';
    } 
    else if (modoSelecionado === 'zip') {
        sectionDownloads.style.display = 'flex';
        sectionNomeArquivo.style.display = 'block';
        labelNomeArquivo.textContent = 'Nome do Arquivo ZIP';
        nomeArquivoInput.placeholder = 'Ex: shadow_slave_volume_1';
        nomeArquivoInput.required = true;

        btnPrincipal.textContent = 'Baixar e Compactar em ZIP';
        rootStyles.style.setProperty('--input-focus', 'var(--color-zip)');
        btnPrincipal.style.backgroundColor = 'var(--color-zip)';
    } 
    else if (modoSelecionado === 'unificar') {
        sectionDownloads.style.display = 'none';
        sectionNomeArquivo.style.display = 'block';
        labelNomeArquivo.textContent = 'Nome do Arquivo Unificado (.txt)';
        nomeArquivoInput.placeholder = 'Ex: volume_1_completo';
        nomeArquivoInput.required = true;

        btnPrincipal.textContent = 'Unificar Arquivos da Pasta';
        rootStyles.style.setProperty('--input-focus', 'var(--color-unify)');
        btnPrincipal.style.backgroundColor = 'var(--color-unify)';
    }
}

// Interceptador unificado e desacoplado do submit
document.getElementById('formDownload').addEventListener('submit', async (e) => {
    e.preventDefault();

    const pastaBase = document.getElementById('caminhoDestino').value;
    if (!pastaBase) {
        alert('Por favor, selecione uma pasta de destino antes de iniciar.');
        return;
    }

    const formato = document.querySelector('input[name="formato"]:checked').value;
    const nomeArquivo = document.getElementById('nomeArquivo').value.trim();
    const statusPainel = document.getElementById('unifierStatus');
    const linkDownload = document.getElementById('linkDownload');

    // FLUXO ISOLADO 3: UNIFICAR PASTA LOCAL (Corrigido aqui)
    if (formato === 'unificar') {
        statusPainel.className = 'status-panel';
        statusPainel.innerHTML = '<div class="text-center">⏳ Processando mesclagem dos arquivos locais...</div>';
        
        try {
            // CORREÇÃO: Removido o () extra que causava o TypeError
            const resposta = await eel.unificar_txt_arquivos(pastaBase, nomeArquivo)(); 
            if (resposta.ok) {
                statusPainel.className = 'status-panel unifier-success';
                statusPainel.innerHTML = `<strong>✓ Fusão realizada!</strong><br><small>${resposta.caminho}</small>`;
            } else {
                statusPainel.className = 'status-panel unifier-error';
                statusPainel.innerHTML = `<strong>✗ Falha:</strong> ${resposta.msg}`;
            }
        } catch (error) {
            statusPainel.className = 'status-panel unifier-error';
            statusPainel.innerHTML = `<strong>✗ Erro de Processo:</strong> ${error}`;
        }
        return;
    }

    // FLUXOS ISOLADOS 1 E 2: DOWNLOADS (TXT INDIVIDUAL / ZIP PACOTE)
    const url = document.getElementById('url').value;
    const inicio = parseInt(document.getElementById('capituloInicial').value);
    const fim = parseInt(document.getElementById('capituloFinal').value);

    linkDownload.innerHTML = '<strong>Aguardando inicialização do Python...</strong>';
    saveDevSettings();

    const resposta = await eel.iniciar_download_desktop(url, inicio, fim, formato, nomeArquivo, configSettings, pastaBase)();

    if (resposta.ok) {
        downloadState.caminhoDestino = resposta.caminho;
        downloadState.formato = formato;
        downloadState.total = fim - inicio + 1;
        downloadState.progresso.total = fim - inicio + 1;
        downloadState.progresso.atual = 0;

        linkDownload.innerHTML = '<strong>Download ativo em segundo plano...</strong>';
        construirGradeProgresso(inicio, fim);
        exibirPainelProgresso();
    } else {
        linkDownload.innerHTML = `<span style="color:#991b1b; font-weight:600;">✗ Erro: ${resposta.msg || 'Falha na rotina externa.'}</span>`;
    }
});

function exibirPainelProgresso() {
    document.getElementById('stats').style.display = 'block';
    const container = document.getElementById('progressLogContainer');
    const toggle = document.getElementById('progressToggle');
    
    if (progressLogExpanded) {
        container.classList.remove('collapsed');
        toggle.classList.remove('collapsed');
    } else {
        container.classList.add('collapsed');
        toggle.classList.add('collapsed');
    }
}

function construirGradeProgresso(inicio, fim) {
    const boxProgresso = document.getElementById('progresso');
    let html = '<table class="log-table"><thead><tr><th>Capítulo</th><th>Nome na Fonte</th><th style="text-align:right;">Status</th></tr></thead><tbody>';
    
    for (let i = inicio; i <= fim; i++) {
        const num = String(i).padStart(5, '0');
        html += `<tr id="row-${num}"><td>Cap. ${num}</td><td id="title-${num}" style="color:var(--text-muted); font-style:italic;">Aguardando...</td><td id="status-${num}" style="text-align:right;">⏳</td></tr>`;
    }
    html += '</tbody></table>';
    boxProgresso.innerHTML = html;
}

eel.expose(receberProgresso);
function receberProgresso(capitulo, nome, atual, total, numero_cap) {
    const num = String(numero_cap).padStart(5, '0');
    const cellTitulo = document.getElementById(`title-${num}`);
    const cellStatus = document.getElementById(`status-${num}`);
    
    if (cellTitulo) {
        cellTitulo.textContent = nome;
        cellTitulo.style.color = 'var(--text-main)';
        cellTitulo.style.fontStyle = 'normal';
        cellStatus.textContent = '✓';
        cellStatus.style.color = 'var(--color-unify)';
    }
    atualizarBarraProgresso(atual, total);
}

function atualizarBarraProgresso(atual, total) {
    downloadState.progresso.atual = atual;
    downloadState.progresso.total = total;
    const porcentagem = Math.round((atual / total) * 100);
    
    document.getElementById('progressBar').style.width = porcentagem + '%';
    document.getElementById('progressPercentage').textContent = porcentagem + '%';
    document.getElementById('statsSummary').innerHTML = `Processados: <strong>${atual} de ${total}</strong> arquivos (${porcentagem}%)`;
    document.getElementById('progressTitle').textContent = `Baixando Capítulos (${atual}/${total})`;
}

eel.expose(finalizarDownload);
function finalizarDownload(sucesso, caminhoFinal) {
    const linkDownload = document.getElementById('linkDownload');
    linkDownload.innerHTML = sucesso 
        ? `<div class="unifier-success" style="text-align:left;"><strong>✓ Processo concluído com sucesso!</strong><br><small>Destino: ${caminhoFinal}</small></div>`
        : '<div class="unifier-error"><strong>✗ Erro crítico durante o fechamento do lote.</strong></div>';
}

eel.expose(registrarErro);
function registrarErro(numero_cap, mensagem) {
    const num = String(numero_cap).padStart(5, '0');
    const cellStatus = document.getElementById(`status-${num}`);
    const cellTitulo = document.getElementById(`title-${num}`);
    if (cellStatus) {
        cellStatus.textContent = '✗';
        cellStatus.style.color = 'var(--color-zip)';
        if (cellTitulo) {
            cellTitulo.textContent = `Falha: ${mensagem}`;
            cellTitulo.style.color = '#b91c1c';
        }
    }
}

function toggleProgressLog() {
    const container = document.getElementById('progressLogContainer');
    const toggle = document.getElementById('progressToggle');
    if (container.classList.contains('collapsed')) {
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

function saveDevSettings() {
    configSettings.maxConcurrent = document.getElementById('maxConcurrent').value;
    configSettings.timeout = document.getElementById('timeout').value;
    configSettings.minDelay = document.getElementById('minDelay').value;
    configSettings.maxDelay = document.getElementById('maxDelay').value;
    localStorage.setItem('maxConcurrent', configSettings.maxConcurrent);
    localStorage.setItem('timeout', configSettings.timeout);
    localStorage.setItem('minDelay', configSettings.minDelay);
    localStorage.setItem('maxDelay', configSettings.maxDelay);
}

document.addEventListener('DOMContentLoaded', async function() {
    const defaults = await eel.obter_config_padrao()();
    configSettings = {
        maxConcurrent: localStorage.getItem('maxConcurrent') ?? defaults.maxConcurrent,
        timeout: localStorage.getItem('timeout') ?? defaults.timeout,
        minDelay: localStorage.getItem('minDelay') ?? defaults.minDelay,
        maxDelay: localStorage.getItem('maxDelay') ?? defaults.maxDelay
    };
    document.getElementById('maxConcurrent').value = configSettings.maxConcurrent;
    document.getElementById('timeout').value = configSettings.timeout;
    document.getElementById('minDelay').value = configSettings.minDelay;
    document.getElementById('maxDelay').value = configSettings.maxDelay;

    document.getElementById('btnSelecionarPasta').addEventListener('click', async () => {
        const pasta = await eel.selecionar_pasta()();
        if (pasta) {
            document.getElementById('caminhoDestino').value = pasta;
            downloadState.caminhoDestino = pasta;
        }
    });

    // Inicializa no modo padrão (TXT)
    alterarModo('txt');
});