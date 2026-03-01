"""OpenCV overlay HUD drawn onto the live preview frame."""

import cv2

_FONT = cv2.FONT_HERSHEY_SIMPLEX

_GESTURE_COLOURS = {
    "NEXT SLIDE": (0, 200, 255),    # amber
    "PREV SLIDE": (255, 180, 0),    # blue-ish
    "ZOOM IN":   (0, 255, 120),     # green
    "ZOOM OUT":  (80, 80, 255),     # red
}

_HELP_LINES = [
    "Wave  LEFT  →  Next slide",
    "Wave  RIGHT →  Prev slide",
    "Pinch OPEN  →  Zoom in",
    "Pinch CLOSE →  Zoom out",
    "Press  Q    →  Quit",
]


def draw_overlay(frame, gesture: str | None, fps: float, filename: str = ""):
    """
    Render the HUD onto *frame* in-place and return it.

    Draws:
    * FPS counter (top-left)
    * Presentation filename (top-right, truncated to 40 chars)
    * Gesture label when a gesture is active (bottom-centre, large)
    * Static help bar (bottom-left)
    """
    h, w = frame.shape[:2]

    # ---- FPS counter -------------------------------------------------------
    cv2.putText(
        frame, f"FPS: {fps:.1f}",
        (10, 32), _FONT, 0.75, (0, 255, 0), 2, cv2.LINE_AA,
    )

    # ---- Filename (top-right) ---------------------------------------------
    if filename:
        label = filename if len(filename) <= 40 else "…" + filename[-39:]
        (tw, _), _ = cv2.getTextSize(label, _FONT, 0.6, 1)
        cv2.rectangle(frame, (w - tw - 16, 6), (w, 36), (0, 0, 0), -1)
        cv2.putText(
            frame, label,
            (w - tw - 8, 28), _FONT, 0.6, (180, 220, 255), 1, cv2.LINE_AA,
        )

    # ---- Active gesture label ----------------------------------------------
    if gesture:
        label = gesture.replace("_", " ").upper()
        colour = _GESTURE_COLOURS.get(label, (255, 255, 255))
        (tw, th), _ = cv2.getTextSize(label, _FONT, 1.4, 3)
        tx = max(0, (w - tw) // 2)
        ty = h - 50
        cv2.rectangle(frame, (tx - 10, ty - th - 8), (tx + tw + 10, ty + 8), (0, 0, 0), -1)
        cv2.putText(frame, label, (tx, ty), _FONT, 1.4, colour, 3, cv2.LINE_AA)

    # ---- Help bar ----------------------------------------------------------
    bar_y_start = h - len(_HELP_LINES) * 22 - 10
    cv2.rectangle(frame, (0, bar_y_start - 6), (280, h), (0, 0, 0, 160), -1)
    for i, line in enumerate(_HELP_LINES):
        cv2.putText(
            frame, line,
            (6, bar_y_start + i * 22), _FONT, 0.50, (200, 200, 200), 1, cv2.LINE_AA,
        )

    return frame


def show_status(text: str):
    """Legacy stub – kept for backward compatibility."""
    return None
