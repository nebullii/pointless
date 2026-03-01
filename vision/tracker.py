"""Hand tracking using the MediaPipe Tasks API (mediapipe >= 0.10)."""

from __future__ import annotations

import time
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
_MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "hand_landmarker.task"


def _ensure_model() -> str:
    if not _MODEL_PATH.exists():
        _MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading hand landmark model → {_MODEL_PATH} ...")
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
        print("Download complete.")
    return str(_MODEL_PATH)


class _LandmarkList:
    """Thin wrapper so rules.py can use landmarks.landmark[i].x/y/z unchanged."""

    def __init__(self, lm_list) -> None:
        self.landmark = lm_list  # list of NormalizedLandmark (.x .y .z)


class HandTracker:
    def __init__(
        self,
        max_hands: int = 1,
        min_detection: float = 0.6,
        min_tracking: float = 0.6,
    ) -> None:
        model_path = _ensure_model()
        options = mp_vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=min_detection,
            min_hand_presence_confidence=min_detection,
            min_tracking_confidence=min_tracking,
        )
        self._detector = mp_vision.HandLandmarker.create_from_options(options)
        self._t0_ms = int(time.monotonic() * 1000)

    def track(self, frame_bgr) -> list[_LandmarkList]:
        """Return one _LandmarkList per detected hand (empty list if none)."""
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        ts_ms = int(time.monotonic() * 1000) - self._t0_ms
        result = self._detector.detect_for_video(mp_image, ts_ms)
        if not result.hand_landmarks:
            return []
        return [_LandmarkList(lms) for lms in result.hand_landmarks]

    def close(self) -> None:
        self._detector.close()
