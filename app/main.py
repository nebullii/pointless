"""Pointless - hand-gesture control for presentations.

Usage
-----
  python -m app.main                        # file picker opens automatically
  python -m app.main --file slides.pptx     # open a specific file
  python -m app.main --file slides.pptx --profile powerpoint_mac
  python -m app.main --no-open              # presentation is already running

Gestures
--------
  Wave LEFT   ->  next slide
  Wave RIGHT  ->  prev slide
  Pinch OPEN  ->  zoom in
  Pinch CLOSE ->  zoom out
  Q / Esc in preview window -> quit
"""

import argparse
import platform
import time
from pathlib import Path

import cv2

from actions.dispatcher import dispatch
from actions.profiles import load_profile
from app.launcher import open_presentation, pick_file
from core.config import Settings
from gestures.engine import create_engine, process_frame
from ui.overlay import draw_overlay
from vision.capture import open_camera, read_frame, release_camera
from vision.tracker import create_tracker, draw_hands, track_hands


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pointless",
        description="Control a presentation with hand gestures.",
    )
    parser.add_argument(
        "--file", "-f",
        metavar="PATH",
        help=(
            "Path to the presentation file to open (.pptx, .ppt, .key, ...)."
            " If omitted a file-picker dialog will open."
        ),
    )
    parser.add_argument(
        "--profile", "-p",
        metavar="NAME",
        help=(
            "Shortcut profile to use (e.g. powerpoint_mac, keynote_mac)."
            " Auto-detected from OS when omitted."
        ),
    )
    parser.add_argument(
        "--camera", "-c",
        metavar="INDEX",
        type=int,
        default=0,
        help="Camera device index (default: 0).",
    )
    parser.add_argument(
        "--no-overlay",
        action="store_true",
        help="Disable the on-screen HUD.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Skip opening the file (use when the presentation is already running).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print real-time tracking data (wrist x, pinch dist) every frame.",
    )
    return parser.parse_args()


def _auto_profile(profile_arg):
    """Return the profile name to use."""
    if profile_arg:
        return profile_arg
    return "powerpoint_mac" if platform.system() == "Darwin" else "powerpoint_windows"


def main() -> int:
    args = _parse_args()

    settings = Settings(
        profile=_auto_profile(args.profile),
        camera_index=args.camera,
        show_overlay=not args.no_overlay,
        presentation_file=args.file,
    )

    print(f"Pointless starting | OS={platform.system()} | profile={settings.profile}")

    # ---- Resolve presentation file ----------------------------------------
    pptx_path = settings.presentation_file

    if not pptx_path and not args.no_open:
        print("No file specified - opening file picker ...")
        pptx_path = pick_file()
        if not pptx_path:
            print("No file selected. Re-run with --no-open to skip this step.")
            return 1

    if pptx_path and not args.no_open:
        open_presentation(pptx_path)

    # ---- Load profile -------------------------------------------------------
    profile = load_profile(settings.profile)
    print(f"Loaded profile : {profile['name']}")

    # ---- macOS accessibility permission check ------------------------------
    if platform.system() == "Darwin":
        import subprocess
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to keystroke ""'],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(
                "\n" + "=" * 65 + "\n"
                "  ACCESSIBILITY PERMISSION REQUIRED\n"
                "\n"
                "  macOS is blocking keystroke delivery.\n"
                "  To fix this:\n"
                "\n"
                "  1. Open System Settings > Privacy & Security > Accessibility\n"
                "  2. Click the '+' button\n"
                "  3. Add your Terminal app (e.g. Terminal.app or iTerm)\n"
                "  4. Restart this app\n"
                "\n"
                f"  Error: {result.stderr.strip()}\n"
                "=" * 65 + "\n"
            )
            print("Continuing anyway (gestures will be detected but keystrokes won't reach PowerPoint).\n")

    # ---- Camera + tracker ---------------------------------------------------
    print("Opening camera ...")
    cap = open_camera(settings.camera_index)
    tracker = create_tracker(max_hands=1)
    engine = create_engine()

    filename_label = Path(pptx_path).name if pptx_path else ""
    prev_time = time.time()
    active_gesture = None
    gesture_display_until = 0.0

    print("Running - press Q or Esc in the preview window to quit.")

    try:
        while True:
            ok, frame = read_frame(cap)
            if not ok:
                print("Camera read failed - exiting.")
                break

            # ---- Hand tracking --------------------------------------------
            hands = track_hands(frame, tracker)

            # ---- Gesture recognition ------------------------------------
            if hands:
                lms = hands[0]["landmarks"]
                gesture = process_frame(engine, lms)

                if args.debug:
                    from gestures.rules import WRIST, THUMB_TIP, INDEX_TIP, _dist
                    wx = lms[WRIST][0]
                    pd = _dist(lms[THUMB_TIP], lms[INDEX_TIP])
                    hist = engine["history"]
                    hlen = len(hist)
                    print(
                        f"  [dbg] wrist_x={wx:.3f}  pinch={pd:.3f}"
                        f"  hist={hlen}  gesture={gesture}",
                        end="\r",
                    )

                if gesture:
                    sent = dispatch(gesture, profile)
                    print(f"\n>>> GESTURE: {gesture:<12}  key={sent}")
                    active_gesture = gesture
                    gesture_display_until = time.time() + 1.5

            # ---- Drawing / HUD ------------------------------------------
            if settings.show_overlay:
                draw_hands(frame, hands)

            now = time.time()
            fps = 1.0 / max(now - prev_time, 1e-9)
            prev_time = now

            display_gesture = active_gesture if now < gesture_display_until else None
            if settings.show_overlay:
                draw_overlay(frame, display_gesture, fps, filename_label)

            cv2.imshow("Pointless - Gesture Control", frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):   # q, Q, or Esc
                break

    finally:
        release_camera(cap)
        tracker.close()
        cv2.destroyAllWindows()
        print("Pointless stopped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
