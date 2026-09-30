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
    service.stop()
    assert service.wait(1000)

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
        assert service.wait(1000)


def test_capture_can_be_started_and_stopped_repeatedly(monkeypatch):
    captures = []

    def create_capture(*args):
        capture = _FakeVideoCapture(*args)
        captures.append(capture)
        return capture

    monkeypatch.setattr(capture_service.cv2, "VideoCapture", create_capture)
    service = CaptureService(source=0)
    assert captures == []

    for _ in range(2):
        frame_read = threading.Event()
        service.frame_ready.connect(
            lambda _frame, event=frame_read: event.set(),
            Qt.ConnectionType.DirectConnection,
        )
        service.start()
        assert frame_read.wait(1)
        service.stop()
        assert service.wait(1000)

    assert len(captures) == 2
    assert all(not capture.opened for capture in captures)


def test_start_returns_while_camera_open_is_blocked(monkeypatch):
    open_started = threading.Event()
    allow_open = threading.Event()
    start_returned = threading.Event()
    fake_capture = _FakeVideoCapture(0)

    def blocked_open(*args):
        open_started.set()
        allow_open.wait(1)
        return fake_capture

    monkeypatch.setattr(capture_service.cv2, "VideoCapture", blocked_open)
    service = CaptureService(source=0)

    starter = threading.Thread(
        target=lambda: (service.start(), start_returned.set())
    )
    starter.start()

    assert open_started.wait(1)
    assert start_returned.wait(0.1)

    service.stop()
    allow_open.set()
    starter.join(1)
    assert service.wait(1000)


def test_stop_returns_while_camera_read_is_blocked(monkeypatch):
    read_started = threading.Event()
    allow_read = threading.Event()
    stop_returned = threading.Event()

    class BlockingReadCapture(_FakeVideoCapture):
        def read(self):
            self.read_thread = threading.get_ident()
            read_started.set()
            allow_read.wait(1)
            return True, np.zeros((2, 2, 3), dtype=np.uint8)

    fake_capture = BlockingReadCapture(0)
    monkeypatch.setattr(capture_service.cv2, "VideoCapture", lambda *args: fake_capture)
    service = CaptureService(source=0)
    service.start()
    assert read_started.wait(1)

    stopper = threading.Thread(
        target=lambda: (service.stop(), stop_returned.set())
    )
    stopper.start()

    assert stop_returned.wait(0.1)
    allow_read.set()
    stopper.join(1)
    assert service.wait(1000)
