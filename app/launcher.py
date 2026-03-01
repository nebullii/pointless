"""Presentation file selection and launch helpers."""

import platform
import subprocess
import time
from pathlib import Path
from typing import Optional

# Supported presentation file types
_FILETYPES = [
    ("Presentation files", "*.pptx *.ppt *.key *.odp *.pdf"),
    ("PowerPoint", "*.pptx *.ppt"),
    ("Keynote", "*.key"),
    ("All files", "*.*"),
]


def pick_file() -> Optional[str]:
    """
    Open a native OS file-picker dialog and return the chosen path,
    or None if the user cancelled.
    Uses tkinter, which ships with standard Python.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()          # hide the empty root window
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Select presentation file",
            filetypes=_FILETYPES,
        )
        root.destroy()
        return path or None
    except Exception as exc:
        print(f"[launcher] file picker failed: {exc}")
        return None


def open_presentation(filepath: str, wait: float = 3.0) -> None:
    """
    Open *filepath* with the default OS application (PowerPoint, Keynote, …)
    and wait *wait* seconds for the app to become the frontmost window.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Presentation not found: {filepath}")

    os_name = platform.system()
    print(f"[launcher] Opening '{path.name}' …")

    if os_name == "Darwin":
        subprocess.Popen(["open", str(path)])
    elif os_name == "Windows":
        import os
        os.startfile(str(path))   # type: ignore[attr-defined]
    else:
        # Linux / other POSIX
        subprocess.Popen(["xdg-open", str(path)])

    print(f"[launcher] Waiting {wait}s for presentation app to load …")
    time.sleep(wait)
    print("[launcher] Ready – starting gesture control.")
