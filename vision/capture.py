"""Camera capture using OpenCV."""

import cv2


def open_camera(index: int = 0):
    """Open camera and return a cv2.VideoCapture object."""
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera at index {index}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return cap


def read_frame(cap):
    """Read a single frame. Returns (success: bool, frame)."""
    return cap.read()


def release_camera(cap):
    """Release camera resources."""
    if cap:
        cap.release()
