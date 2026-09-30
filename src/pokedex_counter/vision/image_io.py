from pathlib import Path

import cv2
import numpy as np


def load_gray(path: str | Path) -> np.ndarray | None:
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)


def load_color(path: str | Path) -> np.ndarray | None:
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)


def load_unchanged(path: str | Path) -> np.ndarray | None:
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
