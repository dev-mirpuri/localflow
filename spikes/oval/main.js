// THROWAWAY spike S3: can the oval appear, animate and take a click without stealing focus from Notepad?
// Window setup follows section 4 of docs/PROJECT_BRIEF.md. Real code never imports from here.
const { app, BrowserWindow, ipcMain, screen } = require('electron')
const { spawn } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

// S3_SMOKE=1 is a self-check: any foreground app, 2 trials, a scripted click (not a real mouse click).
const SMOKE = process.env.S3_SMOKE === '1'
const TRIALS = SMOKE ? 2 : 20
const CLICK_THROUGH_MS = SMOKE ? 1000 : 15000
const WIDTH = 190
const HEIGHT = 44

const resultsDir = path.join(__dirname, 'results')
fs.mkdirSync(resultsDir, { recursive: true })
const logPath = path.join(resultsDir, SMOKE ? 'smoke.log' : `s3-${Date.now()}.log`)

let oval
let target = SMOKE ? null : 'notepad'
let foreground = ''
let stats = newStats()
let onButton = null

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

function log(line) {
  const stamped = `${new Date().toISOString()} ${line}`
  console.log(stamped)
  fs.appendFileSync(logPath, stamped + '\n')
}

function newStats() {
  return { left: [], focus: 0, keys: 0, downs: 0, fps: [] }
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b)
  return sorted[Math.floor(sorted.length / 2)] ?? 0
}

function startForegroundWatcher() {
  const watcher = spawn('powershell.exe', [
    '-NoProfile', '-ExecutionPolicy', 'Bypass',
    '-File', path.join(__dirname, 'foreground.ps1'), String(process.pid)
  ])
  let buffer = ''
  watcher.stdout.on('data', (chunk) => {
    buffer += chunk
    const lines = buffer.split(/\r?\n/)
    buffer = lines.pop()
    for (const line of lines) {
      const [hwnd, name, pidField] = line.split(' ')
      foreground = name.toLowerCase()
      if (target === null) target = foreground
      const ownHwnd = oval.getNativeWindowHandle().readBigUInt64LE().toString()
      log(`foreground: ${name} hwnd=${hwnd} ${pidField ?? ''} (spike pid=${process.pid}, oval hwnd=${ownHwnd})`)
      if (foreground !== target) stats.left.push(name)
    }
  })
  watcher.stderr.on('data', (chunk) => log(`watcher error: ${chunk}`))
}

function createOval() {
  const { workArea } = screen.getPrimaryDisplay()
  oval = new BrowserWindow({
    width: WIDTH,
    height: HEIGHT,
    x: Math.round(workArea.x + (workArea.width - WIDTH) / 2),
    y: workArea.y + workArea.height - HEIGHT - 12,
    frame: false,
    transparent: true,
    focusable: false,
    resizable: false,
    hasShadow: false,
    show: false,
    webPreferences: { preload: path.join(__dirname, 'preload.js') }
  })
  oval.setAlwaysOnTop(true, 'screen-saver')
  oval.setIgnoreMouseEvents(true)
  oval.on('focus', () => {
    stats.focus += 1
    log('OVAL GOT FOCUS')
  })
  return oval.loadFile(path.join(__dirname, 'oval.html'))
}

function setState(state, text) {
  oval.setIgnoreMouseEvents(state !== 'handsfree')
  oval.webContents.send('state', { state, text })
}

function waitForButton() {
  return new Promise((resolve) => { onButton = resolve })
}

async function runTrial(n) {
  while (foreground !== target) await sleep(50)
  await sleep(1000)
  stats = newStats()

  setState('listening', String(n))
  oval.showInactive()
  await sleep(1200)

  setState('handsfree', String(n))
  if (SMOKE) {
    await sleep(400)
    fs.writeFileSync(path.join(resultsDir, 'smoke.png'), (await oval.webContents.capturePage()).toPNG())
    oval.webContents.executeJavaScript(`document.getElementById('${n % 2 ? 'check' : 'cancel'}').click()`)
  }
  const button = await waitForButton()
  const downsToClick = stats.downs

  setState('processing', String(n))
  await sleep(1000)
  oval.hide()
  await sleep(2000)

  const ok = stats.left.length === 0 && stats.focus === 0 && stats.keys === 0
  log(
    `trial ${n}/${TRIALS} ${ok ? 'ok' : 'FAIL'} button=${button} pressesToClick=${downsToClick} ` +
      `left=[${stats.left}] ovalFocus=${stats.focus} ovalKeys=${stats.keys} fps=${median(stats.fps)}`
  )
  return { ok, fps: stats.fps }
}

async function runClickThroughCheck() {
  log(`CLICK-THROUGH CHECK: click on the oval a few times. It stays up ${CLICK_THROUGH_MS / 1000} s.`)
  stats = newStats()
  setState('listening', 'click')
  oval.showInactive()
  await sleep(CLICK_THROUGH_MS)
  oval.hide()
  log(`click-through: presses that reached the oval=${stats.downs} (want 0) left=[${stats.left}]`)
  return stats.downs
}

async function runDrill() {
  log(`electron ${process.versions.electron}, ${TRIALS} trials`)
  log(`Waiting for ${target ?? 'the first foreground app'}. Click into it to start.`)
  const results = []
  for (let n = 1; n <= TRIALS; n += 1) results.push(await runTrial(n))
  const reachedOval = await runClickThroughCheck()

  const passed = results.filter((r) => r.ok).length
  log(`RESULT focus held ${passed}/${TRIALS} trials; median fps ${median(results.flatMap((r) => r.fps))}; click-through presses reaching oval ${reachedOval}`)
  log(`Log: ${logPath}`)
  app.exit(0)
}

// Electron's default here is an error dialog, which would take focus and spoil the result.
process.on('uncaughtException', (error) => {
  log(`SPIKE ERROR, run is invalid: ${error.stack}`)
  app.exit(1)
})

ipcMain.on('mousedown', () => { stats.downs += 1 })
ipcMain.on('keydown', () => { stats.keys += 1 })
ipcMain.on('fps', (_e, value) => { stats.fps.push(value) })
ipcMain.on('button', (_e, name) => { if (onButton) onButton(name); onButton = null })

app.whenReady().then(async () => {
  await createOval()
  setInterval(() => {
    if (!oval.isDestroyed() && oval.isVisible()) oval.webContents.send('level', 0.5 + 0.5 * Math.sin(Date.now() / 180) * Math.random())
  }, 50)
  startForegroundWatcher()
  runDrill()
})
