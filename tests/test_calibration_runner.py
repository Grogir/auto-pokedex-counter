"""Locks in the two things run_calibration() must guarantee beyond
what roi_writer.py already covers: it targets a writable location whether
running from source or frozen into an exe, and it returns the locked ROIs
so this session uses them in-memory even if persisting them to disk fails
(e.g. no writable roi_calibration.py next to a frozen exe).
"""

import sys
from pathlib import Path

from pokedex_counter import calibration_runner


def test_writable_roi_calibration_path_targets_package_when_not_frozen(monkeypatch):
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    path = calibration_runner._writable_roi_calibration_path()

    assert path == Path(calibration_runner.__file__).resolve().parent / "roi_calibration.py"


def test_writable_roi_calibration_path_targets_exe_dir_when_frozen(monkeypatch, tmp_path):
    fake_exe = tmp_path / "PokedexCounter.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))

    path = calibration_runner._writable_roi_calibration_path()

    assert path == tmp_path / "roi_calibration.py"


def test_ensure_seeded_creates_file_with_none_placeholders(tmp_path):
    config_path = tmp_path / "roi_calibration.py"
    calibration_runner._ensure_seeded(config_path)

    text = config_path.read_text()
    assert text == "GAME_AREA = None\n"


def test_ensure_seeded_leaves_existing_file_untouched(tmp_path):
    config_path = tmp_path / "roi_calibration.py"
    config_path.write_text("# custom content\n")

    calibration_runner._ensure_seeded(config_path)

    assert config_path.read_text() == "# custom content\n"


class _FakeCalibrationService:
    def __init__(self, camera_index):
        self.camera_index = camera_index

    def run(self, templates):
        return self._locked


def _fake_calibration_service(locked):
    def factory(camera_index):
        svc = _FakeCalibrationService(camera_index)
        svc._locked = locked
        return svc

    return factory


def test_run_calibration_returns_locked_rois_even_if_persistence_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(
        calibration_runner, "CalibrationService", _fake_calibration_service({"GAME_AREA": (1, 2, 3, 4)})
    )
    # Parent directory doesn't exist, so writing here always fails — proves
    # a persistence failure doesn't stop the locked ROIs being returned for
    # in-memory use this session.
    unwritable = tmp_path / "does" / "not" / "exist" / "roi_calibration.py"
    monkeypatch.setattr(calibration_runner, "_writable_roi_calibration_path", lambda: unwritable)

    locked = calibration_runner.run_calibration()

    assert locked == {"GAME_AREA": (1, 2, 3, 4)}
    assert not unwritable.exists()


def test_run_calibration_persists_when_writable(monkeypatch, tmp_path):
    monkeypatch.setattr(
        calibration_runner, "CalibrationService", _fake_calibration_service({"GAME_AREA": (9, 9, 9, 9)})
    )
    config_path = tmp_path / "roi_calibration.py"
    monkeypatch.setattr(calibration_runner, "_writable_roi_calibration_path", lambda: config_path)

    locked = calibration_runner.run_calibration()

    assert locked == {"GAME_AREA": (9, 9, 9, 9)}
    assert "GAME_AREA = (9, 9, 9, 9)" in config_path.read_text()


def test_run_calibration_returns_empty_dict_when_nothing_locked(monkeypatch):
    monkeypatch.setattr(calibration_runner, "CalibrationService", _fake_calibration_service({}))

    assert calibration_runner.run_calibration() == {}
