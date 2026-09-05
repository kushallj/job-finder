const { app, BrowserWindow, globalShortcut, ipcMain, screen, Tray, Menu } = require('electron');
const path = require('path');

let mainWindow = null;
let isPanicHidden = false;
let isClickThrough = false;
let isInvisible = true;
let isCompact = false;

function createGhostWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

  const windowWidth = 660;
  const windowHeight = 460;
  const x = Math.round((screenWidth - windowWidth) / 2);
  const y = 32; // Directly beneath the webcam for natural eye contact

  mainWindow = new BrowserWindow({
    width: windowWidth,
    height: windowHeight,
    minWidth: 520,
    minHeight: 140,
    x: x,
    y: y,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    hasShadow: false,
    resizable: true,
    focusable: true,
    backgroundColor: '#00000000',
    webPreferences: {
      preload: path.join(__dirname, '../preload/preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      backgroundThrottling: false,
    },
  });

  // 1. CORE OS-LEVEL INVISIBILITY: Exclude from Zoom, Google Meet, Teams, QuickTime, OBS
  // macOS: [NSWindow setSharingType:NSWindowSharingNone] (0)
  // Windows: SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE) (0x11)
  mainWindow.setContentProtection(true);

  // 2. Pin across all virtual desktops / spaces
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

  // Compact Mode Toggle: Cmd/Ctrl + Shift + M
  globalShortcut.register('CommandOrControl+Shift+M', () => {
    if (!mainWindow) return;
    isCompact = !isCompact;
    if (isCompact) {
      mainWindow.setSize(660, 160, true);
    } else {
      mainWindow.setSize(660, 460, true);
    }
    mainWindow.webContents.send('status:compact-changed', isCompact);
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

  ipcMain.handle('sidekick:set-compact-mode', (_, compact) => {
    if (!mainWindow) return false;
    isCompact = compact;
    if (isCompact) {
      mainWindow.setSize(660, 160, true);
    } else {
      mainWindow.setSize(660, 460, true);
    }
    return isCompact;
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
    if (!mainWindow) return;
    isPanicHidden = true;
    mainWindow.hide();
  });
}

app.whenReady().then(() => {
  // 3. STEALTH DOCK HIDING: Never show an icon or dot in macOS Dock
  if (process.platform === 'darwin' && app.dock) {
    app.dock.hide();
  }

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
