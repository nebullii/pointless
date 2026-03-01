"""Open a PowerPoint file and start the slideshow via osascript."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path


def find_pptx(folder: Path | None = None) -> Path | None:
    """Return the most recently modified .pptx/.ppt in folder (default: ~/Downloads)."""
    search_dir = folder or (Path.home() / "Downloads")
    files = sorted(
        [*search_dir.glob("*.pptx"), *search_dir.glob("*.ppt")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


def open_presentation(path: Path) -> None:
    """Open a PowerPoint file in Microsoft PowerPoint."""
    script = (
        f'tell application "Microsoft PowerPoint"\n'
        f'    activate\n'
        f'    open POSIX file "{path}"\n'
        f'end tell'
    )
    subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)


def start_slideshow(load_wait: float = 4.0) -> None:
    """Wait for PowerPoint to load the file, then start the slideshow from slide 1."""
    print(f"Waiting {load_wait}s for PowerPoint to load …")
    time.sleep(load_wait)

    # Primary: AppleScript — simpler form avoids the -10006 error from
    # trying to set 'starting slide' on newer PowerPoint builds.
    script = (
        'tell application "Microsoft PowerPoint"\n'
        '    activate\n'
        '    tell active presentation\n'
        '        run slide show (slide show settings)\n'
        '    end tell\n'
        'end tell'
    )
    result = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)
    if result.returncode == 0:
        return

    # Fallback: send keyboard shortcut directly to the PowerPoint process.
    print(f"[presentation] AppleScript failed ({result.stderr.decode().strip()}), trying keyboard …")
    time.sleep(0.3)
    key_script = (
        'tell application "System Events" to tell application process '
        '"Microsoft PowerPoint" to key code 96'  # F5 = Play from Start
    )
    result2 = subprocess.run(["osascript", "-e", key_script], capture_output=True, timeout=5)
    if result2.returncode != 0:
        print(f"[presentation] slideshow error: {result2.stderr.decode().strip()}")
