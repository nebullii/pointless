"""Rule-based gesture classifier."""

from __future__ import annotations

import math

# MediaPipe hand landmark indices
_WRIST = 0
_THUMB_TIP = 4
_INDEX_MCP = 5
_INDEX_PIP = 6
_INDEX_TIP = 8
_MIDDLE_PIP = 10
_MIDDLE_TIP = 12
_RING_PIP = 14
_RING_TIP = 16
_PINKY_PIP = 18
_PINKY_TIP = 20

# (tip_idx, pip_idx) pairs for the four non-thumb fingers
_FINGERS = [
    (_INDEX_TIP, _INDEX_PIP),
    (_MIDDLE_TIP, _MIDDLE_PIP),
    (_RING_TIP, _RING_PIP),
    (_PINKY_TIP, _PINKY_PIP),
]


def _xy(landmarks, idx: int) -> tuple[float, float]:
    lm = landmarks.landmark[idx]
    return lm.x, lm.y


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def extract_features(landmarks) -> dict:
    """Extract scalar features from a single frame's hand landmarks.

    All distances are normalized by hand scale (wrist → index MCP),
    so they are robust to the hand being close or far from the camera.
    """
    fingers_up = sum(
        1
        for tip, pip in _FINGERS
        if landmarks.landmark[tip].y < landmarks.landmark[pip].y
    )

    wrist = _xy(landmarks, _WRIST)
    index_mcp = _xy(landmarks, _INDEX_MCP)
    hand_scale = _dist(wrist, index_mcp) or 1e-6

    thumb_tip = _xy(landmarks, _THUMB_TIP)
    index_tip = _xy(landmarks, _INDEX_TIP)
    pinch_dist_norm = _dist(thumb_tip, index_tip) / hand_scale

    return {
        "fingers_up": fingers_up,
        "pinch_dist_norm": pinch_dist_norm,
        "wrist_x": wrist[0],
        "wrist_y": wrist[1],
        "hand_scale": hand_scale,
    }


def classify(
    landmarks,
    pos_history: list[tuple[float, float]],
) -> tuple[str | None, float]:
    """Classify a gesture from the current frame and recent wrist-position history.

    Args:
        landmarks: MediaPipe hand landmarks for one hand.
        pos_history: List of (wrist_x, wrist_y) tuples, newest last.

    Returns:
        (gesture_name, confidence) or (None, 0.0).
    """
    f = extract_features(landmarks)

    # --- Static gestures ---

    # Pinch checked first: thumb+index close overrides fist (both have fingers_up == 0)
    if f["pinch_dist_norm"] < 0.5 and f["fingers_up"] <= 1:
        return "pinch", 0.85

    # Fist: no fingers extended (and not a pinch)
    if f["fingers_up"] == 0:
        return "fist", 0.9

    # Open palm: all four fingers extended
    if f["fingers_up"] == 4:
        return "open_palm", 0.9

    # --- Dynamic gestures: swipe (needs position history) ---
    if len(pos_history) >= 8:
        recent = pos_history[-8:]
        dx = recent[-1][0] - recent[0][0]
        dy = recent[-1][1] - recent[0][1]

        # Movement must be predominantly horizontal
        if abs(dx) > abs(dy) * 1.5:
            norm_dx = dx / f["hand_scale"]
            if norm_dx > 2.0:
                return "swipe_right", min(abs(norm_dx) / 4.0, 1.0)
            if norm_dx < -2.0:
                return "swipe_left", min(abs(norm_dx) / 4.0, 1.0)

    return None, 0.0
