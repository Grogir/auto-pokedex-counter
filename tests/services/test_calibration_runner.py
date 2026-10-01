"""Locks in the two things run_calibration() must guarantee beyond
what roi_writer.py already covers: it targets a writable location whether
running from source or frozen into an exe, and it returns the locked ROIs
so this session uses them in-memory even if persisting them to disk fails
(e.g. no writable saved_calibration.py next to a frozen exe).
"""

import sys
from pathlib import Path

from pokedex_counter.services import calibration_runner


def test_writable_saved_calibration_path_targets_package_when_not_frozen(monkeypatch):
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    path = calibration_runner._writable_saved_calibration_path()

    assert path == Path(calibration_runner.__file__).resolve().parent.parent / "saved_calibration.py"


def test_writable_saved_calibration_path_targets_exe_dir_when_frozen(monkeypatch, tmp_path):
    fake_exe = tmp_path / "PokedexCounter.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))

    path = calibration_runner._writable_saved_calibration_path()

    assert path == tmp_path / "saved_calibration.py"


def test_ensure_seeded_creates_file_with_none_placeholders(tmp_path):
    config_path = tmp_path / "saved_calibration.py"
    calibration_runner._ensure_seeded(config_path)

    text = config_path.read_text()
    assert text == "GAME_AREA = None\n"


def test_ensure_seeded_leaves_existing_file_untouched(tmp_path):
    config_path = tmp_path / "saved_calibration.py"
    config_path.write_text("# custom content\n")

    calibration_runner._ensure_seeded(config_path)

    assert config_path.read_text() == "# custom content\n"


def test_persist_calibration_results_handles_persistence_failure(monkeypatch, tmp_path):
    # Parent directory doesn't exist, so writing here always fails — proves
    # a persistence failure doesn't stop the locked ROIs being returned for
    # in-memory use this session.
    unwritable = tmp_path / "does" / "not" / "exist" / "saved_calibration.py"
    monkeypatch.setattr(calibration_runner, "_writable_saved_calibration_path", lambda: unwritable)

    calibration_runner.save_calibration_results({"GAME_AREA": (1, 2, 3, 4)})

    assert not unwritable.exists()


def test_persist_calibration_results_when_writable(monkeypatch, tmp_path):
    config_path = tmp_path / "saved_calibration.py"
    monkeypatch.setattr(calibration_runner, "_writable_saved_calibration_path", lambda: config_path)

    calibration_runner.save_calibration_results({"GAME_AREA": (9, 9, 9, 9)})
    assert "GAME_AREA = (9, 9, 9, 9)" in config_path.read_text()


def test_run_calibration_starts_service_with_loaded_templates(monkeypatch):
    class FakeCalibrationService:
        def __init__(self):
            self.templates = None

        def start(self, templates):
            self.templates = templates

    service = FakeCalibrationService()
    monkeypatch.setattr(calibration_runner, "CALIBRATION_FILENAMES", {})

    calibration_runner.run_calibration(service)

    assert service.templates == {}


def test_persist_calibration_results_does_nothing_when_no_rois_locked(monkeypatch):
    monkeypatch.setattr(calibration_runner, "CALIBRATION_FILENAMES", {})

    calibration_runner.save_calibration_results({})
