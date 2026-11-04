// THROWAWAY spike S3.
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('oval', {
  onState: (fn) => ipcRenderer.on('state', (_e, msg) => fn(msg)),
  onLevel: (fn) => ipcRenderer.on('level', (_e, value) => fn(value)),
  send: (name, value) => ipcRenderer.send(name, value)
})
