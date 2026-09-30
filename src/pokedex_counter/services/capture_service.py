import cv2
from PySide6.QtCore import QThread, Signal

from pokedex_counter.detection_config import FRAME_SIZE_DETECTION


class CaptureService(QThread):
    frame_ready = Signal(object)

    def __init__(self, source=2):
        super().__init__()
        self.source = source
        self.frame_skip = 1
        self.running = False
        self.cap = None
        self._priority = QThread.Priority.InheritPriority
        self.finished.connect(self._restart_if_requested)

    def _open_capture(self):
        if isinstance(self.source, int):
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(self.source)
        self.change_resolution(FRAME_SIZE_DETECTION)

    def start(self, priority=QThread.Priority.InheritPriority):
        self._priority = priority
        self.running = True
        if self.isRunning():
            return
        super().start(priority)

    def _restart_if_requested(self):
        if self.running and not self.isRunning():
            super().start(self._priority)

    def change_resolution(self, resolution):
        if self.isRunning() and QThread.currentThread() != self:
            raise RuntimeError("Resolution must be changed in the capture thread")
        if self.cap is None:
            raise RuntimeError("Camera is not started")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        changed = (int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        print(f"[CaptureService] Current resolution: {changed[0]}x{changed[1]}")
        return changed

    def run(self):
        try:
            if not self.running:
                return
            self._open_capture()
            if not self.cap or not self.cap.isOpened():
                print(f"[CaptureService] ERROR: could not open camera index {self.source}")
                self.running = False
                return

            frame_count = 0
            while self.running:
                if frame_count % self.frame_skip == 0:
                    ret, frame = self.cap.read()
                    if ret and self.running:
                        self.frame_ready.emit(frame)
                else:
                    self.cap.grab()
                frame_count += 1
            print("[CaptureService] Stopped.")
        finally:
            if self.cap is not None:
                self.cap.release()
            self.cap = None

    def stop(self):
        self.running = False

    def shutdown(self):
        self.stop()
        if self.isRunning():
            self.wait()
