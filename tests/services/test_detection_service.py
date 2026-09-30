from pathlib import Path

import numpy as np
import pytest

from pokedex_counter.config import (
    CALIBRATION_DIR,
    CALIBRATION_FILENAMES,
    DETECTION_IMAGE_DIR,
)
from pokedex_counter.detection_config import (
    DETECTION_TYPE,
    FRAME_SIZE_DETECTION,
)
from pokedex_counter.services.detection_service import DetectionService
from pokedex_counter.services.template_service import TemplateService
from pokedex_counter.vision.image_io import load_color, load_gray
from tests.conftest import sections_for

DETECTION_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "detection"
SEC_HYPNO = sections_for("HYPNO")[0]
SEC_SLOWBRO = sections_for("SLOWBRO")[1]
SEC_CLEFAIRY = sections_for("CLEFAIRY")[2]
DETECTION_IMAGE_CASES = [
    ("calibration_01.png", "catch_01.png", "HYPNO", SEC_HYPNO),
    ("calibration_01.png", "evolve_01.png", "SLOWBRO", SEC_SLOWBRO),
    ("calibration_01.png", "text_01.png", "CLEFAIRY", SEC_CLEFAIRY),
    ("calibration_02.png", "catch_02.png", "HYPNO", SEC_HYPNO),
    ("calibration_02.png", "evolve_02.png", "SLOWBRO", SEC_SLOWBRO),
    ("calibration_02.png", "text_02.png", "CLEFAIRY", SEC_CLEFAIRY),
    ("calibration_01.png", "catch_01_palette.png", "HYPNO", SEC_HYPNO),
    ("calibration_01.png", "catch_01_inverted.png", "HYPNO", SEC_HYPNO),
    ("calibration_01.png", "evolve_01_palette.png", "SLOWBRO", SEC_SLOWBRO),
    ("calibration_01.png", "evolve_01_inverted.png", "SLOWBRO", SEC_SLOWBRO),
    ("calibration_01.png", "text_01_palette.png", "CLEFAIRY", SEC_CLEFAIRY),
    ("calibration_01.png", "text_01_inverted.png", "CLEFAIRY", SEC_CLEFAIRY),
]
DETECTION_TEXTBOX_CASES = [
    ("calibration_03.png", "textbox_catch_03.png", "MAROWAK"),
    ("calibration_03.png", "textbox_evolve_03.png", "GOLDUCK"),
    ("calibration_03.png", "textbox_name_03.png", "EEVEE"),
]


@pytest.fixture(scope="module")
def sprite_templates():
    return TemplateService(DETECTION_IMAGE_DIR).templates


def _make_detector(game_area):
    detector = DetectionService()
    detector.update_game_area(game_area)
    detector._test_section = 0
    detector.set_section_provider(
        lambda: detector._test_section
    )
    return detector


def _build_detector(sprite_templates, game_area):
    detector = _make_detector(game_area)
    detector.build_roi_groups(sprite_templates)
    return detector


def _prime_to_section(detector, section_index):
    detector._test_section = section_index


@pytest.mark.parametrize(
    "calibration_fixture, detection_fixture, expected_name, expected_section",
    DETECTION_IMAGE_CASES,
)
def test_calibrated_game_area_detects_expected_pokemon(
    sprite_templates,
    calibrated_rois,
    calibration_fixture,
    detection_fixture,
    expected_name,
    expected_section,
):
    game_area = calibrated_rois[calibration_fixture]["GAME_AREA"]
    detector = _build_detector(sprite_templates, game_area)
    _prime_to_section(detector, expected_section)
    detections = []
    detector.detection.connect(detections.append)

    frame = load_color(DETECTION_FIXTURES_DIR / detection_fixture)
    assert frame is not None
    detector.process_frame_image(frame)

    assert detections == [expected_name]


@pytest.mark.parametrize(
    "calibration_fixture, detection_fixture, expected_name",
    DETECTION_TEXTBOX_CASES,
)
def test_textbox_frames_detect_expected_pokemon(
    calibration_fixture, detection_fixture, expected_name
):
    detector = _make_detector((0, 0, 1, 1))
    detections = []
    detector.detection.connect(detections.append)

    frame = load_color(DETECTION_FIXTURES_DIR / detection_fixture)
    assert frame is not None
    calibration_dir = Path(__file__).parent.parent / "fixtures" / "calibration"
    calibration = load_gray(calibration_dir / calibration_fixture)
    template = load_gray(CALIBRATION_DIR / CALIBRATION_FILENAMES["GAME_AREA"])
    from pokedex_counter.vision.template_matching import find_best_match

    _, box = find_best_match(calibration, template)
    height, width = calibration.shape[:2]
    detector.update_game_area(
        (box[0] / width, box[1] / height, box[2] / width, box[3] / height)
    )
    detector.process_frame_textbox(frame)

    assert detections == [expected_name]


def test_repeated_frames_detect_only_once_until_forgotten(sprite_templates, calibrated_rois):
    game_area = calibrated_rois["calibration_01.png"]["GAME_AREA"]
    detector = _build_detector(sprite_templates, game_area)
    _prime_to_section(detector, SEC_HYPNO)
    detections = []
    detector.detection.connect(detections.append)
    frame = load_color(DETECTION_FIXTURES_DIR / "catch_01.png")

    for _ in range(5):
        detector.process_frame_image(frame)
    assert detections == ["HYPNO"]

    detector.process_frame_image(np.zeros_like(frame))
    assert detections == ["HYPNO"]

    detector.forget("HYPNO")
    detector.process_frame_image(frame)
    assert detections == ["HYPNO", "HYPNO"]


def test_flat_frame_does_not_spuriously_match(sprite_templates, calibrated_rois):
    game_area = calibrated_rois["calibration_01.png"]["GAME_AREA"]
    detector = _build_detector(sprite_templates, game_area)
    detections = []
    detector.detection.connect(detections.append)

    detector.process_frame_image(
        np.full((*reversed(FRAME_SIZE_DETECTION), 3), 128, dtype=np.uint8)
    )

    assert detections == []


@pytest.mark.parametrize(
    "detection_type, expected_method",
    [(DETECTION_TYPE["TEXT"], "process_frame_textbox"), (DETECTION_TYPE["SPRITE"], "process_frame_image")],
)
def test_process_frame_routes_to_the_selected_detection_method(
    monkeypatch, detection_type, expected_method
):
    detector = _make_detector(None)
    calls = []
    monkeypatch.setattr(detector, "process_frame_textbox", lambda frame: calls.append("text"))
    monkeypatch.setattr(detector, "process_frame_image", lambda frame: calls.append("sprite"))
    detector.set_detection_type(detection_type)

    detector.process_frame(object())

    assert calls == ["text" if expected_method == "process_frame_textbox" else "sprite"]


def test_process_frame_skips_detection_when_disabled(monkeypatch):
    detector = _make_detector(None)
    calls = []
    monkeypatch.setattr(detector, "process_frame_textbox", lambda frame: calls.append("text"))
    monkeypatch.setattr(detector, "process_frame_image", lambda frame: calls.append("sprite"))
    detector.set_detection_type(DETECTION_TYPE["NONE"])

    detector.process_frame(object())

    assert calls == []
