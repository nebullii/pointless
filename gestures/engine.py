"""Gesture engine: feeds landmarks into the classifier with cooldown."""

import time
from collections import deque

from gestures.rules import classify

HISTORY_LEN = 30   # frames retained in sliding window
COOLDOWN = 1.0     # seconds before ANY gesture can fire again
MIN_CONFIDENCE = 0.40


def create_engine() -> dict:
    """Return a fresh engine state dict."""
    return {
        "history": deque(maxlen=HISTORY_LEN),
        "last_gesture": None,
        "last_time": 0.0,
    }


def process_frame(engine: dict, landmarks: list):
    """
    Feed new *landmarks* into *engine*.

    Returns the triggered gesture name (str) when a gesture fires,
    otherwise returns ``None``.
    """
    gesture, confidence = classify(landmarks, engine["history"])

    if gesture is None or confidence < MIN_CONFIDENCE:
        return None

    now = time.time()
    # Suppress ANY gesture within the cooldown window to prevent rapid-fire
    if now - engine["last_time"] < COOLDOWN:
        return None

    engine["last_gesture"] = gesture
    engine["last_time"] = now

    # Clear history after firing so old delta doesn't keep triggering
    engine["history"].clear()

    return gesture
