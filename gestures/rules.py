"""Rule-based gesture classifier."""

import math
from collections import deque
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Gesture tuning constants
# ---------------------------------------------------------------------------
WAVE_WINDOW = 10          # frames used for wave detection
WAVE_THRESHOLD = 0.10     # normalised x-displacement to trigger a wave
WAVE_CONF_SCALE = 0.22    # x-displacement that maps to 100 % confidence

PINCH_WINDOW = 10         # frames used for pinch detection
PINCH_THRESHOLD = 0.05    # normalised distance change to trigger pinch
PINCH_CONF_SCALE = 0.12   # distance change that maps to 100 % confidence

# MediaPipe landmark indices
WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8


def _dist(p1, p2) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def classify(
    landmarks: list,
    history: deque,
) -> Tuple[Optional[str], float]:
    """
    Classify a gesture from the current *landmarks* and running *history*.

    Returns ``(gesture_name, confidence)`` where confidence is in [0, 1],
    or ``(None, 0.0)`` when no gesture is detected.

    Supported gestures
    ------------------
    next_slide  - wave left  (from camera's POV: wrist x increases)
    prev_slide  - wave right (from camera's POV: wrist x decreases)
    zoom_in     - pinch open  (thumb-index distance increases)
    zoom_out    - pinch close (thumb-index distance decreases)
    """
    if not landmarks:
        return None, 0.0

    wrist = landmarks[WRIST]
    pinch_dist = _dist(landmarks[THUMB_TIP], landmarks[INDEX_TIP])

    history.append({"wrist_x": wrist[0], "pinch_dist": pinch_dist})

    if len(history) < WAVE_WINDOW:
        return None, 0.0

    frames = list(history)

    # ------------------------------------------------------------------
    # Wave detection - compare oldest vs newest wrist x in the window
    # ------------------------------------------------------------------
    wave_frames = frames[-WAVE_WINDOW:]
    x_delta = wave_frames[-1]["wrist_x"] - wave_frames[0]["wrist_x"]

    # Camera is NOT mirrored:
    #   Physically waving LEFT  -> x INCREASES (toward camera-right)
    #   Physically waving RIGHT -> x DECREASES (toward camera-left)
    if x_delta > WAVE_THRESHOLD:
        conf = min(1.0, abs(x_delta) / WAVE_CONF_SCALE)
        return "next_slide", conf

    if x_delta < -WAVE_THRESHOLD:
        conf = min(1.0, abs(x_delta) / WAVE_CONF_SCALE)
        return "prev_slide", conf

    # ------------------------------------------------------------------
    # Pinch zoom detection
    # ------------------------------------------------------------------
    pinch_frames = frames[-PINCH_WINDOW:]
    d_delta = pinch_frames[-1]["pinch_dist"] - pinch_frames[0]["pinch_dist"]

    if d_delta > PINCH_THRESHOLD:
        conf = min(1.0, abs(d_delta) / PINCH_CONF_SCALE)
        return "zoom_in", conf

    if d_delta < -PINCH_THRESHOLD:
        conf = min(1.0, abs(d_delta) / PINCH_CONF_SCALE)
        return "zoom_out", conf

    return None, 0.0
