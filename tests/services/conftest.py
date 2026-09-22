from pathlib import Path

import pytest

from pokedex_counter.config import RESOURCES_DIR
from pokedex_counter.services.calibration_service import DEFAULT_SCALES
from pokedex_counter.vision.image_io import load_gray
from pokedex_counter.vision.template_matching import find_best_match

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "calibration"
CALIBRATION_DIR = RESOURCES_DIR / "calibration"

CALIBRATION_FILENAMES = {
    "catch": "catch.png",
    "evolve": "evolve.png",
    "text": "text.png",
}

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
            label: find_best_match(load_gray(FIXTURES_DIR / fixture_name), template, DEFAULT_SCALES)[1]
            for label, template in calibration_templates.items()
        }
        for fixture_name in FIXTURE_FILENAMES
    }
