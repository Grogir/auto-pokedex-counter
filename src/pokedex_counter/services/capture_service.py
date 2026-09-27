import cv2
from PySide6.QtCore import QThread, Signal

from pokedex_counter.detection_config import FRAME_SIZE_DETECTION


class CaptureService(QThread):
    frame_ready = Signal(object)

    def __init__(self, source=2):
        super().__init__()
        self.camera_index = source
        self.frame_skip = 1
        self.running = True
        if isinstance(source, int):
            self.cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(source)
        self.change_resolution(FRAME_SIZE_DETECTION)

    def change_resolution(self, resolution):
        if self.isRunning() and QThread.currentThread() != self:
            raise RuntimeError("Resolution must be changed in the capture thread")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        changed = (int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        print(f"[CaptureService] Current resolution: {changed[0]}x{changed[1]}")
        return changed

    def run(self):
        if not self.cap.isOpened():
            print(f"[CaptureService] ERROR: could not open camera index {self.camera_index}")
            return

        frame_count = 0
        while self.running:
            if frame_count % self.frame_skip == 0:
                ret, frame = self.cap.read()
                if ret:
                    self.frame_ready.emit(frame)
            else:
                self.cap.grab()
            frame_count += 1
        print("[CaptureService] Stopped running.")

    def stop(self):
        self.running = False
        self.cap.release()
        self.wait()
