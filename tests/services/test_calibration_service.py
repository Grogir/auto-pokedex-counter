import pytest

from pokedex_counter.services.calibration_service import (
    DEFAULT_LOCK_THRESHOLD,
    DEFAULT_MIN_ROI_SIZE,
    DEFAULT_SCALES,
    _meets_min_size,
)
from pokedex_counter.vision.image_io import load_gray
from pokedex_counter.vision.template_matching import find_best_match

from .conftest import CALIBRATION_FILENAMES, FIXTURE_FILENAMES, FIXTURES_DIR

CASES = [
    (fixture_name, label)
    for fixture_name in FIXTURE_FILENAMES
    for label in CALIBRATION_FILENAMES
]


@pytest.mark.parametrize("fixture_name, label", CASES)
def test_calibrated_roi_is_reasonable(calibration_templates, fixture_name, label):
    fixture_gray = load_gray(FIXTURES_DIR / fixture_name)
    template = calibration_templates[label]

    best_val, best_box = find_best_match(fixture_gray, template, DEFAULT_SCALES)

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
