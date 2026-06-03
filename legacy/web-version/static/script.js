document.getElementById('formDownload').addEventListener('submit', async function (e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);
    formData.append('downloadZip', 'true'); // força o back-end a zipar

    const progressBar = document.getElementById('progressBar');
    const outputList = document.getElementById('output');
    progressBar.style.width = '0%';
    progressBar.textContent = '0%';
    outputList.innerHTML = '';

    const response = await fetch('/baixar', {
        method: 'POST',
        body: formData
    });

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'capitulos.zip';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    progressBar.style.width = '100%';
    progressBar.textContent = '100%';
    outputList.innerHTML = '<li>Download finalizado com sucesso.</li>';
});
