"""The Hotkey state machine: key events and times in, actions and swallow decisions out. No I/O.

Actions are "start", "hands_free", "finish", "cancel" and "discard".
"""

HOLD_S = 0.25
GAP_S = 0.35
LIMIT_S = 180

IDLE, HOLDING, TAP_WAIT, HANDS_FREE, PROCESSING = (
    "idle",
    "holding",
    "tap wait",
    "hands-free",
    "processing",
)
RECORDING = (HOLDING, TAP_WAIT, HANDS_FREE)


class Hotkey:
    """The spec's transition table. Times are seconds from any steady clock."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.state = IDLE
        self.pressed_at = 0.0
        self.released_at = 0.0
        self.held: set[str | int] = set()
        self.swallowing_esc = False

    def key(
        self, name: str, scan_code: int, down: bool, now: float, injected: bool = False
    ) -> tuple[list[str], bool]:
        """Feed one key event. Returns the actions, and whether to swallow the event.

        `injected` marks keys sent around the Engine's own Ctrl+V. They are ignored,
        except that a key-up still stops a key counting as held.
        """
        expired = self.tick(now)
        # ADR-0002: a key's name can change between down and up, so only these go by name.
        key = name if name in (self.name, "esc") else scan_code
        if injected:
            if not down:
                self.held.discard(key)
            return expired, False
        actions, swallow = self._key(key, down, now)
        return expired + actions, swallow

    def _key(self, key: str | int, down: bool, now: float) -> tuple[list[str], bool]:
        if key == "esc" and self.swallowing_esc:
            # The repeats and key-up of an Esc that cancelled are swallowed too.
            if not down:
                self.swallowing_esc = False
                self.held.discard(key)
            return [], True
        if not down:
            self.held.discard(key)
            return (self._hotkey_up(now) if key == self.name else []), False
        if key in self.held:
            return [], False  # auto-repeat
        self.held.add(key)
        if key == self.name:
            return self._hotkey_down(now), False
        if key == "esc" and self.state in RECORDING:
            self.state, self.swallowing_esc = IDLE, True
            return ["cancel"], True
        if self.state == HOLDING:
            self.state = IDLE
            return ["cancel"], False
        return [], False

    def _hotkey_down(self, now: float) -> list[str]:
        if self.state == IDLE:
            self.state, self.pressed_at = HOLDING, now
            return ["start"]
        if self.state == TAP_WAIT:
            self.state = HANDS_FREE
            return ["hands_free"]
        if self.state == HANDS_FREE:
            self.state = PROCESSING
            return ["finish"]
        return []

    def _hotkey_up(self, now: float) -> list[str]:
        if self.state != HOLDING:
            return []
        if now - self.pressed_at >= HOLD_S:
            self.state = PROCESSING
            return ["finish"]
        self.state, self.released_at = TAP_WAIT, now
        return []

    def tick(self, now: float) -> list[str]:
        """Call often: acts on the 350 ms gap and the 3-minute limit."""
        if self.state in (HOLDING, HANDS_FREE) and now - self.pressed_at >= LIMIT_S:
            self.state = PROCESSING
            return ["finish"]
        if self.state == TAP_WAIT and now - self.released_at > GAP_S:
            self.state = IDLE
            return ["discard"]
        return []

    def finish(self, now: float) -> list[str]:
        """✓ on the Oval."""
        return self._button(now, PROCESSING, "finish")

    def cancel(self, now: float) -> list[str]:
        """✕ on the Oval."""
        return self._button(now, IDLE, "cancel")

    def _button(self, now: float, state: str, action: str) -> list[str]:
        expired = self.tick(now)
        if self.state != HANDS_FREE:
            return expired
        self.state = state
        return [action]

    def done(self) -> None:
        """Processing is over: the next press starts a new Recording."""
        self.state = IDLE
