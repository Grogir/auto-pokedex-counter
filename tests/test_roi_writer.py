"""Locks in atomic persistence of the calibrated full-game ROI."""

from pathlib import Path

import pytest

from pokedex_counter.roi_writer import update_roi_constants

ORIGINAL = '''GAME_AREA = (348, 41, 99, 99)

ROI_CONFIG = [
    ["BULBASAUR", GAME_AREA],
]
'''


@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / "roi_config.py"
    path.write_text(ORIGINAL)
    return path


def test_updates_full_constant(config_file):
    locked = {"GAME_AREA": (383, 35, 127, 127)}

    updated = update_roi_constants(config_file, locked)

    assert updated == ["GAME_AREA"]
    text = config_file.read_text()
    assert "GAME_AREA = (383, 35, 127, 127)" in text


def test_preserves_rest_of_file(config_file):
    update_roi_constants(config_file, {"GAME_AREA": (1, 2, 3, 4)})

    text = config_file.read_text()
    assert 'ROI_CONFIG = [\n    ["BULBASAUR", GAME_AREA],\n]' in text


def test_replaces_none_placeholder_on_first_calibration(tmp_path):
    path = tmp_path / "roi_calibration.py"
    path.write_text("GAME_AREA = None\n")

    updated = update_roi_constants(path, {"GAME_AREA": (1, 2, 3, 4)})

    assert updated == ["GAME_AREA"]
    text = path.read_text()
    assert "GAME_AREA = (1, 2, 3, 4)" in text


def test_unknown_constant_name_is_skipped_not_crashed(config_file):
    updated = update_roi_constants(config_file, {"NOT_A_REAL_KEY": (1, 2, 3, 4)})

    assert updated == []
    assert config_file.read_text() == ORIGINAL


def test_missing_constant_in_file_warns_and_skips(tmp_path, capsys):
    path = tmp_path / "roi_config.py"
    path.write_text("ROI_OTHER = (1, 1, 1, 1)\n")

    updated = update_roi_constants(path, {"GAME_AREA": (9, 9, 9, 9)})

    assert updated == []
    assert path.read_text() == "ROI_OTHER = (1, 1, 1, 1)\n"
    assert "could not find" in capsys.readouterr().out


def test_empty_locked_dict_leaves_file_untouched(config_file):
    updated = update_roi_constants(config_file, {})

    assert updated == []
    assert config_file.read_text() == ORIGINAL


def test_no_leftover_tmp_file(config_file):
    update_roi_constants(config_file, {"GAME_AREA": (1, 2, 3, 4)})

    assert not config_file.with_suffix(".py.tmp").exists()
