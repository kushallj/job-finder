# 👻 Ghost Interview Copilot (Desktop App)
*Undetectable, Real-Time AI Interview Assistant & Teleprompter for macOS, Windows & Linux.*

---

## ⚡ Key Highlights
1. **100% Screen-Share Invisible**: Uses OS Compositor Exclusion (`NSWindowSharingNone` on macOS, `WDA_EXCLUDEFROMCAPTURE` on Windows). **Invisible on Zoom, Google Meet, Microsoft Teams, and WebRTC.**
2. **Sub-Microsecond In-Memory Trie (< 5µs)**: Instant bullet answers for 200+ algorithms, system design blueprints, and STAR stories.
3. **Global Panic Switch (`Cmd+Shift+X` / `Ctrl+Shift+X`)**: Instantly hides/restores the window from any focused app.
4. **Global Click-Through (`Cmd+Shift+C`)**: Enables mouse and keyboard events to pass straight through the HUD so you can code in LeetCode/VS Code underneath!
5. **Speech Listener**: Continuous loopback audio transcription.

---

## 🚀 Quick Start (Development)

```bash
cd sidekick-desktop
npm install
npm start
```

---

## 📦 Building Native Installers

### 🍎 macOS (.dmg / .zip / Apple Silicon & Intel)
```bash
npm run dist:mac
```

### 🪟 Windows (.exe / NSIS Installer / Portable)
```bash
npm run dist:win
```

### 🐧 Linux (.AppImage / .deb)
```bash
npm run dist:linux
```

All build artifacts will be output to `sidekick-desktop/dist/`.

---

## ⌨️ Global Hotkeys
- **`Cmd/Ctrl + Shift + X`**: Emergency Panic Hide / Show.
- **`Cmd/Ctrl + Shift + C`**: Toggle Click-Through Mode.
- **`Cmd/Ctrl + Shift + L`**: Toggle Invisibility Protection.
