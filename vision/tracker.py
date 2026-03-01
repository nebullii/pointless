"""Hand tracking using MediaPipe HandLandmarker (mediapipe >= 0.10).

Uses VIDEO running mode for temporal smoothing across frames.
Only tracks hand landmarks — no gesture classification needed.
"""

from __future__ import annotations

import pathlib
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python as _mp_tasks
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    RunningMode,
)

# ---------------------------------------------------------------------------
# Model auto-download
# ---------------------------------------------------------------------------
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
_MODEL_PATH = pathlib.Path(__file__).resolve().parents[1] / "models" / "hand_landmarker.task"


def _ensure_model() -> str:
    if not _MODEL_PATH.exists():
        _MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading hand_landmarker.task → {_MODEL_PATH} ...")
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
        print("Download complete.")
    return str(_MODEL_PATH)


# ---------------------------------------------------------------------------
# Landmark index constants (MediaPipe 21-point hand model)
# ---------------------------------------------------------------------------
WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8
MIDDLE_TIP = 12
RING_TIP = 16
PINKY_TIP = 20

# Connections used for drawing (pairs of landmark indices)
_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),       # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # index
    (5, 9), (9, 10), (10, 11), (11, 12),   # middle
    (9, 13), (13, 14), (14, 15), (15, 16), # ring
    (13, 17), (17, 18), (18, 19), (19, 20),# pinky
    (0, 17),                                # palm base
]


def create_tracker(
    max_hands: int = 1,
    detection_confidence: float = 0.5,
    tracking_confidence: float = 0.5,
) -> HandLandmarker:
    """Return an initialised HandLandmarker in VIDEO mode."""
    model_path = _ensure_model()
    options = HandLandmarkerOptions(
        base_options=_mp_tasks.BaseOptions(model_asset_path=model_path),
        running_mode=RunningMode.VIDEO,
        num_hands=max_hands,
        min_hand_detection_confidence=detection_confidence,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=tracking_confidence,
    )
    return HandLandmarker.create_from_options(options)


# Monotonically increasing timestamp for VIDEO mode
_frame_ts_ms = 0


def track_hands(frame, tracker: HandLandmarker) -> list[dict]:
    """Process a BGR frame and return detected hands.

    Each dict has:
      'landmarks' — list of 21 (x, y, z) normalised coords
      'handedness' — 'Left' or 'Right'
    """
    global _frame_ts_ms
    _frame_ts_ms += 33  # ~30 fps, must be strictly increasing

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = tracker.detect_for_video(mp_image, _frame_ts_ms)

    hands = []
    if result.hand_landmarks:
        for lms, handedness_list in zip(result.hand_landmarks, result.handedness):
            lm_list = [(lm.x, lm.y, lm.z) for lm in lms]
            label = handedness_list[0].category_name
            hands.append({"landmarks": lm_list, "handedness": label})
    return hands


def draw_hands(frame, hands: list[dict]) -> None:
    """Draw landmarks and skeleton connections on *frame* in-place."""
    h, w = frame.shape[:2]
    for hand in hands:
        lms = hand["landmarks"]
        for a, b in _CONNECTIONS:
            x1, y1 = int(lms[a][0] * w), int(lms[a][1] * h)
            x2, y2 = int(lms[b][0] * w), int(lms[b][1] * h)
            cv2.line(frame, (x1, y1), (x2, y2), (255, 80, 0), 2, cv2.LINE_AA)
        for x, y, _ in lms:
            cx, cy = int(x * w), int(y * h)
            cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
