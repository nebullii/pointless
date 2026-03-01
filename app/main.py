"""Pointless entrypoint."""

import cv2

from actions.dispatcher import Dispatcher
from actions.profiles import load_profile
from core.config import Settings
from gestures.engine import GestureEngine
from vision.capture import open_camera
from vision.tracker import HandTracker

_FONT = cv2.FONT_HERSHEY_SIMPLEX

# Hand skeleton connections (MediaPipe 21-landmark layout)
_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),           # index
    (0, 9), (9, 10), (10, 11), (11, 12),      # middle
    (0, 13), (13, 14), (14, 15), (15, 16),    # ring
    (0, 17), (17, 18), (18, 19), (19, 20),    # pinky
    (5, 9), (9, 13), (13, 17),                # palm arch
]


def _draw_hand(frame, hand_lm) -> None:
    h, w = frame.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand_lm.landmark]
    for a, b in _CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], (255, 80, 0), 2)
    for pt in pts:
        cv2.circle(frame, pt, 4, (0, 255, 0), -1)


def _draw_hud(
    frame,
    state: str,
    last_gesture: str | None,
    last_action: str | None,
    no_hand: bool,
) -> None:
    state_color = (0, 200, 255) if state == "active" else (60, 60, 200)
    cv2.putText(frame, state.upper(), (10, 30), _FONT, 0.7, state_color, 2)

    if no_hand:
        cv2.putText(frame, "no hand", (10, 60), _FONT, 0.6, (120, 120, 120), 1)
    elif last_gesture:
        line = last_gesture if last_action is None else f"{last_gesture} → {last_action}"
        cv2.putText(frame, line, (10, 60), _FONT, 0.7, (0, 255, 80), 2)


def main() -> int:
    settings = Settings()
    print(f"Pointless starting. profile={settings.profile}")

    profile = load_profile(settings.profile)
    cap = open_camera(settings.camera_index)
    tracker = HandTracker()
    engine = GestureEngine()
    dispatcher = Dispatcher(profile)

    last_gesture: str | None = None
    last_action: str | None = None

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            landmarks = tracker.track(frame)

            if landmarks:
                hand_lm = landmarks[0]
                _draw_hand(frame, hand_lm)
                gesture, _conf = engine.update(hand_lm)
                if gesture:
                    last_gesture = gesture
                    last_action = dispatcher.dispatch(gesture)
            else:
                engine.reset()

            _draw_hud(frame, dispatcher.state, last_gesture, last_action, no_hand=not landmarks)

            cv2.imshow("Pointless (dev)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
