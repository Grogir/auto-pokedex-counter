import numpy as np
import pytest

from pokedex_counter.detection_config import (
    FRAME_SIZE_CALIBRATION,
)
from pokedex_counter.services.calibration_service import (
    DEFAULT_LOCK_THRESHOLD,
    DEFAULT_MIN_ROI_SIZE,
    CalibrationService,
    _meets_min_size,
)
from pokedex_counter.vision.image_io import load_gray
from pokedex_counter.vision.template_matching import find_best_match

from .conftest import CALIBRATION_FILENAMES, FIXTURE_FILENAMES, FIXTURES_DIR


def test_start_connects_frame_handler_and_changes_resolution_from_frame(monkeypatch):
    class FakeCaptureService:
        def __init__(self):
            self.calls = []

        def change_resolution(self, resolution):
            self.calls.append(resolution)
            return resolution

        class Signal:
            def connect(self, slot, connection_type):
                self.slot = slot

            def disconnect(self, slot):
                assert slot is self.slot

    capture = FakeCaptureService()
    capture.frame_ready = capture.Signal()
    monkeypatch.setattr(
        "pokedex_counter.services.calibration_service.cv2.destroyAllWindows",
        lambda: None,
    )

    service = CalibrationService(capture)
    service.start({"TEST": np.zeros((1, 1), dtype=np.uint8)})
    service.process_frame(np.zeros((2, 2, 3), dtype=np.uint8))

    assert capture.calls == [FRAME_SIZE_CALIBRATION]


def test_start_requires_capture_service_when_templates_are_provided():
    service = CalibrationService()

    with pytest.raises(RuntimeError, match="requires a capture service"):
        service.start({"TEST": np.zeros((1, 1), dtype=np.uint8)})

CASES = [
    (fixture_name, label)
    for fixture_name in FIXTURE_FILENAMES
    for label in CALIBRATION_FILENAMES
]


@pytest.mark.parametrize("fixture_name, label", CASES)
def test_calibrated_roi_is_reasonable(calibration_templates, fixture_name, label):
    fixture_gray = load_gray(FIXTURES_DIR / fixture_name)
    template = calibration_templates[label]

    best_val, best_box = find_best_match(fixture_gray, template)

    assert best_box is not None, f"{fixture_name}: no match found at any scale"

    x, y, w, h = best_box
    fh, fw = fixture_gray.shape[:2]

    assert x >= 0 and y >= 0, f"{fixture_name}: ROI has negative origin {best_box}"
    assert x + w <= fw and y + h <= fh, (
        f"{fixture_name}: ROI {best_box} extends outside frame bounds ({fw}x{fh})"
    )
    assert _meets_min_size(best_box, DEFAULT_MIN_ROI_SIZE), (
        f"{fixture_name}: ROI {best_box} smaller than minimum {DEFAULT_MIN_ROI_SIZE}"
    )

    assert best_val >= DEFAULT_LOCK_THRESHOLD, (
        f"{fixture_name}: score {best_val:.3f} below calibration lock threshold {DEFAULT_LOCK_THRESHOLD}"
    )
