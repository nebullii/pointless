"""Basic gesture rule tests using a mock landmark object."""

from __future__ import annotations

from types import SimpleNamespace

from gestures.rules import classify, extract_features


def _make_landmarks(finger_states: dict, wrist_xy=(0.5, 0.7), pinch_close=False):
    """
    Build a mock MediaPipe hand landmark object.

    finger_states: dict with keys index/middle/ring/pinky → True (extended).
    Hand scale (wrist → index_mcp) ≈ 0.15 in these coords.
    """
    all_up = finger_states  # alias for readability

    base = {
        0:  (wrist_xy[0],        wrist_xy[1]),          # WRIST
        4:  (wrist_xy[0] - 0.12, wrist_xy[1] - 0.10)   # THUMB_TIP (open)
            if not pinch_close
            else (wrist_xy[0] + 0.01, wrist_xy[1] - 0.13),  # pinch: near index
        5:  (wrist_xy[0],        wrist_xy[1] - 0.15),   # INDEX_MCP
        6:  (wrist_xy[0],        wrist_xy[1] - 0.22),   # INDEX_PIP
        8:  (wrist_xy[0],        wrist_xy[1] - 0.30     # INDEX_TIP
             if all_up.get("index", True) else wrist_xy[1] - 0.15),
        10: (wrist_xy[0] + 0.02, wrist_xy[1] - 0.23),  # MIDDLE_PIP
        12: (wrist_xy[0] + 0.02, wrist_xy[1] - 0.33    # MIDDLE_TIP
             if all_up.get("middle", True) else wrist_xy[1] - 0.20),
        14: (wrist_xy[0] + 0.04, wrist_xy[1] - 0.22),  # RING_PIP
        16: (wrist_xy[0] + 0.04, wrist_xy[1] - 0.30    # RING_TIP
             if all_up.get("ring", True) else wrist_xy[1] - 0.19),
        18: (wrist_xy[0] + 0.06, wrist_xy[1] - 0.18),  # PINKY_PIP
        20: (wrist_xy[0] + 0.06, wrist_xy[1] - 0.26    # PINKY_TIP
             if all_up.get("pinky", True) else wrist_xy[1] - 0.15),
    }
    if pinch_close:
        base[8] = (wrist_xy[0] - 0.01, wrist_xy[1] - 0.13)  # index near thumb; dist ≈ 0.02

    full = []
    for i in range(21):
        if i in base:
            full.append(SimpleNamespace(x=base[i][0], y=base[i][1], z=0.0))
        else:
            full.append(SimpleNamespace(x=wrist_xy[0], y=wrist_xy[1], z=0.0))

    return SimpleNamespace(landmark=full)


def _swipe_history(start_x: float, end_x: float, n: int = 8):
    """Linearly interpolated wrist positions simulating a horizontal swipe."""
    return [(start_x + (end_x - start_x) * i / (n - 1), 0.5) for i in range(n)]


# ---------------------------------------------------------------------------
# extract_features
# ---------------------------------------------------------------------------

def test_features_open_palm():
    lm = _make_landmarks({"index": True, "middle": True, "ring": True, "pinky": True})
    assert extract_features(lm)["fingers_up"] == 4


def test_features_fist():
    lm = _make_landmarks({"index": False, "middle": False, "ring": False, "pinky": False})
    assert extract_features(lm)["fingers_up"] == 0


# ---------------------------------------------------------------------------
# classify — static
# ---------------------------------------------------------------------------

def test_open_palm():
    lm = _make_landmarks({"index": True, "middle": True, "ring": True, "pinky": True})
    gesture, conf = classify(lm, [])
    assert gesture == "open_palm" and conf >= 0.75


def test_fist():
    lm = _make_landmarks({"index": False, "middle": False, "ring": False, "pinky": False})
    gesture, conf = classify(lm, [])
    assert gesture == "fist" and conf >= 0.75


def test_pinch():
    lm = _make_landmarks(
        {"index": False, "middle": False, "ring": False, "pinky": False},
        pinch_close=True,
    )
    gesture, conf = classify(lm, [])
    assert gesture == "pinch" and conf >= 0.75


# ---------------------------------------------------------------------------
# classify — swipe (hand_scale ≈ 0.15, threshold at norm_dx > 2.0)
# ---------------------------------------------------------------------------

def test_swipe_right():
    # dx ≈ 0.35, norm_dx ≈ 0.35/0.15 ≈ 2.3 → fires
    lm = _make_landmarks({"index": True, "middle": False, "ring": False, "pinky": False})
    gesture, conf = classify(lm, _swipe_history(0.3, 0.65))
    assert gesture == "swipe_right"


def test_swipe_left():
    lm = _make_landmarks({"index": True, "middle": False, "ring": False, "pinky": False})
    gesture, conf = classify(lm, _swipe_history(0.65, 0.3))
    assert gesture == "swipe_left"


def test_no_gesture_short_history():
    lm = _make_landmarks({"index": True, "middle": False, "ring": False, "pinky": False})
    gesture, _ = classify(lm, [(0.5, 0.5)])  # only 1 frame → no swipe
    assert gesture is None
