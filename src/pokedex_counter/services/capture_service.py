import cv2
from PySide6.QtCore import QThread, Signal
from pokedex_counter.config import FRAME_SIZE

class CaptureService(QThread):
    frame_ready = Signal(object)

    def __init__(self, source=2):
        super().__init__()
        self.camera_index = source
        self.frame_skip = 1
        if isinstance(source, int):
            self.cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(source)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_SIZE[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_SIZE[1])
        self.running = True

    def run(self):
        if not self.cap.isOpened():
            print(f"[CaptureService] ERROR: could not open camera index {self.camera_index}")
            return
        print(f"[CaptureService] Opened VideoCapture in {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")

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
