import { app, BrowserWindow, clipboard, ipcMain, Menu, screen, Tray } from 'electron'
import { execFile, spawn, type ChildProcessByStdio } from 'node:child_process'
import { join } from 'node:path'
import { createInterface } from 'node:readline'
import type { Readable, Writable } from 'node:stream'
import icon from '../../resources/icon.png?asset'

const OVAL_HEIGHT = 44 // The height and gap spike S3 proved (ADR-0003).
const OVAL_GAP = 12
const OVAL_MARGIN = 6 // Room around the pill for its ring and shadow, as in the spike's 44 px.
const QUIT_WAIT_MS = 15000 // Unloading the cleanup model can take up to 5 s.
const CRASHED = "LocalFlow's engine stopped. Quit LocalFlow from the tray and start it again."

let engine: ChildProcessByStdio<Writable, Readable, null> | null = null // null once it has exited
let history: BrowserWindow
let oval: BrowserWindow
let tray: Tray // Held here so it isn't garbage-collected.
let quitting = false
let nextId = 1
let config: EngineMessage | null = null // Sent once at startup; a History page loaded later needs it.
const replies = new Map<number, (data: unknown) => void>()

function startEngine(): void {
  const dataDir = join(app.getPath('appData'), app.isPackaged ? 'LocalFlow' : 'LocalFlow Dev')
  const project = join(app.getAppPath(), '..', 'engine') // T10 swaps in the bundled exe.
  const child = spawn(
    'uv',
    ['run', '--project', project, 'localflow-engine', 'dictate', '--data-dir', dataDir],
    {
      stdio: ['pipe', 'pipe', 'inherit'],
      windowsHide: true
    }
  )
  child.on('error', engineStopped) // For example, uv isn't installed.
  child.on('close', engineStopped) // After stdout ends, so no last line arrives after it.
  child.stdin.on('error', () => {}) // A write after a crash; 'close' reports the crash.
  createInterface({ input: child.stdout }).on('line', onEngineLine)
  engine = child
}

function engineStopped(): void {
  if (!engine) return
  engine = null
  if (quitting) app.quit()
  else {
    onEngineMessage({ type: 'error', message: CRASHED }) // No automatic restart.
    onEngineMessage({ type: 'state', state: 'idle' }) // So no bars stay up from a dead Engine.
  }
}

function sendToEngine(message: EngineMessage): void {
  engine?.stdin.write(JSON.stringify(message) + '\n')
}

function onEngineLine(line: string): void {
  let message: EngineMessage
  try {
    message = JSON.parse(line)
  } catch {
    console.error('the engine sent a line that is not JSON')
    return
  }
  if (message.type === 'reply') {
    replies.get(message.id as number)?.(message.data)
    replies.delete(message.id as number)
  } else {
    onEngineMessage(message)
  }
}

function onEngineMessage(message: EngineMessage): void {
  if (message.type === 'config') config = message
  for (const window of [history, oval]) {
    if (!window.isDestroyed()) window.webContents.send('event', message)
  }
}

// The Oval page decides what shows; the window is held at the pill's size so no wider
// empty area takes clicks, and takes clicks only while ✕ and ✓ are visible (ADR-0003).
type Pill = { width: number; clickable: boolean } | null

function showOval(pill: Pill): void {
  if (oval.isDestroyed()) return
  if (!pill) {
    oval.hide()
    return
  }
  const { workArea } = screen.getPrimaryDisplay()
  const width = Math.min(Math.ceil(pill.width) + 2 * OVAL_MARGIN, workArea.width)
  oval.setBounds({
    x: Math.round(workArea.x + (workArea.width - width) / 2),
    y: workArea.y + workArea.height - OVAL_HEIGHT - OVAL_GAP,
    width,
    height: OVAL_HEIGHT
  })
  oval.setIgnoreMouseEvents(!pill.clickable)
  if (!oval.isVisible()) oval.showInactive()
}

function loadPage(window: BrowserWindow, page: string): void {
  if (!app.isPackaged && process.env['ELECTRON_RENDERER_URL']) {
    window.loadURL(`${process.env['ELECTRON_RENDERER_URL']}/${page}`)
  } else {
    window.loadFile(join(__dirname, '../renderer', page))
  }
}

const webPreferences = { preload: join(__dirname, '../preload/index.js') }

function createHistory(): void {
  history = new BrowserWindow({
    width: 900,
    height: 670,
    show: false,
    autoHideMenuBar: true,
    webPreferences
  })
  history.webContents.on('did-finish-load', () => {
    if (config) history.webContents.send('event', config)
  })
  history.on('restore', showSearch) // From the taskbar, which doesn't go through openHistory.
  history.on('close', (event) => {
    if (quitting) return
    event.preventDefault()
    history.hide()
  })
  loadPage(history, 'history.html')
}

function createOval(): void {
  oval = new BrowserWindow({
    height: OVAL_HEIGHT, // showOval sets the width and position each time.
    frame: false,
    transparent: true,
    focusable: false,
    resizable: false,
    hasShadow: false,
    skipTaskbar: true,
    show: false,
    webPreferences
  })
  oval.setAlwaysOnTop(true, 'screen-saver')
  oval.setIgnoreMouseEvents(true)
  // The Engine starts once the Oval page listens, so "Downloading speech model…" isn't missed.
  oval.webContents.once('did-finish-load', startEngine)
  loadPage(oval, 'oval.html')
}

function openHistory(): void {
  if (!history || history.isDestroyed()) return // A second launch before ready, or while quitting.
  if (history.isMinimized()) history.restore()
  history.show()
  history.focus()
  showSearch()
}

// The History page focuses search each time the window is shown.
function showSearch(): void {
  history.webContents.send('event', { type: 'shown' })
}

if (!app.requestSingleInstanceLock()) {
  app.quit()
} else {
  app.on('second-instance', openHistory)

  // Quit waits for the engine: closing its stdin makes it unload the cleanup model and exit.
  app.on('before-quit', (event) => {
    quitting = true
    if (!engine) return
    event.preventDefault()
    engine.stdin.end()
    // A stuck Engine can't block Quit. Killing only uv would leave python holding the
    // Hotkey hook and the VRAM, so the whole tree goes.
    const pid = String(engine.pid)
    setTimeout(
      () => execFile('taskkill', ['/pid', pid, '/T', '/F'], () => {}),
      QUIT_WAIT_MS
    ).unref()
  })

  ipcMain.handle('request', (_event, method: string, params: unknown) => {
    const id = nextId++
    sendToEngine({ type: 'request', id, method, params })
    return new Promise((resolve) => replies.set(id, resolve))
  })
  ipcMain.on('command', (_event, name: string) => sendToEngine({ type: 'command', name }))
  ipcMain.handle('copy', (_event, text: string) => clipboard.writeText(text))
  ipcMain.on('show-oval', (_event, pill: Pill) => showOval(pill))

  app.whenReady().then(() => {
    createOval()
    createHistory()
    history.once('ready-to-show', openHistory)
    tray = new Tray(icon)
    tray.setToolTip('LocalFlow')
    tray.setContextMenu(
      Menu.buildFromTemplate([
        { label: 'Open history', click: openHistory },
        { label: 'Quit', click: () => app.quit() }
      ])
    )
    tray.on('click', openHistory)
  })
}
