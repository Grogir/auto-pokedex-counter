from __future__ import annotations

from pathlib import Path
from typing import Union

import cv2
import numpy as np

ImagePath = Union[str, Path]


def load_gray(path: ImagePath) -> np.ndarray | None:
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)


def load_color(path: ImagePath) -> np.ndarray | None:
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
