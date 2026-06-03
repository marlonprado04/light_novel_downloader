document.getElementById('formDownload').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const url = document.getElementById('url').value;
    const inicio = parseInt(document.getElementById('capituloInicial').value);
    const fim = parseInt(document.getElementById('capituloFinal').value);
    const listaProgresso = document.getElementById('progresso');
    const linkDownload = document.getElementById('linkDownload');
    
    // Limpa estados anteriores
    listaProgresso.innerHTML = '';
    linkDownload.innerHTML = 'Aguardando seleção de pasta de destino...';
    
    // Chama a função exposta no Python (main.py)
    const resposta = await eel.iniciar_download_desktop(url, inicio, fim)();
    
    if (resposta.ok) {
        linkDownload.innerHTML = '<strong>Download em andamento...</strong>';
    } else {
        linkDownload.innerHTML = `<span style="color:red;">${resposta.msg || 'Erro ao iniciar.'}</span>`;
    }
});

// Expõe funções JS para o Python conseguir enviar dados em tempo real
eel.expose(receberProgresso);
function receberProgresso(capitulo, nome, atual, total) {
    const listaProgresso = document.getElementById('progresso');
    const porcentagem = Math.round((atual / total) * 100);
    
    // Atualiza ou cria mensagens de progresso na tela
    let item = document.getElementById(`cap-${atual}`);
    if (!item) {
        item = document.createElement('li');
        item.id = `cap-${atual}`;
        listaProgresso.appendChild(item);
    }
    item.innerHTML = `[${porcentagem}%] Baixado: ${capitulo} (${nome}) - ${atual}/${total}`;
    
    // Rola a lista de capítulos automaticamente para baixo
    listaProgresso.scrollTop = listaProgresso.scrollHeight;
}

eel.expose(finalizarDownload);
function finalizarDownload(sucesso, caminhoFinal) {
    const linkDownload = document.getElementById('linkDownload');
    if (sucesso) {
        linkDownload.innerHTML = `<span style="color:green; font-weight:bold;">Sucesso! Arquivo salvo em:<br><small>${caminhoFinal}</small></span>`;
    } else {
        linkDownload.innerHTML = '<span style="color:red; font-weight:bold;">Ocorreu um erro durante o empacotamento.</span>';
    }
}