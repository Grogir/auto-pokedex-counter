import time

import cv2
import numpy as np

from pokedex_counter.config import FRAME_SIZE_CALIBRATION
from pokedex_counter.vision.template_matching import find_best_match

DEFAULT_SCALES = np.linspace(0.1, 5.0, 500)
DEFAULT_LOCK_THRESHOLD = 0.95
DEFAULT_CONFIRM_DELAY = 1.0
DEFAULT_POSITION_TOLERANCE = 1
DEFAULT_MIN_ROI_SIZE = (30, 30)


def _boxes_close(box_a, box_b, tolerance) -> bool:
    return all(abs(a - b) <= tolerance for a, b in zip(box_a, box_b))


def _meets_min_size(box, min_size) -> bool:
    _, _, w, h = box
    min_w, min_h = min_size
    return w >= min_w and h >= min_h


class CalibrationService:
    def __init__(
        self,
        camera_index=2,
        lock_threshold=DEFAULT_LOCK_THRESHOLD,
        scales=DEFAULT_SCALES,
        confirm_delay=DEFAULT_CONFIRM_DELAY,
        position_tolerance=DEFAULT_POSITION_TOLERANCE,
        min_roi_size=DEFAULT_MIN_ROI_SIZE,
    ):
        self.camera_index = camera_index
        self.lock_threshold = lock_threshold
        self.scales = scales
        self.confirm_delay = confirm_delay
        self.position_tolerance = position_tolerance
        self.min_roi_size = min_roi_size

    def run(self, templates: dict[str, np.ndarray], timeout: float | None = None) -> dict[str, tuple[int, int, int, int]]:
        """
        templates: mapping of ROI name (currently only "GAME_AREA") -> grayscale reference image.
        Returns mapping of ROI name -> locked normalized (x, y, w, h) for whichever templates
        stayed confident, at/above min_roi_size, AND at the same position for
        `confirm_delay` seconds.
        """
        pending = dict(templates)
        locked: dict[str, tuple[int, int, int, int]] = {}

        # name -> (timestamp streak started, box at streak start)
        candidates: dict[str, tuple[float, tuple[int, int, int, int]]] = {}

        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_SIZE_CALIBRATION[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_SIZE_CALIBRATION[1])
        if not cap.isOpened():
            raise RuntimeError(f"Could not open camera index {self.camera_index}")

        start = time.time()
        frame_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        frame_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(f"[Calibration] Opened VideoCapture in {int(frame_width)}x{int(frame_height)}")
        print(f"[Calibration] Waiting for: {', '.join(pending)}")
        print(f"[Calibration] Minimum ROI size: {self.min_roi_size[0]}x{self.min_roi_size[1]}")
        print("ESC or the window close button to abort.\n")

        try:
            while pending:
                if timeout is not None and time.time() - start > timeout:
                    print(f"[Calibration] Timed out with {list(pending)} unlocked.")
                    break

                ret, frame = cap.read()
                if not ret:
                    continue

                frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                display = frame.copy()
                newly_locked = []
                now = time.time()

                for name, template in pending.items():
                    best_val, best_box = find_best_match(frame_gray, template, self.scales)

                    confident = (
                        best_box is not None
                        and best_val >= self.lock_threshold
                        and _meets_min_size(best_box, self.min_roi_size)
                    )

                    if confident:
                        x, y, w, h = best_box
                        cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(display, f"{name}: {best_val:.2f}", (x, max(y - 8, 12)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                        streak = candidates.get(name)

                        if streak is None:
                            candidates[name] = (now, best_box)
                        elif _boxes_close(best_box, streak[1], self.position_tolerance):
                            first_hit_time, _ = streak
                            if now - first_hit_time >= self.confirm_delay:
                                locked[name] = (best_box[0] / frame_width, best_box[1] / frame_height, best_box[2] / frame_width, best_box[3] / frame_height)
                                newly_locked.append(name)
                                print(f"[Calibration] Locked {name} = {best_box}  "
                                      f"(score={best_val:.3f}, held for "
                                      f"{now - first_hit_time:.2f}s)")
                        else:
                            candidates[name] = (now, best_box)
                    else:
                        if best_box is not None:
                            x, y, w, h = best_box
                            color = (0, 165, 255) if best_val >= self.lock_threshold else (0, 0, 255)
                            cv2.rectangle(display, (x, y), (x + w, y + h), color, 2)
                            cv2.putText(display, f"{name}: {best_val:.2f} ({w}x{h})", (x, max(y - 8, 12)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        candidates.pop(name, None)

                for name in newly_locked:
                    pending.pop(name)
                    candidates.pop(name, None)

                window_name = "Calibration"
                cv2.imshow(window_name, cv2.resize(display, (1280, 720)))
                key = cv2.waitKey(1) & 0xFF
                if key == 27 or cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                    print("[Calibration] Aborted by user.")
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

        return locked
