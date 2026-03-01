"""Gesture → key-event dispatcher with state machine and active-window gating."""

from __future__ import annotations

import subprocess
import time
from typing import Literal

try:
    from pynput import keyboard as _kb

    _ctrl = _kb.Controller()
    _HAS_PYNPUT = True
except ImportError:
    _ctrl = None  # type: ignore[assignment]
    _HAS_PYNPUT = False

# Gesture → profile shortcut-key name
# "fist" is not here — it drives the state machine, not a key event
_GESTURE_TO_ACTION: dict[str, str] = {
    "swipe_right": "next",
    "swipe_left":  "prev",
    "open_palm":   "pointer",
    "pinch":       "blank",
}

# ---------------------------------------------------------------------------
# Key parsing
# ---------------------------------------------------------------------------

def _parse_shortcut(shortcut: str) -> tuple[list, object | None]:
    """Parse "RIGHT", "CTRL+L", "CMD+SHIFT+F5" etc. into (modifiers, key)."""
    if not _HAS_PYNPUT:
        return [], None

    _SPECIAL: dict[str, object] = {
        "RIGHT":  _kb.Key.right,
        "LEFT":   _kb.Key.left,
        "UP":     _kb.Key.up,
        "DOWN":   _kb.Key.down,
        "SPACE":  _kb.Key.space,
        "ENTER":  _kb.Key.enter,
        "ESC":    _kb.Key.esc,
        "TAB":    _kb.Key.tab,
        "F5":     _kb.Key.f5,
        "F6":     _kb.Key.f6,
    }
    _MODS: dict[str, object] = {
        "CTRL":  _kb.Key.ctrl,
        "CMD":   _kb.Key.cmd,
        "SHIFT": _kb.Key.shift,
        "ALT":   _kb.Key.alt,
        "WIN":   _kb.Key.cmd,  # treat WIN as CMD on macOS
    }

    mods: list = []
    key = None

    for part in (p.strip().upper() for p in shortcut.split("+")):
        if part in _MODS:
            mods.append(_MODS[part])
        elif part in _SPECIAL:
            key = _SPECIAL[part]
        elif len(part) == 1:
            key = part.lower()

    return mods, key


def _send_shortcut(shortcut: str) -> None:
    """Press a parsed shortcut via pynput, or log if pynput is unavailable."""
    if not _HAS_PYNPUT:
        print(f"[dispatch] (no pynput) would send: {shortcut}")
        return

    mods, key = _parse_shortcut(shortcut)
    if key is None:
        return

    for mod in mods:
        _ctrl.press(mod)
    _ctrl.press(key)
    _ctrl.release(key)
    for mod in reversed(mods):
        _ctrl.release(mod)


# ---------------------------------------------------------------------------
# Active-window gating (macOS only, cached)
# ---------------------------------------------------------------------------

def _frontmost_app(timeout: float = 0.05) -> str:
    """Return the frontmost macOS application name, or '' on failure."""
    try:
        result = subprocess.run(
            [
                "osascript", "-e",
                'tell application "System Events" to get name of '
                'first application process whose frontmost is true',
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class Dispatcher:
    """Translates confirmed gestures into key presses.

    States:
        active — gestures map to key events (default)
        paused — fist toggled; other gestures are suppressed
    """

    _WINDOW_POLL_INTERVAL = 1.0  # seconds between active-app checks

    def __init__(self, profile: dict, gate_window: bool = True) -> None:
        self._shortcuts: dict[str, str] = profile.get("shortcuts", {})
        self._app_name: str = profile.get("app", "")
        self._gate = gate_window
        self._state: Literal["active", "paused"] = "active"
        self._last_poll = 0.0
        self._window_ok = True  # optimistic until first poll

    @property
    def state(self) -> Literal["active", "paused"]:
        return self._state

    def _target_focused(self) -> bool:
        """Return True when the target app is the frontmost window."""
        if not self._gate or not self._app_name:
            return True
        now = time.monotonic()
        if now - self._last_poll >= self._WINDOW_POLL_INTERVAL:
            active = _frontmost_app()
            self._window_ok = self._app_name.lower() in active.lower()
            self._last_poll = now
        return self._window_ok

    def dispatch(self, gesture: str) -> str | None:
        """Process a confirmed gesture.

        Returns the action name that was fired, or None.

        Fist always toggles the paused/active state (no key sent).
        All other gestures require the target app to be focused.
        """
        if gesture == "fist":
            self._state = "paused" if self._state == "active" else "active"
            print(f"[dispatcher] state → {self._state}")
            return "pause_toggle"

        if self._state == "paused":
            return None

        if not self._target_focused():
            return None

        action = _GESTURE_TO_ACTION.get(gesture)
        if action is None:
            return None

        shortcut = self._shortcuts.get(action)
        if shortcut is None:
            return None

        _send_shortcut(shortcut)
        print(f"[dispatcher] {gesture} → {action} → {shortcut}")
        return action
