"""Locks in the behaviour run_calibration() relies on: writing freshly
calibrated ROIs back into roi_config.py's ROI_CATCH/ROI_EVOLVE/ROI_TEXT
constants in place, atomically, without disturbing the rest of the file.
"""

from pathlib import Path

import pytest

from pokedex_counter.roi_writer import update_roi_constants

ORIGINAL = '''ROI_CATCH = (348, 41, 99, 99)
ROI_EVOLVE = (263, 55, 99, 99)
ROI_TEXT = (335, 226, 111, 40)

ROI_CONFIG = [
    ["BULBASAUR", ROI_CATCH],
    ["VENUSAUR", ROI_EVOLVE],
]
'''


@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / "roi_config.py"
    path.write_text(ORIGINAL)
    return path


def test_updates_all_locked_constants(config_file):
    locked = {
        "CATCH": (383, 35, 127, 127),
        "EVOLVE": (275, 54, 126, 126),
        "TEXT": (367, 273, 140, 50),
    }

    updated = update_roi_constants(config_file, locked)

    assert set(updated) == {"ROI_CATCH", "ROI_EVOLVE", "ROI_TEXT"}
    text = config_file.read_text()
    assert "ROI_CATCH = (383, 35, 127, 127)" in text
    assert "ROI_EVOLVE = (275, 54, 126, 126)" in text
    assert "ROI_TEXT = (367, 273, 140, 50)" in text


def test_preserves_rest_of_file(config_file):
    update_roi_constants(config_file, {"CATCH": (1, 2, 3, 4)})

    text = config_file.read_text()
    assert 'ROI_CONFIG = [\n    ["BULBASAUR", ROI_CATCH],\n    ["VENUSAUR", ROI_EVOLVE],\n]' in text


def test_partial_lock_only_updates_given_keys(config_file):
    updated = update_roi_constants(config_file, {"EVOLVE": (9, 9, 9, 9)})

    assert updated == ["ROI_EVOLVE"]
    text = config_file.read_text()
    assert "ROI_EVOLVE = (9, 9, 9, 9)" in text
    assert "ROI_CATCH = (348, 41, 99, 99)" in text  # untouched
    assert "ROI_TEXT = (335, 226, 111, 40)" in text  # untouched


def test_replaces_none_placeholder_on_first_calibration(tmp_path):
    path = tmp_path / "roi_calibration.py"
    path.write_text("ROI_CATCH = None\nROI_EVOLVE = None\nROI_TEXT = None\n")

    updated = update_roi_constants(path, {"CATCH": (1, 2, 3, 4)})

    assert updated == ["ROI_CATCH"]
    text = path.read_text()
    assert "ROI_CATCH = (1, 2, 3, 4)" in text
    assert "ROI_EVOLVE = None" in text  # untouched
    assert "ROI_TEXT = None" in text  # untouched


def test_unknown_constant_name_is_skipped_not_crashed(config_file):
    updated = update_roi_constants(config_file, {"NOT_A_REAL_KEY": (1, 2, 3, 4)})

    assert updated == []
    assert config_file.read_text() == ORIGINAL


def test_missing_constant_in_file_warns_and_skips(tmp_path, capsys):
    path = tmp_path / "roi_config.py"
    path.write_text("ROI_CATCH = (1, 1, 1, 1)\n")

    updated = update_roi_constants(path, {"EVOLVE": (9, 9, 9, 9)})

    assert updated == []
    assert path.read_text() == "ROI_CATCH = (1, 1, 1, 1)\n"
    assert "could not find" in capsys.readouterr().out


def test_empty_locked_dict_leaves_file_untouched(config_file):
    updated = update_roi_constants(config_file, {})

    assert updated == []
    assert config_file.read_text() == ORIGINAL


def test_no_leftover_tmp_file(config_file):
    update_roi_constants(config_file, {"CATCH": (1, 2, 3, 4)})

    assert not config_file.with_suffix(".py.tmp").exists()
