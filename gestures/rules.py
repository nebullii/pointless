"""Rule-based gesture classifier.

Supported gestures
------------------
next_slide  — wrist moves right with all 5 fingers extended
prev_slide  — wrist moves left  with all 5 fingers extended
zoom_in     — thumb-index distance increases (pinch open)
zoom_out    — thumb-index distance decreases (pinch close)
fist        — all 4 non-thumb fingers curled
"""

from __future__ import annotations

import math
from collections import deque
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------
WAVE_WINDOW     = 10    # frames used for swipe detection
WAVE_THRESHOLD  = 0.10  # normalised x-displacement to trigger a swipe
WAVE_CONF_SCALE = 0.22  # x-displacement that maps to 100 % confidence

PINCH_WINDOW     = 10
PINCH_THRESHOLD  = 0.05
PINCH_CONF_SCALE = 0.12

# Minimum fingers that must be extended for a swipe to be valid
MIN_EXTENDED_FOR_SWIPE = 4   # out of 5 (thumb extension is unreliable sideways)

# ---------------------------------------------------------------------------
# MediaPipe landmark indices
# ---------------------------------------------------------------------------
WRIST     = 0
THUMB_TIP = 4
THUMB_MCP = 2
INDEX_TIP = 8

# Non-thumb fingers: (tip_index, pip_index, mcp_index)
_FINGERS = [
    (8,  6,  5),   # index
    (12, 10, 9),   # middle
    (16, 14, 13),  # ring
    (20, 18, 17),  # pinky
]


def _dist(p1, p2) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


# Tip must be this many times farther than MCP to count as "extended" (strict — for swipe gate)
_EXTENDED_THRESH = 1.8
# Tip must be within this multiple of MCP distance to count as "curled" (lenient — for fist)
_FIST_THRESH = 1.5


def _extended_count(landmarks: list) -> int:
    """Count how many of the 5 fingers are clearly extended.

    Orientation-invariant: uses wrist→tip vs wrist→MCP distance ratio.
    Uses a strict threshold so only clearly open hands qualify for swipe.
    """
    wrist = landmarks[WRIST]
    count = 0
    for tip, _, mcp in _FINGERS:
        if _dist(landmarks[tip], wrist) > _dist(landmarks[mcp], wrist) * _EXTENDED_THRESH:
            count += 1
    if _dist(landmarks[THUMB_TIP], wrist) > _dist(landmarks[THUMB_MCP], wrist) * _EXTENDED_THRESH:
        count += 1
    return count


def _is_fist(landmarks: list) -> bool:
    """Return True when all 4 non-thumb fingers are curled.

    Uses a lenient threshold so closing the hand reliably triggers fist detection.
    """
    wrist = landmarks[WRIST]
    for tip, _, mcp in _FINGERS:
        if _dist(landmarks[tip], wrist) > _dist(landmarks[mcp], wrist) * _FIST_THRESH:
            return False
    return True


def classify(
    landmarks: list,
    history: deque,
) -> Tuple[Optional[str], float]:
    """Classify a gesture from current *landmarks* and running *history*.

    Returns ``(gesture_name, confidence)`` or ``(None, 0.0)``.
    """
    if not landmarks:
        return None, 0.0

    wrist = landmarks[WRIST]
    pinch_dist = _dist(landmarks[THUMB_TIP], landmarks[INDEX_TIP])

    history.append({"wrist_x": wrist[0], "pinch_dist": pinch_dist})

    # ------------------------------------------------------------------
    # Fist — detected immediately, no history needed
    # ------------------------------------------------------------------
    if _is_fist(landmarks):
        return "fist", 1.0

    if len(history) < WAVE_WINDOW:
        return None, 0.0

    frames = list(history)

    # ------------------------------------------------------------------
    # Swipe — only valid with 5 fingers extended
    # ------------------------------------------------------------------
    if _extended_count(landmarks) >= MIN_EXTENDED_FOR_SWIPE:
        wave_frames = frames[-WAVE_WINDOW:]
        x_delta = wave_frames[-1]["wrist_x"] - wave_frames[0]["wrist_x"]

        if x_delta > WAVE_THRESHOLD:
            conf = min(1.0, abs(x_delta) / WAVE_CONF_SCALE)
            return "next_slide", conf

        if x_delta < -WAVE_THRESHOLD:
            conf = min(1.0, abs(x_delta) / WAVE_CONF_SCALE)
            return "prev_slide", conf

    # ------------------------------------------------------------------
    # Pinch zoom
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
