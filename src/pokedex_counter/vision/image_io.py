from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np


ImagePath = Union[str, Path]


def load_gray(path: ImagePath) -> Optional[np.ndarray]:
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)


def load_color(path: ImagePath) -> Optional[np.ndarray]:
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
