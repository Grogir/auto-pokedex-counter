from pathlib import Path

import cv2
import numpy as np
import pytest

from pokedex_counter.config import FRAME_SIZE, SPRITES_BG_DIR, THRESHOLD
from pokedex_counter.roi_config import build_detection_entries
from pokedex_counter.services.detection_service import DetectionService
from pokedex_counter.services.template_service import TemplateService

DETECTION_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "detection"

# (calibration_fixture, label, detection_fixture, expected_name, expected_section)
# expected_section is where `expected_name` actually lives in CATCH_SECTIONS,
# since detection is only active for the current section - see
# _prime_to_section below.
DETECTION_CASES = [
    ("calibration_01.png", "catch", "catch_01.png", "97", 1),
    ("calibration_01.png", "evolve", "evolve_01.png", "80", 11),
    ("calibration_01.png", "text", "text_01.png", "35", 9),
    ("calibration_02.png", "catch", "catch_02.png", "97", 1),
    ("calibration_02.png", "evolve", "evolve_02.png", "80", 11),
    ("calibration_02.png", "text", "text_02.png", "35", 9),
    # Real captures of the same screens under a different (non-default) GBC
    # hardware palette and under a fully inverted ("Negative"-style) one -
    # regression coverage for canonicalize_shades()/the ROI search margin.
    ("calibration_01.png", "catch", "catch_01_palette.png", "97", 1),
    ("calibration_01.png", "catch", "catch_01_inverted.png", "97", 1),
    ("calibration_01.png", "evolve", "evolve_01_palette.png", "80", 11),
    ("calibration_01.png", "evolve", "evolve_01_inverted.png", "80", 11),
    ("calibration_01.png", "text", "text_01_palette.png", "35", 9),
    ("calibration_01.png", "text", "text_01_inverted.png", "35", 9),
]


@pytest.fixture(scope="module")
def sprite_templates():
    return TemplateService(Path(SPRITES_BG_DIR)).templates


def _roi_templates_for(calibration_fixture, sprite_templates, calibrated_rois):
    rois = calibrated_rois[calibration_fixture]
    locked = {"CATCH": rois["catch"], "EVOLVE": rois["evolve"], "TEXT": rois["text"]}
    return build_detection_entries(sprite_templates, locked)


def _prime_to_section(detector, section_index):
    """Simulate the run having already progressed to `section_index`, by
    marking every earlier section's required Pokemon as already detected.
    DetectionService only matches templates in its current active section
    (see roi_config.py's CATCH_SECTIONS/SECTION_TRIGGERS), so a cold
    detector can't see a later section's Pokemon in isolation the way
    these fixtures test them."""
    detector._detected.update(
        name for names in detector._section_triggers[:section_index] for name in names
    )


@pytest.mark.parametrize(
    "calibration_fixture, label, detection_fixture, expected_name, expected_section", DETECTION_CASES
)
def test_calibrated_roi_detects_expected_pokemon(
    sprite_templates, calibrated_rois, calibration_fixture, label, detection_fixture, expected_name, expected_section
):
    roi_templates = _roi_templates_for(calibration_fixture, sprite_templates, calibrated_rois)

    detector = DetectionService(roi_templates)
    _prime_to_section(detector, expected_section)
    detections = []
    detector.detection.connect(detections.append)

    frame = cv2.imread(str(DETECTION_FIXTURES_DIR / detection_fixture))
    assert frame is not None, f"Could not load image: {detection_fixture}"
    detector.process_frame(cv2.flip(frame, 1))

    assert detections == [expected_name], (
        f"{calibration_fixture} -> {detection_fixture} ({label}): "
        f"expected detection {expected_name!r}, got {detections}"
    )


def test_repeated_frames_detect_only_once_until_forgotten(sprite_templates, calibrated_rois):
    roi_templates = _roi_templates_for("calibration_01.png", sprite_templates, calibrated_rois)

    detector = DetectionService(roi_templates)
    _prime_to_section(detector, 1)  # "97" lives in section 1
    detections = []
    detector.detection.connect(detections.append)

    frame = cv2.imread(str(DETECTION_FIXTURES_DIR / "catch_01.png"))
    flipped = cv2.flip(frame, 1)

    # Same screen held across many frames (e.g. player hasn't pressed a
    # button yet) must only fire the signal once, not once per frame.
    for _ in range(5):
        detector.process_frame(flipped)
    assert detections == ["97"]

    # A frame with nothing recognizable must not re-trigger it either.
    detector.process_frame(np.zeros_like(flipped))
    assert detections == ["97"]

    # Only forgetting it (manual "unclick" in the UI) allows re-detection.
    detector.forget("97")
    detector.process_frame(flipped)
    assert detections == ["97", "97"]


def _pattern(seed, size=20):
    return np.random.RandomState(seed).randint(0, 256, (size, size), dtype=np.uint8)


def _frame_with_pattern_at(roi, pattern):
    """Build a frame containing `pattern` exactly at `roi`. The result is
    pre-flipped so passing it to process_frame (which flips once) lands
    the pattern at `roi` in the coordinates DetectionService crops from."""
    width, height = FRAME_SIZE
    frame = np.full((height, width, 3), 127, dtype=np.uint8)
    x, y, w, h = roi
    for channel in range(3):
        frame[y:y + h, x:x + w, channel] = pattern
    return cv2.flip(frame, 1)


def test_entries_outside_active_section_are_excluded_until_trigger_fires():
    roi = (0, 0, 20, 20)
    name_a, name_b = "A", "B"
    roi_templates = [(name_a, roi, _pattern(1), 0), (name_b, roi, _pattern(2), 1)]

    detector = DetectionService(roi_templates)
    detector._section_triggers = [[name_a], []]  # detecting "A" advances to section 1
    detections = []
    detector.detection.connect(detections.append)

    frame_b = _frame_with_pattern_at(roi, _pattern(2))  # exact match for "B"

    # Fresh detector starts on section 0; "B" belongs to section 1 and must
    # not be considered at all, even though it's a perfect pixel match.
    detector.process_frame(frame_b)
    assert detections == []

    # Detecting "A" (section 0's trigger) advances to section 1, so the
    # same frame is now detected as "B".
    detector.process_frame(_frame_with_pattern_at(roi, _pattern(1)))
    assert detections == [name_a]

    detector.process_frame(frame_b)
    assert detections == [name_a, name_b]


def test_a_section_holds_until_every_required_pokemon_is_caught():
    """The bug this mechanic replaced: advancing on one Pokemon meant
    catching it out of order ended the section early, and since nothing
    outside the active section is ever matched, whatever was still
    outstanding became uncatchable for the rest of the run."""
    roi = (0, 0, 20, 20)
    early, straggler, next_section = "EARLY", "STRAGGLER", "NEXT"
    roi_templates = [
        (early, roi, _pattern(1), 0),
        (straggler, roi, _pattern(2), 0),
        (next_section, roi, _pattern(3), 1),
    ]

    detector = DetectionService(roi_templates)
    detector._section_triggers = [[early, straggler], []]
    detections = []
    detector.detection.connect(detections.append)

    # "EARLY" out of order: the section must NOT end, since "STRAGGLER" is
    # still outstanding.
    detector.process_frame(_frame_with_pattern_at(roi, _pattern(1)))
    assert detections == [early]
    assert detector.current_section() == 0

    # Section 1's Pokemon is a perfect pixel match but still out of scope.
    detector.process_frame(_frame_with_pattern_at(roi, _pattern(3)))
    assert detections == [early]

    # The straggler is still reachable - that's the whole point.
    detector.process_frame(_frame_with_pattern_at(roi, _pattern(2)))
    assert detections == [early, straggler]
    assert detector.current_section() == 1

    detector.process_frame(_frame_with_pattern_at(roi, _pattern(3)))
    assert detections == [early, straggler, next_section]


def test_forgetting_any_one_required_pokemon_rolls_the_section_back():
    """forget() has to undo the advance no matter which of the required
    Pokemon was the misdetection, not just the last one."""
    roi = (0, 0, 20, 20)
    first, second = "FIRST", "SECOND"
    roi_templates = [(first, roi, _pattern(1), 0), (second, roi, _pattern(2), 0)]

    detector = DetectionService(roi_templates)
    detector._section_triggers = [[first, second], []]

    detector.process_frame(_frame_with_pattern_at(roi, _pattern(1)))
    detector.process_frame(_frame_with_pattern_at(roi, _pattern(2)))
    assert detector.current_section() == 1

    detector.forget(first)
    assert detector.current_section() == 0


def test_forgetting_the_trigger_rolls_back_the_active_section():
    roi = (0, 0, 20, 20)
    name_a, name_b = "A", "B"
    roi_templates = [(name_a, roi, _pattern(1), 0), (name_b, roi, _pattern(2), 1)]

    detector = DetectionService(roi_templates)
    detector._section_triggers = [[name_a], []]
    detections = []
    detector.detection.connect(detections.append)

    frame_a = _frame_with_pattern_at(roi, _pattern(1))
    frame_b = _frame_with_pattern_at(roi, _pattern(2))

    detector.process_frame(frame_a)
    detector.process_frame(frame_b)
    assert detections == [name_a, name_b]

    # Undo both (e.g. the player manually un-clicks a misdetection). "A"
    # being forgotten must roll the active section back to 0, so "B" isn't
    # matched again even though its template is still a perfect fit.
    detector.forget(name_a)
    detector.forget(name_b)
    detector.process_frame(frame_b)
    assert detections == [name_a, name_b]


def test_update_rois_rebuilds_groups_without_touching_detected():
    roi = (0, 0, 20, 20)
    detector = DetectionService([("A", roi, _pattern(1), 0)])
    detector._detected.add("A")

    new_roi = (0, 0, 25, 25)
    detector.update_rois([("B", new_roi, _pattern(2), 0)])

    assert "A" in detector._detected  # mid-run progress survives recalibration
    assert [roi for roi, _entries in detector._roi_groups] == [new_roi]
    names_in_group = {name for name, _template, _canonical, _section in detector._roi_groups[0][1]}
    assert names_in_group == {"B"}


def test_update_rois_new_templates_are_matched_immediately():
    roi = (0, 0, 20, 20)
    detector = DetectionService([("A", roi, _pattern(1), 0)])
    detections = []
    detector.detection.connect(detections.append)

    detector.update_rois([("B", roi, _pattern(2), 0)])
    detector.process_frame(_frame_with_pattern_at(roi, _pattern(2)))

    assert detections == ["B"]


def _shade_pattern(shade_grid, levels, size_scale=1):
    levels_arr = np.array(levels, dtype=np.uint8)
    img = levels_arr[shade_grid]
    if size_scale > 1:
        img = np.repeat(np.repeat(img, size_scale, axis=0), size_scale, axis=1)
    return img


# 20x20 grid (matching the ROI size used throughout these tests) using all 4
# shade indices in a fixed pseudo-random spatial pattern - dense enough that
# TM_CCOEFF_NORMED is actually sensitive to distortions between shades
# (a handful of flat quadrants correlate too robustly to be a meaningful
# test of anything other than a full inversion).
_TEST_SHADE_GRID = np.random.RandomState(42).randint(0, 4, size=(20, 20))


def test_negative_style_palette_still_detects_via_canonicalization():
    """A GBC "Negative" palette fully reverses which shade is lightest vs
    darkest. Raw grayscale matching can't recover from that (it scores
    strongly negative for an inverted match), but the canonical+inverted
    candidate in process_frame should."""
    roi = (0, 0, 20, 20)
    name = "A"
    template = _shade_pattern(_TEST_SHADE_GRID, (0, 85, 170, 255))
    live_crop = _shade_pattern(_TEST_SHADE_GRID, (255, 170, 85, 0))  # order reversed

    # Prove the fix is load-bearing: the raw score alone must already be
    # below threshold, or this test wouldn't be exercising the fix at all.
    raw_score = cv2.minMaxLoc(cv2.matchTemplate(live_crop, template, cv2.TM_CCOEFF_NORMED))[1]
    assert raw_score < THRESHOLD

    detector = DetectionService([(name, roi, template, 0)])
    detections = []
    detector.detection.connect(detections.append)

    detector.process_frame(_frame_with_pattern_at(roi, live_crop))

    assert detections == [name]


def test_low_contrast_palette_still_detects_via_canonicalization():
    """A low-contrast palette can compress two shades to near-identical
    luminance - a non-affine distortion relative to the template's even
    spacing that TM_CCOEFF_NORMED's linear-invariance can't paper over on
    the raw grayscale path, but rank canonicalization (which only cares
    about relative order, not spacing) can."""
    roi = (0, 0, 20, 20)
    name = "A"
    template = _shade_pattern(_TEST_SHADE_GRID, (0, 85, 170, 255))
    live_crop = _shade_pattern(_TEST_SHADE_GRID, (0, 16, 32, 255))  # shades 1-3 compressed together

    raw_score = cv2.minMaxLoc(cv2.matchTemplate(live_crop, template, cv2.TM_CCOEFF_NORMED))[1]
    assert raw_score < THRESHOLD

    detector = DetectionService([(name, roi, template, 0)])
    detections = []
    detector.detection.connect(detections.append)

    detector.process_frame(_frame_with_pattern_at(roi, live_crop))

    assert detections == [name]


def test_flat_crop_does_not_spuriously_match_via_canonicalization():
    """A blank/transition crop has no real 4-shade structure - canonicalize
    _shades correctly returns None for it (see tests/vision), and
    process_frame must not crash or fabricate a match when that happens."""
    roi = (0, 0, 20, 20)
    template = _shade_pattern(_TEST_SHADE_GRID, (0, 85, 170, 255))
    flat_crop = np.full((20, 20), 128, dtype=np.uint8)

    detector = DetectionService([("A", roi, template, 0)])
    detections = []
    detector.detection.connect(detections.append)

    detector.process_frame(_frame_with_pattern_at(roi, flat_crop))

    assert detections == []
