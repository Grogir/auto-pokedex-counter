from pathlib import Path

import pytest

from pokedex_counter.config import CALIBRATION_DIR, CALIBRATION_FILENAMES
from pokedex_counter.vision.image_io import load_gray
from pokedex_counter.vision.template_matching import find_best_match

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "calibration"

FIXTURE_FILENAMES = ["calibration_01.png", "calibration_02.png"]


@pytest.fixture(scope="session")
def calibration_templates():
    return {
        label: load_gray(CALIBRATION_DIR / filename)
        for label, filename in CALIBRATION_FILENAMES.items()
    }


@pytest.fixture(scope="session")
def calibrated_rois(calibration_templates):
    return {
        fixture_name: {
            label: _normalized_box(load_gray(FIXTURES_DIR / fixture_name), template)
            for label, template in calibration_templates.items()
        }
        for fixture_name in FIXTURE_FILENAMES
    }


def _normalized_box(frame, template):
    box = find_best_match(frame, template)[1]
    height, width = frame.shape[:2]
    return (box[0] / width, box[1] / height, box[2] / width, box[3] / height)
