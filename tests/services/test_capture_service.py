import threading
import time

import numpy as np
from PySide6.QtCore import Qt

from pokedex_counter.services import capture_service
from pokedex_counter.services.capture_service import CaptureService


class _FakeVideoCapture:
    def __init__(self, source, backend=None):
        self.resolution = [640, 480]
        self.set_threads = []
        self.read_thread = None
        self.opened = True

    def set(self, prop, value):
        self.set_threads.append(threading.get_ident())
        self.resolution[0 if prop == capture_service.cv2.CAP_PROP_FRAME_WIDTH else 1] = value
        return True

    def get(self, prop):
        return self.resolution[
            0 if prop == capture_service.cv2.CAP_PROP_FRAME_WIDTH else 1
        ]

    def isOpened(self):
        return self.opened

    def read(self):
        self.read_thread = threading.get_ident()
        time.sleep(0.001)
        return True, np.zeros((2, 2, 3), dtype=np.uint8)

    def grab(self):
        return True

    def release(self):
        self.opened = False


def test_resolution_changes_are_applied_from_frame_slot(monkeypatch):
    fake_capture = _FakeVideoCapture(0)
    monkeypatch.setattr(capture_service.cv2, "VideoCapture", lambda *args: fake_capture)
    service = CaptureService(source=0)
    changed = threading.Event()

    def calibrate_frame(frame):
        service.change_resolution((1920, 1080))
        changed.set()
        service.running = False

    service.frame_ready.connect(
        calibrate_frame, Qt.ConnectionType.DirectConnection
    )
    service.start()
    assert changed.wait(1)
    service.wait()

    assert fake_capture.read_thread is not None
    assert fake_capture.set_threads[-1] == fake_capture.read_thread


def test_resolution_change_from_ui_thread_is_rejected_while_running(monkeypatch):
    fake_capture = _FakeVideoCapture(0)
    monkeypatch.setattr(capture_service.cv2, "VideoCapture", lambda *args: fake_capture)
    service = CaptureService(source=0)
    frame_read = threading.Event()
    service.frame_ready.connect(
        lambda _: frame_read.set(), Qt.ConnectionType.DirectConnection
    )
    service.start()

    try:
        assert frame_read.wait(1)
        try:
            service.change_resolution((1920, 1080))
        except RuntimeError:
            pass
        else:
            raise AssertionError("UI-thread resolution change should be rejected")
    finally:
        service.stop()