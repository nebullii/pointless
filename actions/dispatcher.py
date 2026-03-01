"""Dispatch gestures to keyboard shortcuts.

On macOS, uses AppleScript via System Events for reliable keystroke delivery
to the target application.  On other platforms, uses pyautogui.
"""

import platform
import subprocess
import time
from typing import Optional

_IS_MAC = platform.system() == "Darwin"

# Map gesture names -> profile shortcut keys
_GESTURE_TO_SHORTCUT_KEY = {
    "next_slide": "next",
    "prev_slide": "prev",
    "zoom_in": "zoom_in",
    "zoom_out": "zoom_out",
}

# ---- macOS AppleScript approach ----
# Map human-readable key names to AppleScript key codes
_APPLESCRIPT_KEY_CODES = {
    "right":  124,
    "left":   123,
    "up":     126,
    "down":   125,
    "return": 36,
    "escape": 53,
    "space":  49,
    "tab":    48,
}


def _applescript_keystroke(shortcut: str, app_name: str) -> None:
    """
    Send *shortcut* to *app_name* using AppleScript + System Events.

    Handles:
    - Single character keys  ("b" -> keystroke "b")
    - Named keys             ("right" -> key code 124)
    - Modifier combos        ("command+equal" -> keystroke "=" using {command down})
    """
    parts = [p.strip().lower() for p in shortcut.split("+")]
    key = parts[-1]                 # last part is the actual key
    modifiers = parts[:-1]          # everything before is a modifier

    # Build modifier clause
    mod_map = {
        "command": "command down",
        "cmd":     "command down",
        "ctrl":    "control down",
        "control": "control down",
        "shift":   "shift down",
        "alt":     "option down",
        "option":  "option down",
    }
    using_parts = [mod_map[m] for m in modifiers if m in mod_map]
    using_clause = ""
    if using_parts:
        using_clause = " using {" + ", ".join(using_parts) + "}"

    # Decide between 'keystroke' (character) and 'key code' (special keys)
    key_code = _APPLESCRIPT_KEY_CODES.get(key)
    # Also map common names to their character equivalents
    char_map = {"equal": "=", "minus": "-", "plus": "+"}
    char = char_map.get(key, key if len(key) == 1 else None)

    if key_code is not None:
        action = f"key code {key_code}{using_clause}"
    elif char is not None:
        action = f'keystroke "{char}"{using_clause}'
    else:
        # Fallback: try as keystroke
        action = f'keystroke "{key}"{using_clause}'

    script = (
        f'tell application "{app_name}" to activate\n'
        f'delay 0.1\n'
        f'tell application "System Events"\n'
        f'    {action}\n'
        f'end tell'
    )
    subprocess.Popen(
        ["osascript", "-e", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ---- pyautogui fallback (Windows / Linux) ----
def _pyautogui_keystroke(shortcut: str) -> None:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.0

    _KEY_ALIASES = {
        "command": "command", "cmd": "command",
        "ctrl": "ctrl", "control": "ctrl",
        "shift": "shift",
        "alt": "alt", "option": "alt",
        "equal": "=", "minus": "-", "plus": "+",
    }
    parts = [
        _KEY_ALIASES.get(p.strip().lower(), p.strip().lower())
        for p in shortcut.split("+")
    ]
    if len(parts) == 1:
        pyautogui.press(parts[0])
    else:
        pyautogui.hotkey(*parts)


def dispatch(gesture: str, profile: dict) -> Optional[str]:
    """
    Look up *gesture* in *profile* shortcuts and fire the keystroke.

    Returns the shortcut string that was sent, or ``None`` if the gesture
    has no mapping in the profile.
    """
    shortcut_key = _GESTURE_TO_SHORTCUT_KEY.get(gesture)
    if not shortcut_key:
        return None

    shortcut = profile.get("shortcuts", {}).get(shortcut_key)
    if not shortcut:
        return None

    app_name = profile.get("app", "")

    if _IS_MAC and app_name:
        _applescript_keystroke(shortcut, app_name)
    else:
        _pyautogui_keystroke(shortcut)

    return shortcut
