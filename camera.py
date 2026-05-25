"""
camera.py
=========
OpenCV webcam abstraction layer.
Handles camera open/close, resolution, frame read, display, and save.
Designed for easy swap when migrating to edge hardware (e.g. CSI camera
on Raspberry Pi).
"""

import cv2
from config import CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT
from logger_config import logger


def open_camera(index: int = None) -> cv2.VideoCapture | None:
    """
    Open the webcam and return a VideoCapture object.
    Returns None if the camera cannot be opened.
    """
    idx = index if index is not None else CAMERA_INDEX
    cap = cv2.VideoCapture(idx)

    if not cap.isOpened():
        logger.error("Cannot open camera at index %d", idx)
        print(f"\n[ERROR] Cannot open camera at index {idx}.")
        print("  → Make sure your webcam is connected and not used by another app.")
        print(f"  → You can change CAMERA_INDEX in config.py (current: {CAMERA_INDEX}).\n")
        return None

    set_camera_resolution(cap)
    logger.info("Camera opened successfully (index=%d)", idx)
    return cap


def set_camera_resolution(cap: cv2.VideoCapture,
                          width: int = None,
                          height: int = None) -> None:
    """Set the capture resolution. Falls back to config defaults."""
    w = width if width is not None else FRAME_WIDTH
    h = height if height is not None else FRAME_HEIGHT
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)


def release_camera(cap: cv2.VideoCapture) -> None:
    """Release the camera and destroy OpenCV windows."""
    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()
    logger.info("Camera released")


def read_frame(cap: cv2.VideoCapture):
    """
    Read a single frame from the camera.

    Returns
    -------
    tuple (bool, frame)
        success flag and the BGR frame (or None).
    """
    if cap is None:
        return False, None
    ret, frame = cap.read()
    if not ret:
        logger.warning("Failed to read frame from camera")
    return ret, frame


def show_frame(window_name: str, frame) -> None:
    """Display a frame in an OpenCV window."""
    if frame is not None:
        cv2.imshow(window_name, frame)


def save_frame(path: str, frame) -> bool:
    """
    Save a frame to disk as JPEG.

    Returns
    -------
    bool
        True if the save succeeded.
    """
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    success = cv2.imwrite(path, frame)
    if success:
        logger.debug("Frame saved to %s", path)
    else:
        logger.warning("Failed to save frame to %s", path)
    return success
