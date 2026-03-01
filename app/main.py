"""Pointless — hand-gesture control for presentations.

Usage
-----
  python -m app.main                        # launch with default profile
  python -m app.main --file slides.pptx     # open a specific file
  python -m app.main -p keynote_mac         # use a specific profile
  python -m app.main --no-gate              # disable app-running check

Gestures
--------
  Swipe RIGHT  →  next slide
  Swipe LEFT   →  prev slide
  Pinch OPEN   →  zoom in
  Pinch CLOSE  →  zoom out
  Q in preview →  quit
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

from actions.dispatcher import Dispatcher
from actions.profiles import load_profile
from core.config import Settings
from gestures.engine import create_engine, process_frame
from vision.tracker import create_tracker, track_hands, draw_hands

_FONT = cv2.FONT_HERSHEY_SIMPLEX


def _make_camera_nonactivating(title: str) -> None:
    """Use PyObjC to stop the camera window from stealing keyboard focus.

    Sets the window level to floating and prevents it from becoming the
    key window, so the presentation app retains keyboard focus.
    """
    try:
        from AppKit import NSApp, NSFloatingWindowLevel  # type: ignore
        app = NSApp()
        if app is None:
            return
        for win in app.windows():
            if win.title() == title:
                win.setLevel_(NSFloatingWindowLevel)
                win.setHidesOnDeactivate_(False)
                # Resign key so the presentation app keeps keyboard focus
                if win.isKeyWindow():
                    win.resignKeyWindow()
                break
    except Exception:
        pass  # PyObjC not available — window may steal focus, but app still works


def _draw_hud(
    frame,
    last_gesture: str | None,
    last_action: str | None,
    no_hand: bool,
) -> None:
    if no_hand:
        cv2.putText(frame, "no hand", (10, 30), _FONT, 0.6, (120, 120, 120), 1)
    elif last_gesture:
        line = last_gesture if last_action is None else f"{last_gesture} -> {last_action}"
        cv2.putText(frame, line, (10, 30), _FONT, 0.7, (0, 255, 80), 2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Pointless gesture controller")
    parser.add_argument("--profile", "-p", help="Profile name (overrides config)")
    parser.add_argument("--no-gate", action="store_true", help="Disable app-running check")
    parser.add_argument("--camera", "-c", type=int, default=0, help="Camera index")
    args = parser.parse_args()

    settings = Settings()
    if args.profile:
        settings.profile = args.profile

    print(f"Pointless starting. profile={settings.profile}")

    profile = load_profile(settings.profile)
    tracker = create_tracker()
    engine = create_engine()
    dispatcher = Dispatcher(profile, gate_window=not args.no_gate)

    # Open camera
    cap = cv2.VideoCapture(args.camera or settings.camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    # Create window: always-on-top + non-activating so the presentation
    # app keeps keyboard focus (same approach as Zesture).
    cv2.namedWindow("Pointless", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Pointless", cv2.WND_PROP_TOPMOST, 1)
    _make_camera_nonactivating("Pointless")

    last_gesture: str | None = None
    last_action: str | None = None

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            # Mirror the frame so gestures match user's perspective
            frame = cv2.flip(frame, 1)

            hands = track_hands(frame, tracker)

            if hands:
                hand = hands[0]
                draw_hands(frame, hands)
                gesture = process_frame(engine, hand["landmarks"])
                if gesture:
                    last_gesture = gesture
                    last_action = dispatcher.dispatch(gesture)
                    print(f"[main] gesture={gesture} action={last_action}")

            _draw_hud(frame, last_gesture, last_action, no_hand=not hands)

            cv2.imshow("Pointless", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
