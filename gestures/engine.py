"""Gesture engine: feeds landmarks into the classifier with cooldown.

Swipe gesture sequence
----------------------
1. Swipe LEFT or RIGHT with all five fingers extended → stored as pending
2. Close hand into a FIST (rising edge only)          → confirms and fires the swipe

Fist is edge-triggered: it fires once on the open→close transition.
Holding the fist does NOT repeat the gesture; the user must open their hand first.
A fist with no pending swipe passes through as a "fist" event (pause toggle).
A pending swipe times out after PENDING_TIMEOUT seconds if no fist follows.
"""

from __future__ import annotations

import time
from collections import deque

from gestures.rules import classify, _extended_count

HISTORY_LEN     = 30   # frames retained in sliding window
COOLDOWN        = 1.0  # seconds before another gesture can fire
MIN_CONFIDENCE  = 0.40
PENDING_TIMEOUT = 3.0  # seconds to wait for fist after a swipe
MIN_OPEN_FINGERS = 2   # fingers that must be extended to consider hand "open"


def create_engine() -> dict:
    """Return a fresh engine state dict."""
    return {
        "history":       deque(maxlen=HISTORY_LEN),
        "last_gesture":  None,
        "last_time":     0.0,
        "pending_swipe": None,   # "next_slide" or "prev_slide"
        "pending_ts":    0.0,
        "prev_fist":     False,  # was the previous frame a fist?
    }


def process_frame(engine: dict, landmarks: list) -> str | None:
    """Feed new *landmarks* into *engine*.

    Returns the triggered gesture name when a gesture fires, else None.
    """
    gesture, confidence = classify(landmarks, engine["history"])
    now = time.time()

    # Track open→close transition for edge-triggered fist.
    # prev_fist resets to False only when the hand is clearly open
    # (2+ fingers extended). Intermediate/zoom frames do NOT reset it,
    # preventing spurious fist edges during hand opening motion.
    is_fist = (gesture == "fist")
    is_open = (_extended_count(landmarks) >= MIN_OPEN_FINGERS)

    if is_fist:
        fist_edge = not engine["prev_fist"]
        engine["prev_fist"] = True
    elif is_open:
        engine["prev_fist"] = False
        fist_edge = False
    else:
        fist_edge = False  # intermediate state — leave prev_fist unchanged

    # Expire a pending swipe if the user waited too long
    if engine["pending_swipe"] and now - engine["pending_ts"] > PENDING_TIMEOUT:
        print(f"[engine] pending swipe '{engine['pending_swipe']}' expired")
        engine["pending_swipe"] = None

    if gesture is None or confidence < MIN_CONFIDENCE:
        return None

    # ------------------------------------------------------------------
    # Fist — only fires on the rising edge (open→close transition)
    # ------------------------------------------------------------------
    if gesture == "fist":
        if not fist_edge:
            return None  # hand is still closed from before; ignore

        if engine["pending_swipe"]:
            confirmed = engine["pending_swipe"]
            engine["pending_swipe"] = None
            engine["last_gesture"] = confirmed
            engine["last_time"] = now
            engine["history"].clear()
            print(f"[engine] fist confirmed → {confirmed}")
            return confirmed

        # No pending swipe — pass through as pause toggle (with cooldown)
        if now - engine["last_time"] < COOLDOWN:
            return None
        engine["last_gesture"] = "fist"
        engine["last_time"] = now
        engine["history"].clear()
        return "fist"

    # ------------------------------------------------------------------
    # Swipe — stored as pending; requires fist to execute
    # ------------------------------------------------------------------
    if gesture in ("next_slide", "prev_slide"):
        if engine["pending_swipe"] is None and now - engine["last_time"] >= COOLDOWN:
            engine["pending_swipe"] = gesture
            engine["pending_ts"] = now
            engine["history"].clear()
            print(f"[engine] swipe detected: {gesture} — close fist to confirm")
        return None

    # ------------------------------------------------------------------
    # Zoom (and any other gesture) — blocked while swipe is pending
    # ------------------------------------------------------------------
    if engine["pending_swipe"]:
        return None

    if now - engine["last_time"] < COOLDOWN:
        return None

    engine["last_gesture"] = gesture
    engine["last_time"] = now
    engine["history"].clear()
    return gesture
