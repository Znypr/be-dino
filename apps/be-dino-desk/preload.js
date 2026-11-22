// The window's only door to the main process (docs/247): catalog, feedback, a picture's folder, smoke helpers.
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('desk', {
  catalog: () => ipcRenderer.invoke('catalog'),
  feedback: { load: () => ipcRenderer.invoke('feedback:load'), save: (fb) => ipcRenderer.invoke('feedback:save', fb) },
  openFile: (rel) => ipcRenderer.invoke('open:file', rel),
  media: (rel) => 'desk://repo/' + String(rel).split('/').map(encodeURIComponent).join('/'),
  smokeShot: (name) => ipcRenderer.invoke('smoke:shot', name),
  smokeDone: (report) => ipcRenderer.invoke('smoke:done', report),
});
