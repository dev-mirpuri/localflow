import { app, BrowserWindow, clipboard, ipcMain, Menu, screen, Tray } from 'electron'
import { spawn, type ChildProcessByStdio } from 'node:child_process'
import { join } from 'node:path'
import { createInterface } from 'node:readline'
import type { Readable, Writable } from 'node:stream'
import icon from '../../resources/icon.png?asset'

const OVAL_WIDTH = 190 // The size and gap spike S3 proved (ADR-0003).
const OVAL_HEIGHT = 44
const OVAL_GAP = 12
const ERROR_SHOWN_MS = 4000
const QUIT_WAIT_MS = 15000 // Unloading the cleanup model can take up to 5 s.
const CRASHED = "LocalFlow's engine stopped. Quit LocalFlow from the tray and start it again."

let engine: ChildProcessByStdio<Writable, Readable, null> | null = null // null once it has exited
let history: BrowserWindow
let oval: BrowserWindow
let tray: Tray // Held here so it isn't garbage-collected.
let quitting = false
let errorTimer: NodeJS.Timeout | undefined
let nextId = 1
const replies = new Map<
  number,
  { resolve: (data: unknown) => void; reject: (error: Error) => void }
>()

function startEngine(): void {
  const dataDir = join(app.getPath('appData'), app.isPackaged ? 'LocalFlow' : 'LocalFlow Dev')
  const [command, args] = app.isPackaged
    ? [join(process.resourcesPath, 'engine', 'localflow-engine.exe'), []]
    : ['uv', ['run', '--project', join(app.getAppPath(), '..', 'engine'), 'localflow-engine']]
  const child = spawn(command, [...args, 'dictate', '--data-dir', dataDir], {
    stdio: ['pipe', 'pipe', 'inherit'],
    windowsHide: true
  })
  child.on('error', engineStopped) // For example, uv isn't installed.
  child.on('close', engineStopped) // After stdout ends, so no last line arrives after it.
  child.stdin.on('error', () => {}) // A write after a crash; 'exit' reports the crash.
  createInterface({ input: child.stdout }).on('line', onEngineLine)
  engine = child
}

function engineStopped(): void {
  if (!engine) return
  engine = null
  replies.forEach(({ reject }) => reject(new Error('the engine stopped')))
  replies.clear()
  if (quitting) app.quit()
  else onEngineMessage({ type: 'error', message: CRASHED }) // No automatic restart.
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
    replies.get(message.id as number)?.resolve(message.data)
    replies.delete(message.id as number)
  } else {
    onEngineMessage(message)
  }
}

function onEngineMessage(message: EngineMessage): void {
  for (const window of [history, oval]) {
    if (!window.isDestroyed()) window.webContents.send('event', message)
  }
  if (message.type === 'error') {
    clearTimeout(errorTimer)
    showOval(true)
    errorTimer = setTimeout(() => {
      errorTimer = undefined
      showOval(false)
    }, ERROR_SHOWN_MS)
  } else if (message.type === 'state' && !(message.state === 'idle' && errorTimer)) {
    clearTimeout(errorTimer) // An idle right after an error leaves the error showing.
    errorTimer = undefined
    showOval(message.state !== 'idle')
  }
}

function showOval(shown: boolean): void {
  if (oval.isDestroyed()) return
  if (shown) oval.showInactive()
  else oval.hide()
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
  history.on('close', (event) => {
    if (quitting) return
    event.preventDefault()
    history.hide()
  })
  loadPage(history, 'history.html')
}

function createOval(): void {
  const { workArea } = screen.getPrimaryDisplay()
  oval = new BrowserWindow({
    width: OVAL_WIDTH,
    height: OVAL_HEIGHT,
    x: Math.round(workArea.x + (workArea.width - OVAL_WIDTH) / 2),
    y: workArea.y + workArea.height - OVAL_HEIGHT - OVAL_GAP,
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
  oval.setIgnoreMouseEvents(true) // The ✕ and ✓ buttons come in T7.
  loadPage(oval, 'oval.html')
}

function openHistory(): void {
  if (!history || history.isDestroyed()) return // A second launch before ready, or while quitting.
  if (history.isMinimized()) history.restore()
  history.show()
  history.focus()
}

if (!app.requestSingleInstanceLock()) {
  app.quit()
} else {
  app.on('second-instance', openHistory)

  // Quit waits for the engine: closing its stdin makes it unload the cleanup model and exit.
  app.on('before-quit', (event) => {
    quitting = true
    clearTimeout(errorTimer) // A timer firing on a destroyed window opens an error dialog (ADR-0003).
    if (!engine) return
    event.preventDefault()
    engine.stdin.end()
    setTimeout(() => engine?.kill(), QUIT_WAIT_MS).unref() // A stuck Engine can't block Quit.
  })

  ipcMain.handle('request', (_event, method: string, params: unknown) => {
    if (!engine) throw new Error('the engine stopped')
    const id = nextId++
    sendToEngine({ type: 'request', id, method, params })
    return new Promise((resolve, reject) => replies.set(id, { resolve, reject }))
  })
  ipcMain.on('command', (_event, name: string) => sendToEngine({ type: 'command', name }))
  ipcMain.on('copy', (_event, text: string) => clipboard.writeText(text))

  app.whenReady().then(() => {
    app.setAppUserModelId('com.localflow.app')
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
    startEngine()
  })
}
