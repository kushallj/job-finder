const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('ghostCopilot', {
  togglePanic: () => ipcRenderer.invoke('sidekick:toggle-panic'),
  setClickThrough: (enabled) => ipcRenderer.invoke('sidekick:set-click-through', enabled),
  setCompactMode: (compact) => ipcRenderer.invoke('sidekick:set-compact-mode', compact),
  toggleInvisibility: () => ipcRenderer.invoke('sidekick:toggle-invisibility'),
  closeApp: () => ipcRenderer.invoke('sidekick:close'),
  minimizeApp: () => ipcRenderer.invoke('sidekick:minimize'),
  onInvisibilityChanged: (callback) => ipcRenderer.on('status:invisibility-changed', (_, val) => callback(val)),
  onClickThroughChanged: (callback) => ipcRenderer.on('status:click-through-changed', (_, val) => callback(val)),
  onCompactChanged: (callback) => ipcRenderer.on('status:compact-changed', (_, val) => callback(val)),
});
