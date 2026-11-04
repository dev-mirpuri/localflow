"""THROWAWAY spike S2: do hold and double-tap feel right, and does paste work everywhere?

Never imported by real code. No model runs: "processing" is a sleep, and the pasted text is canned.
Everything printed is also appended to results/s2.log. How to run it: see the spike's hand-off.
"""

import argparse
import collections
import ctypes
import queue
import random
import statistics
import threading
import time
import wave
import winsound
from pathlib import Path

import keyboard
import sounddevice as sd

RESULTS = Path(__file__).parent / "results"
u32, k32 = ctypes.WinDLL("user32"), ctypes.WinDLL("kernel32")
HANDLE, SIZE, UINT = ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint
u32.GetClipboardData.restype, u32.GetClipboardData.argtypes = HANDLE, (UINT,)
u32.SetClipboardData.restype, u32.SetClipboardData.argtypes = HANDLE, (UINT, HANDLE)
u32.OpenClipboard.argtypes, u32.EnumClipboardFormats.argtypes = (HANDLE,), (UINT,)
u32.RegisterClipboardFormatW.restype = UINT
k32.GlobalAlloc.restype, k32.GlobalAlloc.argtypes = HANDLE, (UINT, SIZE)
k32.GlobalLock.restype, k32.GlobalLock.argtypes = HANDLE, (HANDLE,)
k32.GlobalUnlock.argtypes, k32.GlobalFree.argtypes = (HANDLE,), (HANDLE,)
k32.GlobalSize.restype, k32.GlobalSize.argtypes = SIZE, (HANDLE,)

CF_UNICODETEXT = 13
HANDLE_FORMATS = {2, 3, 9, 14, 0x80, 0x82, 0x83, 0x8E}  # GDI handles and owner-drawn: not memory
NO_HISTORY = [
    u32.RegisterClipboardFormatW(n)
    for n in (
        "ExcludeClipboardContentFromMonitorProcessing",
        "CanIncludeInClipboardHistory",
        "CanUploadToCloudClipboard",
    )
]
log_lock = threading.Lock()


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    with log_lock:
        print(line, flush=True)
        with open(RESULTS / "s2.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")


def open_clipboard():
    for _ in range(100):
        if u32.OpenClipboard(None):
            return
        time.sleep(0.01)
    raise OSError("clipboard stayed busy for 1 s")


def format_name(fmt):
    buf = ctypes.create_unicode_buffer(128)
    return buf.value if u32.GetClipboardFormatNameW(fmt, buf, 128) else f"#{fmt}"


def clipboard_save():
    """Copy every memory-block format. Returns ([(format, bytes)], [skipped format names])."""
    items, skipped = [], []
    open_clipboard()
    try:
        fmt = u32.EnumClipboardFormats(0)
        while fmt:
            handle = None
            if fmt not in HANDLE_FORMATS and not 0x200 <= fmt <= 0x3FF:
                handle = u32.GetClipboardData(fmt)
            size = k32.GlobalSize(handle) if handle else 0
            ptr = k32.GlobalLock(handle) if size else None
            if ptr:
                items.append((fmt, ctypes.string_at(ptr, size)))
                k32.GlobalUnlock(handle)
            else:
                skipped.append(format_name(fmt))
            fmt = u32.EnumClipboardFormats(fmt)
    finally:
        u32.CloseClipboard()
    return items, skipped


def clipboard_write(items):
    """Replace the clipboard with items, always marked to stay out of Win+V history."""
    open_clipboard()
    try:
        u32.EmptyClipboard()
        for fmt, data in items + [(f, b"\0\0\0\0") for f in NO_HISTORY]:
            mem = k32.GlobalAlloc(0x0002, max(len(data), 1))  # GMEM_MOVEABLE
            ctypes.memmove(k32.GlobalLock(mem), data, len(data))
            k32.GlobalUnlock(mem)
            if not u32.SetClipboardData(fmt, mem):
                k32.GlobalFree(mem)
    finally:
        u32.CloseClipboard()


def text_item(text):
    return [(CF_UNICODETEXT, text.encode("utf-16-le") + b"\0\0")]


injecting = threading.Event()  # our own Ctrl+V must not reach the hotkey logic


def paste(text, restore_ms):
    t0 = time.perf_counter()
    saved, skipped = clipboard_save()
    t1 = time.perf_counter()
    clipboard_write(text_item(text))
    injecting.set()
    keyboard.send("ctrl+v")
    time.sleep(0.03)
    injecting.clear()
    t2 = time.perf_counter()
    time.sleep(restore_ms / 1000)
    clipboard_write(saved)
    after = dict(clipboard_save()[0])
    lost = [format_name(f) for f, b in saved if not after.get(f, b"").startswith(b)]
    names = [format_name(f) for f, _ in saved]
    log(
        f"  paste save={(t1 - t0) * 1000:.0f}ms send={(t2 - t1) * 1000:.0f}ms "
        f"restore_wait={restore_ms}ms bytes={sum(len(b) for _, b in saved)} formats={names} "
        f"skipped={skipped} restore_verify={'OK' if not lost else f'DIFFERS {lost}'}"
    )


class Hotkey:
    """The brief's section 4 hotkey rules. Runs on the hook thread, so it only sets state."""

    def __init__(self, combo, trigger, hold_s, gap_s, events):
        self.combo, self.trigger, self.hold_s, self.gap_s = set(combo), trigger, hold_s, gap_s
        self.events = events
        self.state, self.recording, self.esc_down = "idle", False, False
        self.down, self.t_press, self.t_release = set(), 0.0, 0.0
        self.lock = threading.Lock()

    def feed(self, key, is_down, t):
        """Returns True if this key event must be swallowed."""
        with self.lock:
            if key == "esc":
                if is_down and self.recording and not self.esc_down:
                    self.esc_down = True
                    self.end("cancel_esc", t)
                if self.esc_down:
                    self.esc_down = is_down
                    return True
                return False
            repeat = is_down and key in self.down
            was_on = self.combo <= self.down
            (self.down.add if is_down else self.down.discard)(key)
            is_on = self.combo <= self.down
            if repeat:
                return False
            if is_on and not was_on:
                self.pressed(t)
            elif was_on and not is_on:
                self.released(t)
            elif is_down and key not in self.combo and self.state == "hold":
                self.end("cancel_key", t)
            return False

    def tick(self, t):
        with self.lock:
            if self.state == "wait" and t - self.t_release > self.gap_s:
                self.end("discard", t)

    def go(self, state, t, note=""):
        self.state = state
        self.events.put(("state", state, t, note))

    def start_recording(self, t):
        self.recording = True
        self.events.put(("mic_start", None, t, ""))

    def pressed(self, t):
        if self.state == "idle":
            self.t_press = t
            if self.trigger == "double_tap":
                self.go("first_tap", t)
            else:
                self.start_recording(t)
                self.go("hold", t)
        elif self.state == "wait":
            if not self.recording:
                self.start_recording(t)
            self.go("handsfree", t, f"gap={(t - self.t_release) * 1000:.0f}ms")
        elif self.state == "handsfree":
            self.end("handsfree", t)

    def released(self, t):
        held = t - self.t_press
        note = f"held={held * 1000:.0f}ms"
        if self.state == "hold" and held >= self.hold_s:
            self.end("ptt", t, note)
        elif self.state == "first_tap" and held >= self.hold_s:
            self.end("ignored", t, note)
        elif self.state == "first_tap" or (self.state == "hold" and self.trigger == "both"):
            self.t_release = t
            self.go("wait", t, note)
        elif self.state == "hold":
            self.end("discard", t, note)

    def end(self, outcome, t, note=""):
        self.recording, self.state = False, "idle"
        self.events.put(("end", outcome, t, note))


DRILLS = {
    "both": [
        ("HOLD about 1 s, release", "ptt", 18),
        ("quick TAP once", "discard", 10),
        ("DOUBLE-TAP, wait 1 s, tap to finish", "handsfree", 12),
        ("HOLD, then press F9 while holding", "cancel_key", 5),
        ("DOUBLE-TAP, wait 1 s, press Esc", "cancel_esc", 5),
    ],
    "hold": [
        ("HOLD about 1 s, release", "ptt", 30),
        ("quick TAP once", "discard", 10),
        ("HOLD, then press F9 while holding", "cancel_key", 5),
        ("HOLD, then press Esc while holding", "cancel_esc", 5),
    ],
    "double_tap": [
        ("DOUBLE-TAP, wait 1 s, tap to finish", "handsfree", 30),
        ("quick TAP once", "discard", 10),
        ("LONG press about 1 s (nothing should happen)", "ignored", 5),
        ("DOUBLE-TAP, wait 1 s, press Esc", "cancel_esc", 5),
    ],
}
SINGLE_LINE = "S2 test {n}, hold, one line, café."
MULTI_LINE = "S2 test {n}, hands-free, line one.\nLine two.\nLine three."


def beep(*tones):
    threading.Thread(target=lambda: [winsound.Beep(f, 60) for f in tones], daemon=True).start()


class Mic:
    """Opens the mic when told to, as the brief plans, and reports how late the first audio is."""

    def __init__(self):
        self.stream, self.first, self.frames, self.count = None, None, [], 0

    def callback(self, data, _frames, _time, _status):
        self.first = self.first or time.perf_counter()
        self.frames.append(bytes(data))

    def start(self, t_press):
        self.first, self.frames = None, []
        self.stream = sd.RawInputStream(
            samplerate=16000, blocksize=320, channels=1, dtype="int16", callback=self.callback
        )
        self.stream.start()
        opened = time.perf_counter()
        while not self.first and time.perf_counter() - opened < 2:
            time.sleep(0.001)
        first = self.first or opened
        log(
            f"  mic stream_open={(opened - t_press) * 1000:.0f}ms first_audio={(first - t_press) * 1000:.0f}ms"
        )

    def stop(self, keep):
        self.stream.stop()
        self.stream.close()
        if keep:
            self.count += 1
            path = RESULTS / f"mic-{time.strftime('%H%M%S')}-{self.count:02}.wav"
            with wave.open(str(path), "wb") as f:
                f.setnchannels(1), f.setsampwidth(2), f.setframerate(16000)
                f.writeframes(b"".join(self.frames))
            log(f"  mic saved {path.name}; playing it back")
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)


def paste_worker(jobs, hotkey, args):
    while True:
        text, t_end = jobs.get()
        time.sleep(args.proc_ms / 1000)
        waited = time.perf_counter()
        while hotkey.combo & hotkey.down:  # Ctrl+V must not combine with held hotkey keys
            time.sleep(0.005)
        waited = time.perf_counter() - waited
        paste(text + " ", args.restore_ms)
        log(
            f"  pasted {time.perf_counter() - t_end:.2f}s after finish (waited {waited * 1000:.0f}ms for keys up); queue={jobs.qsize()}"
        )


def run_hotkey(args):
    combo = [k.strip().lower() for k in args.keys.split("+")]
    events, jobs = queue.Queue(), queue.Queue()
    hotkey = Hotkey(combo, args.trigger, args.hold_ms / 1000, args.gap_ms / 1000, events)
    hook_times, outcomes, misfires, count = [], collections.Counter(), [], 0
    mic = Mic() if args.mic else None
    drill = [(p, o) for p, o, n in DRILLS[args.trigger] for _ in range(n)] if args.drill else []
    random.shuffle(drill)
    total = len(drill)

    def on_key(e):
        if injecting.is_set() or e.name is None:
            return True
        t = time.perf_counter()
        # Names change with Shift ("a" down, "A" up), so only named keys are tracked by name.
        key = e.name if e.name == "esc" or e.name in hotkey.combo else e.scan_code
        swallow = hotkey.feed(key, e.event_type == "down", t)
        hook_times.append(time.perf_counter() - t)
        return not swallow

    def ticker():
        while True:
            hotkey.tick(time.perf_counter())
            time.sleep(0.005)

    threading.Thread(target=ticker, daemon=True).start()
    threading.Thread(target=paste_worker, args=(jobs, hotkey, args), daemon=True).start()
    keyboard.hook(on_key, suppress=True)
    log(f"=== hotkey run: {vars(args)}")
    log("Listening. Ctrl+C in this window to stop and see the summary.")
    if drill:
        log(f"DRILL 1/{total}: {drill[0][0]}")
    try:
        while True:
            try:  # a blocking get with no timeout can't be interrupted by Ctrl+C on Windows
                kind, value, t, note = events.get(timeout=0.1)
            except queue.Empty:
                continue
            if kind == "mic_start":
                if mic:
                    mic.start(t)
                else:
                    beep(880)
            elif kind == "state":
                log(f"state={value} {note}")
            elif kind == "end":
                done = value in ("ptt", "handsfree")
                outcomes[value] += 1
                log(f"END {value} {note} | counts={dict(outcomes)} queue={jobs.qsize()}")
                if mic and mic.stream:
                    mic.stop(done)
                    mic.stream = None
                elif not mic:
                    beep(*((660,) if done else (330, 330)))
                if done:
                    count += 1
                    jobs.put(((SINGLE_LINE if value == "ptt" else MULTI_LINE).format(n=count), t))
                if drill:
                    prompt, want = drill.pop(0)
                    if value != want:
                        misfires.append((prompt, want, value))
                        log(f"  MISFIRE: asked '{prompt}', expected {want}, got {value}")
                    log(
                        f"DRILL {total - len(drill) + 1}/{total}: {drill[0][0]}"
                        if drill
                        else "DRILL DONE"
                    )
    except KeyboardInterrupt:
        keyboard.unhook_all()
        ms = sorted(x * 1000 for x in hook_times) or [0]
        log(
            f"SUMMARY outcomes={dict(outcomes)} misfires={len(misfires)}/{total - len(drill)} {misfires}"
        )
        log(
            f"SUMMARY hook time over {len(ms)} key events: median={statistics.median(ms):.3f}ms p99={ms[int(len(ms) * 0.99)]:.3f}ms max={ms[-1]:.3f}ms"
        )


def run_restore_test(args):
    delays = [int(d) for d in args.delays.split(",")]
    original = clipboard_save()[0]
    log(f"=== restore test: delays={delays} rounds={args.rounds}")
    for s in range(args.countdown, 0, -1):
        print(f"Click into the target text box now: {s}", flush=True)
        time.sleep(1)
    for d in delays:
        for _ in range(args.rounds):
            clipboard_write(text_item(f"[{d}ms OLD] "))
            paste(f"[{d}ms new] ", d)
            time.sleep(0.3)
    clipboard_write(original)
    log(
        "Done, clipboard put back. Any OLD in the target means that delay is too short for that app."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keys", default="right ctrl", help='"right ctrl" or "ctrl+shift" etc.')
    parser.add_argument("--trigger", default="both", choices=DRILLS)
    parser.add_argument("--hold-ms", type=int, default=250)
    parser.add_argument("--gap-ms", type=int, default=350)
    parser.add_argument("--restore-ms", type=int, default=200)
    parser.add_argument("--proc-ms", type=int, default=500, help="fake processing time")
    parser.add_argument("--drill", action="store_true", help="prompt and score 50 mixed presses")
    parser.add_argument("--mic", action="store_true", help="really open the mic on key-down")
    parser.add_argument("--restore-test", action="store_true")
    parser.add_argument("--delays", default="0,10,25,50,100,200,500")
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--countdown", type=int, default=5)
    cli = parser.parse_args()
    RESULTS.mkdir(exist_ok=True)
    (run_restore_test if cli.restore_test else run_hotkey)(cli)
