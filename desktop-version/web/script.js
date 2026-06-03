document.getElementById('formDownload').addEventListener('submit', async (e) => {
    e.preventDefault();

    const url = document.getElementById('url').value;
    const inicio = parseInt(document.getElementById('capituloInicial').value);
    const fim = parseInt(document.getElementById('capituloFinal').value);
    const formato = document.querySelector('input[name="formato"]:checked').value;
    const listaProgresso = document.getElementById('progresso');
    const linkDownload = document.getElementById('linkDownload');

    // Limpa estados anteriores
    listaProgresso.innerHTML = '';
    linkDownload.innerHTML = 'Aguardando seleção de pasta de destino...';

    // Chama a função exposta no Python (main.py)
    const resposta = await eel.iniciar_download_desktop(url, inicio, fim, formato)();

    if (resposta.ok) {
        linkDownload.innerHTML = '<strong>Download em andamento...</strong>';
        // Inicializa tabela de progresso
        atualizarTabelaProgresso(inicio, fim);
    } else {
        linkDownload.innerHTML = `<span style="color:red;">${resposta.msg || 'Erro ao iniciar.'}</span>`;
    }
});

function atualizarTabelaProgresso(inicio, fim) {
    const listaProgresso = document.getElementById('progresso');

    // Cria tabela
    let html = '<table class="progress-table"><thead><tr><th>Cap</th><th>Título</th><th>Status</th></tr></thead><tbody id="progress-body">';

    for (let i = inicio; i <= fim; i++) {
        const num = String(i).padStart(5, '0');
        html += `<tr id="row-${num}"><td>${num}</td><td id="title-${num}">-</td><td id="status-${num}">⏳</td></tr>`;
    }

    html += '</tbody></table><div id="stats"></div>';
    listaProgresso.innerHTML = html;
}

// Expõe funções JS para o Python conseguir enviar dados em tempo real
eel.expose(receberProgresso);
function receberProgresso(capitulo, nome, atual, total, numero_cap) {
    const num = String(numero_cap).padStart(5, '0');
    const titleCell = document.getElementById(`title-${num}`);
    const statusCell = document.getElementById(`status-${num}`);

    if (titleCell) {
        titleCell.textContent = nome;
        statusCell.textContent = '✓';
        statusCell.style.color = 'green';
    }

    // Atualiza estatísticas
    const stats = document.getElementById('stats');
    const porcentagem = Math.round((atual / total) * 100);
    stats.innerHTML = `<div class="stats-summary">${atual}/${total} capítulos (${porcentagem}%)</div>`;
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
        statusCell.title = mensagem;
    }
}