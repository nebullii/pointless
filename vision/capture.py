"""Camera capture helper."""

from __future__ import annotations

import cv2


def open_camera(index: int = 0):
    cap = cv2.VideoCapture(index)
    # 720p default
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    return cap
