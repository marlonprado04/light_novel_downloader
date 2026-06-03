const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  baixarCapitulos: (params) => ipcRenderer.invoke('baixar-capitulos', params),
  baixarCapitulosComProgresso: (params, onProgresso) => {
    return new Promise((resolve, reject) => {
      ipcRenderer.invoke('baixar-capitulos-com-progresso', params);
      const progressoListener = (event, progresso) => {
        onProgresso(progresso);
      };
      ipcRenderer.on('progresso-capitulo', progressoListener);
      ipcRenderer.once('baixar-capitulos-finalizado', (event, result) => {
        ipcRenderer.removeListener('progresso-capitulo', progressoListener);
        resolve(result);
      });
    });
  }
});
