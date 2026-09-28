import time

import cv2
import numpy as np
from PySide6.QtCore import QObject, Qt, Signal, Slot

from pokedex_counter.detection_config import (
    FRAME_SIZE_CALIBRATION,
    FRAME_SIZE_DETECTION,
)
from pokedex_counter.vision.template_matching import find_best_match

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


class CalibrationService(QObject):
    finished = Signal(dict)

    def __init__(
        self,
        capture_service,
        lock_threshold=DEFAULT_LOCK_THRESHOLD,
        confirm_delay=DEFAULT_CONFIRM_DELAY,
        position_tolerance=DEFAULT_POSITION_TOLERANCE,
        min_roi_size=DEFAULT_MIN_ROI_SIZE,
    ):
        super().__init__()
        self.capture_service = capture_service
        self.lock_threshold = lock_threshold
        self.confirm_delay = confirm_delay
        self.position_tolerance = position_tolerance
        self.min_roi_size = min_roi_size
        self.active = False

    def start(self, templates: dict[str, np.ndarray], timeout: float | None = None) -> None:
        if not templates:
            print("[Calibration] No reference images found, skipping calibration.")
            self.finished.emit({})
            return
        self.pending = dict(templates)
        self.locked = {}
        self.candidates = {}
        self.started_at = time.time()
        self.timeout = timeout
        self.active = True
        self.change_resolution = True

        self.capture_service.frame_ready.connect(
            self.process_frame, Qt.ConnectionType.DirectConnection
        )
        print(f"[Calibration] Starting up. Looking for: {', '.join(self.pending)}")
        print("ESC or the window close button to abort.")

    @Slot(object)
    def process_frame(self, frame) -> None:
        if not self.active:
            return
        if self.change_resolution:
            self.capture_service.change_resolution(FRAME_SIZE_CALIBRATION)
            self.change_resolution = False
            return
        if self.timeout is not None and time.time() - self.started_at > self.timeout:
            print(f"[Calibration] Timed out with {list(self.pending)} unlocked.")
            self._finish()
            return

        frame_height, frame_width = frame.shape[:2]
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        display = frame.copy()
        newly_locked = []
        now = time.time()

        for name, template in self.pending.items():
            best_val, best_box = find_best_match(frame_gray, template)
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
                streak = self.candidates.get(name)
                if streak is None or not _boxes_close(
                    best_box, streak[1], self.position_tolerance
                ):
                    self.candidates[name] = (now, best_box)
                else:
                    first_hit_time, _ = streak
                    if now - first_hit_time >= self.confirm_delay:
                        self.locked[name] = (
                            best_box[0] / frame_width,
                            best_box[1] / frame_height,
                            best_box[2] / frame_width,
                            best_box[3] / frame_height,
                        )
                        newly_locked.append(name)
                        print(f"[Calibration] Locked {name} = {best_box} "
                              f"(score={best_val:.3f}, held for "
                              f"{now - first_hit_time:.2f}s)")
            else:
                if best_box is not None:
                    x, y, w, h = best_box
                    color = (0, 165, 255) if best_val >= self.lock_threshold else (0, 0, 255)
                    cv2.rectangle(display, (x, y), (x + w, y + h), color, 2)
                    cv2.putText(display, f"{name}: {best_val:.2f} ({w}x{h})", (x, max(y - 8, 12)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                self.candidates.pop(name, None)

        for name in newly_locked:
            self.pending.pop(name)
            self.candidates.pop(name, None)

        window_name = "Calibration"
        cv2.imshow(window_name, cv2.resize(display, (1280, 720)))
        key = cv2.waitKey(1) & 0xFF
        if not self.pending or key == 27 or cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            if self.pending:
                print("[Calibration] Aborted by user.")
            self._finish()

    def _finish(self) -> None:
        self.active = False
        self.capture_service.frame_ready.disconnect(self.process_frame)
        self.capture_service.change_resolution(FRAME_SIZE_DETECTION)
        cv2.destroyAllWindows()
        self.finished.emit(self.locked.copy())
