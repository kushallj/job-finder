const { app, BrowserWindow, globalShortcut, ipcMain, screen, Tray, Menu } = require('electron');
const path = require('path');

let mainWindow = null;
let isPanicHidden = false;
let isClickThrough = false;
let isInvisible = true;
let tray = null;

function createGhostWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

  const windowWidth = 680;
  const windowHeight = 420;
  const x = Math.round((screenWidth - windowWidth) / 2);
  const y = 30; // Direct eye-line beneath webcam

  mainWindow = new BrowserWindow({
    width: windowWidth,
    height: windowHeight,
    x: x,
    y: y,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    hasShadow: false,
    resizable: true,
    focusable: true,
    webPreferences: {
      preload: path.join(__dirname, '../preload/preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      backgroundThrottling: false,
    },
  });

  // 1. CORE INVISIBILITY: Exclude from Screen Capture (Zoom, Meet, Teams, WebRTC)
  // macOS: NSWindowSharingNone (0) | Windows: WDA_EXCLUDEFROMCAPTURE (0x11)
  mainWindow.setContentProtection(true);

  // 2. Multi-space / Full-screen pinning
  if (process.platform === 'darwin') {
    mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
    mainWindow.setAlwaysOnTop(true, 'screen-saver', 1);
  } else {
    mainWindow.setAlwaysOnTop(true, 'screen-saver');
  }

  mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function registerGlobalShortcuts() {
  // Panic Toggle: Cmd/Ctrl + Shift + X
  globalShortcut.register('CommandOrControl+Shift+X', () => {
    if (!mainWindow) return;
    isPanicHidden = !isPanicHidden;
    if (isPanicHidden) {
      mainWindow.hide();
    } else {
      mainWindow.show();
      mainWindow.focus();
    }
  });

  // Click-Through Toggle: Cmd/Ctrl + Shift + C
  globalShortcut.register('CommandOrControl+Shift+C', () => {
    if (!mainWindow) return;
    isClickThrough = !isClickThrough;
    mainWindow.setIgnoreMouseEvents(isClickThrough, { forward: true });
    mainWindow.webContents.send('status:click-through-changed', isClickThrough);
  });

  // Invisibility Protection Toggle: Cmd/Ctrl + Shift + L
  globalShortcut.register('CommandOrControl+Shift+L', () => {
    if (!mainWindow) return;
    isInvisible = !isInvisible;
    mainWindow.setContentProtection(isInvisible);
    mainWindow.webContents.send('status:invisibility-changed', isInvisible);
  });
}

function setupIPC() {
  ipcMain.handle('sidekick:toggle-panic', () => {
    if (!mainWindow) return false;
    isPanicHidden = !isPanicHidden;
    if (isPanicHidden) mainWindow.hide();
    else mainWindow.show();
    return isPanicHidden;
  });

  ipcMain.handle('sidekick:set-click-through', (_, enabled) => {
    if (!mainWindow) return false;
    isClickThrough = enabled;
    mainWindow.setIgnoreMouseEvents(enabled, { forward: true });
    return isClickThrough;
  });

  ipcMain.handle('sidekick:toggle-invisibility', () => {
    if (!mainWindow) return false;
    isInvisible = !isInvisible;
    mainWindow.setContentProtection(isInvisible);
    return isInvisible;
  });

  ipcMain.handle('sidekick:close', () => {
    if (mainWindow) mainWindow.close();
    app.quit();
  });

  ipcMain.handle('sidekick:minimize', () => {
    if (mainWindow) mainWindow.minimize();
  });
}

app.whenReady().then(() => {
  createGhostWindow();
  registerGlobalShortcuts();
  setupIPC();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createGhostWindow();
  });
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
