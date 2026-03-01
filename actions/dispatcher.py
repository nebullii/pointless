"""Gesture → key-event dispatcher with state machine and active-window gating."""

from __future__ import annotations

import subprocess
import time
from typing import Literal

try:
    from pynput.keyboard import Key, Controller as _KbController, KeyCode
    _kb = _KbController()
    _PYNPUT_OK = True
except Exception:
    _PYNPUT_OK = False

# Gesture → profile shortcut-key name
_GESTURE_TO_ACTION: dict[str, str] = {
    "next_slide": "next",
    "prev_slide": "prev",
    "zoom_in":    "zoom_in",
    "zoom_out":   "zoom_out",
}

# ---------------------------------------------------------------------------
# pynput key mapping
# ---------------------------------------------------------------------------

_PYNPUT_KEYS: dict[str, Key] = {
    "RIGHT": Key.right,
    "LEFT":  Key.left,
    "UP":    Key.up,
    "DOWN":  Key.down,
    "SPACE": Key.space,
    "ENTER": Key.enter,
    "ESC":   Key.esc,
    "TAB":   Key.tab,
    "F5":    Key.f5,
    "F6":    Key.f6,
}

_PYNPUT_MODS: dict[str, Key] = {
    "CMD":   Key.cmd,
    "CTRL":  Key.ctrl,
    "SHIFT": Key.shift,
    "ALT":   Key.alt,
    "WIN":   Key.cmd,
}

# ---------------------------------------------------------------------------
# AppleScript helper (for native app actions only — no Accessibility needed)
# ---------------------------------------------------------------------------

def _run_applescript(script: str) -> str | None:
    """Run an AppleScript snippet. Returns stderr if it failed, else None."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return result.stderr.strip()
        return None
    except Exception as exc:
        return str(exc)


def _send_applescript_action(script: str) -> None:
    """Execute a native AppleScript action from the profile."""
    err = _run_applescript(script)
    if err:
        if "-1728" in err:
            print("[dispatcher] ERROR: PowerPoint slideshow not running — press F5 in PowerPoint first.")
        else:
            print(f"[dispatcher] AppleScript error: {err}")


# ---------------------------------------------------------------------------
# pynput keystroke sender (Zesture-style global input simulation)
# ---------------------------------------------------------------------------

def _send_pynput(shortcut: str) -> bool:
    """Send a keystroke via pynput. Returns False if pynput unavailable."""
    if not _PYNPUT_OK:
        return False

    parts = [p.strip().upper() for p in shortcut.split("+")]
    mods = [_PYNPUT_MODS[p] for p in parts if p in _PYNPUT_MODS]
    key_str = next((p for p in parts if p not in _PYNPUT_MODS), None)
    if key_str is None:
        return False

    key = _PYNPUT_KEYS.get(key_str) or KeyCode.from_char(key_str.lower())

    try:
        for mod in mods:
            _kb.press(mod)
        _kb.press(key)
        _kb.release(key)
        for mod in reversed(mods):
            _kb.release(mod)
        return True
    except Exception as exc:
        print(f"[dispatcher] pynput error: {exc}")
        print("[dispatcher] Hint: grant Accessibility permission to Terminal in")
        print("             System Settings → Privacy & Security → Accessibility")
        return False


# ---------------------------------------------------------------------------
# Active-app gating (macOS only, cached)
# ---------------------------------------------------------------------------

def _app_is_running(app_name: str, timeout: float = 0.3) -> bool:
    script = f'tell application "System Events" to (name of processes) contains "{app_name}"'
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout,
        )
        return "true" in result.stdout.strip().lower()
    except Exception:
        return True


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class Dispatcher:
    """Translates confirmed gestures into key presses.

    Profile keys:
        app                  — target application name (for gating)
        applescript_actions  — action → raw AppleScript (no Accessibility needed)
        shortcuts            — action → shortcut string (uses pynput, needs Accessibility)
    """

    _WINDOW_POLL_INTERVAL = 2.0

    def __init__(self, profile: dict, gate_window: bool = True) -> None:
        self._shortcuts: dict[str, str] = profile.get("shortcuts", {})
        self._applescript_actions: dict[str, str] = profile.get("applescript_actions", {})
        self._app_name: str = profile.get("app", "")
        self._gate = gate_window
        self._state: Literal["active", "paused"] = "active"
        self._last_poll = 0.0
        self._window_ok = True

    @property
    def state(self) -> Literal["active", "paused"]:
        return self._state

    def _target_running(self) -> bool:
        if not self._gate or not self._app_name:
            return True
        now = time.monotonic()
        if now - self._last_poll >= self._WINDOW_POLL_INTERVAL:
            self._window_ok = _app_is_running(self._app_name)
            self._last_poll = now
        return self._window_ok

    def dispatch(self, gesture: str) -> str | None:
        """Process a confirmed gesture. Returns the action name fired, or None."""
        if gesture == "fist":
            self._state = "paused" if self._state == "active" else "active"
            print(f"[dispatcher] state → {self._state}")
            return "pause_toggle"

        if self._state == "paused":
            return None

        if not self._target_running():
            return None

        action = _GESTURE_TO_ACTION.get(gesture)
        if action is None:
            return None

        # 1. Native AppleScript (no Accessibility permission needed)
        script = self._applescript_actions.get(action)
        if script:
            _send_applescript_action(script)
            print(f"[dispatcher] {gesture} → {action} (native AppleScript)")
            return action

        # 2. pynput global keystroke (Accessibility permission needed)
        shortcut = self._shortcuts.get(action)
        if shortcut:
            ok = _send_pynput(shortcut)
            if ok:
                print(f"[dispatcher] {gesture} → {action} → {shortcut} (pynput)")
            return action

        return None
