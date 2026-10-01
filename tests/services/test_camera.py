"""Locks in find_camera_index()/resolve_camera_index()'s contract: match a
DirectShow device by name (case-insensitive substring), and fall back
cleanly both when the named device isn't present and when enumeration
itself fails (no DirectShow subsystem, driver issues, etc.).
"""

from pokedex_counter.services import camera_finder


class _FakeFilterGraph:
    def __init__(self, devices):
        self._devices = devices

    def get_input_devices(self):
        return self._devices


def _patch_devices(monkeypatch, devices):
    monkeypatch.setattr(camera_finder, "FilterGraph", lambda: _FakeFilterGraph(devices))


def test_finds_exact_name_match(monkeypatch):
    _patch_devices(monkeypatch, ["Game Capture 4K60 Pro MK.2", "USB 2.0 Camera", "OBS Virtual Camera"])

    assert camera_finder.find_camera_index("OBS Virtual Camera") == 2


def test_matches_case_insensitively_and_as_substring(monkeypatch):
    _patch_devices(monkeypatch, ["OBS-Camera", "obs virtual camera (DirectShow)"])

    assert camera_finder.find_camera_index("OBS Virtual Camera") == 1


def test_returns_none_when_not_found(monkeypatch):
    _patch_devices(monkeypatch, ["Game Capture 4K60 Pro MK.2", "USB 2.0 Camera"])

    assert camera_finder.find_camera_index("OBS Virtual Camera") is None


def test_returns_none_when_enumeration_raises(monkeypatch):
    def boom():
        raise OSError("no DirectShow subsystem")

    monkeypatch.setattr(camera_finder, "FilterGraph", boom)

    assert camera_finder.find_camera_index("OBS Virtual Camera") is None


def test_resolve_returns_found_index(monkeypatch):
    _patch_devices(monkeypatch, ["USB 2.0 Camera", "OBS Virtual Camera"])

    assert camera_finder.resolve_camera_index("OBS Virtual Camera", fallback=99) == 1


def test_resolve_falls_back_when_not_found(monkeypatch):
    _patch_devices(monkeypatch, ["USB 2.0 Camera"])

    assert camera_finder.resolve_camera_index("OBS Virtual Camera", fallback=7) == 7
