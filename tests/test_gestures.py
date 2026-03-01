"""Tests for gesture rules: classify()."""

from __future__ import annotations

from collections import deque

from gestures.rules import classify, WAVE_WINDOW


def _make_landmarks(wrist_x=0.5, wrist_y=0.5, pinch_dist=0.15, fist=False):
    """Build a minimal 21-landmark list with controllable wrist, pinch, and hand shape.

    Uses distance-from-wrist to determine extended vs curled, matching rules.py:
      fist=False → tip is far from wrist (> MCP distance * 1.3) → extended
      fist=True  → tip is close to wrist (< MCP distance * 1.3) → curled
    """
    lms = [(wrist_x, wrist_y, 0.0)] * 21

    # MCP joints sit just above the wrist (same for both states)
    mcp_y = wrist_y - 0.08

    if fist:
        # Tips curl back close to wrist level — dist(wrist,tip) < dist(wrist,mcp)*1.3
        tip_y = wrist_y - 0.05   # barely above wrist, clearly < mcp_dist * 1.3
    else:
        # Tips are fully extended — dist(wrist,tip) >> dist(wrist,mcp)
        tip_y = wrist_y - 0.30

    pip_y = (mcp_y + tip_y) / 2  # PIP sits between MCP and tip

    # Set MCP, PIP, tip for all 4 non-thumb fingers
    for tip_idx, pip_idx, mcp_idx in [(8, 6, 5), (12, 10, 9), (16, 14, 13), (20, 18, 17)]:
        lms[mcp_idx] = (wrist_x, mcp_y, 0.0)
        lms[pip_idx] = (wrist_x, pip_y, 0.0)
        lms[tip_idx] = (wrist_x, tip_y, 0.0)

    # Thumb MCP (2) and tip (4)
    lms[2] = (wrist_x, mcp_y, 0.0)
    lms[4] = (wrist_x - pinch_dist / 2, tip_y, 0.0)
    # Index tip (8) overrides with pinch offset for zoom tests
    lms[8] = (wrist_x + pinch_dist / 2, tip_y, 0.0)

    return lms


# ---------------------------------------------------------------------------
# Wave / swipe detection (requires extended fingers)
# ---------------------------------------------------------------------------

def test_swipe_right():
    history = deque(maxlen=30)
    result = None
    for i in range(WAVE_WINDOW + 2):
        x = 0.3 + i * 0.02  # moving right
        lms = _make_landmarks(wrist_x=x)
        r = classify(lms, history)
        if r[0] is not None:
            result = r
    assert result is not None
    assert result[0] == "next_slide"


def test_swipe_left():
    history = deque(maxlen=30)
    result = None
    for i in range(WAVE_WINDOW + 2):
        x = 0.7 - i * 0.02  # moving left
        lms = _make_landmarks(wrist_x=x)
        r = classify(lms, history)
        if r[0] is not None:
            result = r
    assert result is not None
    assert result[0] == "prev_slide"


def test_no_swipe_stationary():
    history = deque(maxlen=30)
    result = None
    for _ in range(WAVE_WINDOW + 2):
        lms = _make_landmarks(wrist_x=0.5)
        r = classify(lms, history)
        if r[0] is not None:
            result = r
    assert result is None


def test_swipe_blocked_without_extended_fingers():
    """Swipe with a fist (fingers curled) should not produce next/prev_slide."""
    history = deque(maxlen=30)
    results = set()
    for i in range(WAVE_WINDOW + 2):
        x = 0.3 + i * 0.02
        lms = _make_landmarks(wrist_x=x, fist=True)
        gesture, _ = classify(lms, history)
        if gesture:
            results.add(gesture)
    assert "next_slide" not in results
    assert "prev_slide" not in results


# ---------------------------------------------------------------------------
# Pinch / zoom detection
# ---------------------------------------------------------------------------

def test_zoom_in():
    history = deque(maxlen=30)
    result = None
    for i in range(WAVE_WINDOW + 2):
        dist = 0.05 + i * 0.01  # fingers spreading
        lms = _make_landmarks(pinch_dist=dist)
        r = classify(lms, history)
        if r[0] is not None:
            result = r
    assert result is not None
    assert result[0] == "zoom_in"


def test_zoom_out():
    history = deque(maxlen=30)
    result = None
    for i in range(WAVE_WINDOW + 2):
        dist = 0.20 - i * 0.01  # fingers closing
        lms = _make_landmarks(pinch_dist=dist)
        r = classify(lms, history)
        if r[0] is not None:
            result = r
    assert result is not None
    assert result[0] == "zoom_out"


def test_no_zoom_stationary():
    history = deque(maxlen=30)
    result = None
    for _ in range(WAVE_WINDOW + 2):
        lms = _make_landmarks(pinch_dist=0.10)
        r = classify(lms, history)
        if r[0] is not None:
            result = r
    assert result is None


# ---------------------------------------------------------------------------
# Fist detection
# ---------------------------------------------------------------------------

def test_fist_detected():
    history = deque(maxlen=30)
    lms = _make_landmarks(fist=True)
    gesture, conf = classify(lms, history)
    assert gesture == "fist"
    assert conf == 1.0


# ---------------------------------------------------------------------------
# Engine: swipe + fist confirmation sequence
# ---------------------------------------------------------------------------

def test_swipe_requires_fist_confirmation():
    """A swipe alone should not fire — it becomes pending until a fist follows."""
    from gestures.engine import create_engine, process_frame

    engine = create_engine()
    fired = []

    # Swipe right with extended hand
    for i in range(WAVE_WINDOW + 2):
        x = 0.3 + i * 0.02
        lms = _make_landmarks(wrist_x=x)
        g = process_frame(engine, lms)
        if g:
            fired.append(g)

    assert fired == [], f"Swipe without fist should not fire, got {fired}"
    assert engine["pending_swipe"] == "next_slide"


def test_swipe_fires_after_fist():
    """Swipe followed by fist should fire the slide action."""
    from gestures.engine import create_engine, process_frame

    engine = create_engine()
    fired = []

    # Step 1: swipe right
    for i in range(WAVE_WINDOW + 2):
        x = 0.3 + i * 0.02
        lms = _make_landmarks(wrist_x=x)
        g = process_frame(engine, lms)
        if g:
            fired.append(g)

    assert engine["pending_swipe"] == "next_slide"

    # Step 2: fist to confirm
    fist_lms = _make_landmarks(fist=True)
    g = process_frame(engine, fist_lms)
    if g:
        fired.append(g)

    assert fired == ["next_slide"]
    assert engine["pending_swipe"] is None


def test_engine_cooldown():
    """After a gesture fires, same gesture shouldn't fire within cooldown."""
    from gestures.engine import create_engine, process_frame

    engine = create_engine()

    # Swipe right + fist to confirm
    for i in range(WAVE_WINDOW + 2):
        x = 0.3 + i * 0.02
        lms = _make_landmarks(wrist_x=x)
        process_frame(engine, lms)
    process_frame(engine, _make_landmarks(fist=True))  # confirm

    # Immediately swipe + fist again — should be suppressed by cooldown
    for i in range(WAVE_WINDOW + 2):
        x = 0.3 + i * 0.02
        lms = _make_landmarks(wrist_x=x)
        process_frame(engine, lms)
    result = process_frame(engine, _make_landmarks(fist=True))
    assert result is None
