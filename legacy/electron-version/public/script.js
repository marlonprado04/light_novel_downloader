const form = document.getElementById('formDownload');
const lista = document.getElementById('progresso');
const linkDownload = document.getElementById('linkDownload');
const barra = document.createElement('progress');
barra.value = 0;
barra.max = 1;
barra.style.width = '100%';
barra.style.display = 'none';
form.parentNode.insertBefore(barra, lista);

let capStatus = {};
let capOrder = [];

form.addEventListener('submit', async function (e) {
    e.preventDefault();
    lista.innerHTML = "";
    linkDownload.innerHTML = "";
    barra.value = 0;
    barra.style.display = 'block';
    capStatus = {};
    capOrder = [];

    const url = document.getElementById('url').value;
    const inicio = Number(document.getElementById('capituloInicial').value);
    const fim = Number(document.getElementById('capituloFinal').value);
    barra.max = fim - inicio + 1;
    barra.value = 0;
    // Chama o backend via IPC e recebe progresso
    let progressoList = [];
    window.electronAPI.baixarCapitulosComProgresso({ url, inicio, fim }, (progresso) => {
        progressoList.push(progresso);
        // Ordena o progressoList pelo número do capítulo
        progressoList.sort((a, b) => {
            const getNum = (cap) => {
                const match = String(cap.capitulo).match(/\d+/);
                return match ? parseInt(match[0], 10) : 0;
            };
            return getNum(a) - getNum(b);
        });
        lista.innerHTML = "";
        progressoList.forEach((data) => {
            let capKey = data.capitulo;
            let item = document.createElement('li');
            item.textContent = `Baixado: ${data.capitulo} - ${data.nome}`;
            item.style.color = data.nome === 'ERRO' ? 'red' : '';
            item.dataset.capnum = capKey;
            lista.appendChild(item);
        });
        barra.value = progresso.atual;
        barra.max = progresso.total;
        barra.style.display = 'block';
    }).then(result => {
        barra.style.display = 'none';
        if (result.ok) {
            const item = document.createElement('li');
            item.textContent = 'Download finalizado! Arquivo salvo em: ' + result.filePath;
            item.style.color = 'green';
            lista.appendChild(item);
        } else {
            const item = document.createElement('li');
            item.textContent = 'Erro ao baixar capítulos.';
            item.style.color = 'red';
            lista.appendChild(item);
        }
    });
});

let totalCaps = 1;
let baixados = 0;

function inserirOrdenado(item, capNum) {
    // capNum pode ser string tipo '10' ou '10-'
    let capNumFloat = parseFloat(capNum.replace('-', '.5'));
    let inserido = false;
    for (let i = 0; i < lista.children.length; i++) {
        let li = lista.children[i];
        let match = li.dataset.capnum;
        if (match) {
            let liNum = parseFloat(match.replace('-', '.5'));
            if (capNumFloat < liNum) {
                lista.insertBefore(item, li);
                inserido = true;
                break;
            }
        }
    }
    if (!inserido) lista.appendChild(item);
}
