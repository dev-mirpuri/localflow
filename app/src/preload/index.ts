import { contextBridge, ipcRenderer } from 'electron'

// The pages' only way out: no Node and no raw ipcRenderer.
const localflow: LocalFlow = {
  onEvent(callback) {
    const listener = (_event: unknown, message: EngineMessage): void => callback(message)
    ipcRenderer.on('event', listener)
    return () => ipcRenderer.off('event', listener)
  },
  request: (method, params) => ipcRenderer.invoke('request', method, params),
  command: (name) => ipcRenderer.send('command', name),
  copy: (text) => ipcRenderer.send('copy', text)
}

contextBridge.exposeInMainWorld('localflow', localflow)
