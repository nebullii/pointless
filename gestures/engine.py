"""Gesture engine: history buffer, smoothing, and debounce."""

from __future__ import annotations

from collections import deque

from gestures.rules import classify, extract_features

_HISTORY_LEN = 20       # frames of wrist-position history kept
_CONF_THRESH = 0.75     # minimum confidence to fire a gesture
_COOLDOWN_FRAMES = 20   # ~0.67 s at 30 fps before the same gesture can re-fire


class GestureEngine:
    def __init__(
        self,
        history_len: int = _HISTORY_LEN,
        confidence_thresh: float = _CONF_THRESH,
        cooldown_frames: int = _COOLDOWN_FRAMES,
    ) -> None:
        self._history: deque[tuple[float, float]] = deque(maxlen=history_len)
        self._conf_thresh = confidence_thresh
        self._cooldown = cooldown_frames
        self._frames_since_fire = cooldown_frames  # ready to fire from the start
        self._last_gesture: str | None = None

    def reset(self) -> None:
        """Clear position history. Call when the hand disappears from frame."""
        self._history.clear()

    def update(self, landmarks) -> tuple[str | None, float]:
        """Feed one frame's landmarks.

        Returns (gesture, confidence) when a gesture fires, else (None, 0.0).
        """
        feat = extract_features(landmarks)
        self._history.append((feat["wrist_x"], feat["wrist_y"]))
        self._frames_since_fire += 1

        gesture, conf = classify(landmarks, list(self._history))

        if gesture is None or conf < self._conf_thresh:
            return None, 0.0

        # Suppress same gesture repeating within the cooldown window
        if (
            self._frames_since_fire < self._cooldown
            and gesture == self._last_gesture
        ):
            return None, 0.0

        self._frames_since_fire = 0
        self._last_gesture = gesture
        return gesture, conf
