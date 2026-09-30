"""run() itself needs a camera and a QApplication, so only the wiring
that's been hoisted out of it is exercised here - for the bonus highlight
that's the whole app-side contract: the checkbox drives the sprite strip,
and the state it was restored in is applied at startup rather than only on
the first toggle.

wire_found_pokemon carries the other half of it: the strip knows nothing
about sections, so app.py is where a find gets classified as a catch or an
evolution.
"""

import pytest
from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtWidgets import QApplication

from pokedex_counter.app import (
    wire_detection,
    wire_preferences,
    wire_ui_settings,
)
from pokedex_counter.boxes_window import BoxesWindow
from pokedex_counter.config import (
    LABEL_COLOR_BONUS,
    LABEL_COLOR_CATCH,
    SPRITES_DIR,
    SPRITES_DIRS,
)
from pokedex_counter.controllers.game_controller import GameController
from pokedex_counter.detection_config import DETECTION_TYPE
from pokedex_counter.game_config import BONUSES
from pokedex_counter.main_window import MainWindow
from pokedex_counter.services.calibration_service import CalibrationService
from pokedex_counter.services.detection_service import DetectionService
from pokedex_counter.settings_window import SettingsWindow
from tests.conftest import sections_for


class _IdleCaptureService(QObject):
    frame_ready = Signal(object)

    def __init__(self):
        super().__init__()
        self.running = False

    def isRunning(self):
        return self.running

    def start(self):
        self.running = True

    def stop(self):
        self.running = False


@pytest.fixture
def wired(qtbot):
    settings = SettingsWindow()
    window = MainWindow()
    qtbot.addWidget(settings)
    qtbot.addWidget(window)
    return settings, window


def test_checking_the_box_highlights_bonuses(wired):
    settings, window = wired
    wire_ui_settings(settings, window, BoxesWindow())
    pokemon = next(iter(BONUSES))
    window.sprite_strip.pokemon_found(pokemon)

    settings.highlight_bonuses_checkbox.setChecked(True)
    assert LABEL_COLOR_BONUS in window.sprite_strip._labels_by_name[pokemon].styleSheet()

    settings.highlight_bonuses_checkbox.setChecked(False)
    assert LABEL_COLOR_CATCH in window.sprite_strip._labels_by_name[pokemon].styleSheet()


def test_a_restored_checked_setting_applies_without_a_toggle(wired):
    """app.py restores the checkbox from QSettings before wiring it, so a
    session that had the setting on must come up highlighting already -
    waiting for a toggle would silently lose the preference."""
    settings, window = wired
    settings.highlight_bonuses_checkbox.setChecked(True)  # as restored from QSettings

    wire_ui_settings(settings, window, BoxesWindow())
    pokemon = next(iter(BONUSES))
    window.sprite_strip.pokemon_found(pokemon)

    assert LABEL_COLOR_BONUS in window.sprite_strip._labels_by_name[pokemon].styleSheet()


def test_starts_off_when_the_setting_is_off(wired):
    settings, window = wired

    wire_ui_settings(settings, window, BoxesWindow())
    pokemon = next(iter(BONUSES))
    window.sprite_strip.pokemon_found(pokemon)

    assert LABEL_COLOR_CATCH in window.sprite_strip._labels_by_name[pokemon].styleSheet()


def test_bottom_margin_setting_updates_main_window_height(wired):
    settings, window = wired
    wire_ui_settings(settings, window, BoxesWindow())

    settings.bottom_margin_spinbox.setValue(23)

    assert window._bottom_margin == 23


def test_detection_type_updates_detector_and_counter_calibration_state(wired, qtbot):
    settings, window = wired
    detector = DetectionService()
    detector.update_game_area(None)
    capture = _IdleCaptureService()
    wire_detection(
        GameController(), detector, capture, CalibrationService(), window,
        BoxesWindow(), settings,
    )

    assert detector._detection_type == DETECTION_TYPE["TEXT"]
    assert not window._calibrated

    settings.detection_type_combo.setCurrentIndex(0)

    assert detector._detection_type == DETECTION_TYPE["NONE"]
    assert window._calibrated

    settings.detection_type_combo.setCurrentIndex(2)

    assert detector._detection_type == DETECTION_TYPE["SPRITE"]
    assert not window._calibrated


def test_capture_follows_detection_mode_and_stays_active_during_none_calibration(wired):
    class FakeCapture(QObject):
        frame_ready = Signal(object)

        def __init__(self):
            super().__init__()
            self.running = False
            self.thread_active = False
            self.starts = 0
            self.stops = 0

        def isRunning(self):
            return self.thread_active

        def start(self):
            self.running = True
            self.starts += 1
            self.thread_active = True

        def stop(self):
            self.running = False
            self.stops += 1

    settings, window = wired
    settings.detection_type_combo.setCurrentIndex(DETECTION_TYPE["NONE"])
    capture = FakeCapture()
    calibration = CalibrationService(capture)
    apply_detection_type = wire_detection(
        GameController(), DetectionService(), capture, calibration, window,
        BoxesWindow(), settings,
    )

    assert capture.starts == 0
    assert capture.stops == 0

    settings.detection_type_combo.setCurrentIndex(DETECTION_TYPE["TEXT"])
    assert capture.running
    assert capture.starts == 1

    settings.detection_type_combo.setCurrentIndex(DETECTION_TYPE["NONE"])
    assert not capture.running
    assert capture.thread_active

    settings.detection_type_combo.setCurrentIndex(DETECTION_TYPE["TEXT"])
    assert capture.running
    assert capture.starts == 2

    calibration.active = True
    stops_before_calibration = capture.stops
    settings.detection_type_combo.setCurrentIndex(DETECTION_TYPE["NONE"])
    assert capture.running
    assert capture.stops == stops_before_calibration

    calibration.active = False
    apply_detection_type()
    assert not capture.running
    assert capture.stops == stops_before_calibration + 1


def test_detection_type_preference_is_restored_and_saved(wired, qtbot, tmp_path):
    settings, window = wired
    prefs = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    prefs.setValue("detection_type", DETECTION_TYPE["SPRITE"])

    wire_preferences(settings, window, BoxesWindow(), prefs, QApplication.instance())

    assert settings.detection_type_combo.currentData() == DETECTION_TYPE["SPRITE"]
    settings.detection_type_combo.setCurrentIndex(0)
    assert prefs.value("detection_type") == DETECTION_TYPE["NONE"]


def test_sprite_set_preference_updates_both_windows_and_is_saved(wired, qtbot, tmp_path):
    settings, window = wired
    boxes = BoxesWindow()
    prefs = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    prefs.setValue("sprite_set", 1)

    wire_ui_settings(settings, window, boxes)
    wire_preferences(settings, window, boxes, prefs, QApplication.instance())

    assert window.sprite_strip._folder == SPRITES_DIRS[0]
    assert boxes._sprites_dir == SPRITES_DIRS[0]

    settings.sprite_set_combo.setCurrentIndex(settings.sprite_set_combo.findData(2))

    assert window.sprite_strip._folder == SPRITES_DIRS[1]
    assert boxes._sprites_dir == SPRITES_DIRS[1]
    assert prefs.value("sprite_set", type=int) == 2


# --- found pokemon ---

# Raticate: catchable in the wild on this route, and also swept up as an
# evolution at the end of the run - so it exercises both classifications.
BOTH_WAYS = "RATICATE"


@pytest.fixture
def found_wiring(qtbot):
    controller = GameController()
    window = MainWindow()
    boxes = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(window)
    qtbot.addWidget(boxes)
    wire_detection(
        controller, DetectionService(), _IdleCaptureService(), CalibrationService(),
        window, boxes, SettingsWindow(),
    )
    return controller, window, boxes


def test_a_wild_catch_reaches_the_strip_as_a_catch(found_wiring, qtbot):
    controller, window, _ = found_wiring
    caught_in, _, _ = sections_for(BOTH_WAYS)

    controller.on_section_changed(caught_in)
    controller.on_detection(BOTH_WAYS)

    assert window.sprite_strip._labels_by_name[BOTH_WAYS]._caught
    assert not window.sprite_strip._labels_by_name[BOTH_WAYS]._evolved


def test_the_same_pokemon_reaches_the_strip_as_an_evolution_elsewhere(found_wiring):
    """Same dex number, different section - only the section it was found in
    says which of the two happened."""
    controller, window, _ = found_wiring
    _, evolved_in, _ = sections_for(BOTH_WAYS)

    controller.on_section_changed(evolved_in)
    controller.on_detection(BOTH_WAYS)

    assert window.sprite_strip._labels_by_name[BOTH_WAYS]._caught
    assert window.sprite_strip._labels_by_name[BOTH_WAYS]._evolved


@pytest.mark.parametrize(
    "section_kind, expected_color",
    [("caught", LABEL_COLOR_BONUS), ("evolved", LABEL_COLOR_CATCH)],
)
def test_manual_bonus_click_color_follows_the_active_section(
    found_wiring, section_kind, expected_color, qtbot
):
    controller, window, _ = found_wiring
    name = "PARASECT"
    caught_in, evolved_in, _ = sections_for(name)
    section = caught_in if section_kind == "caught" else evolved_in

    window.sprite_strip.set_bonus_names({name})
    controller.on_section_changed(section)

    window.sprite_strip._labels_by_name[name].show()
    qtbot.mouseClick(window.sprite_strip._labels_by_name[name], Qt.MouseButton.LeftButton)

    assert f"background-color: {expected_color};" in (
        window.sprite_strip._labels_by_name[name].styleSheet()
    )


def test_manual_sprite_click_and_unclick_reaches_boxes(qtbot):
    window = MainWindow()
    boxes = BoxesWindow(SPRITES_DIR)
    controller = GameController()
    qtbot.addWidget(window)
    qtbot.addWidget(boxes)
    wire_detection(
        controller, DetectionService(), _IdleCaptureService(), CalibrationService(),
        window, boxes, SettingsWindow(),
    )
    label = window.sprite_strip._labels_by_name["BULBASAUR"]

    label.show()
    qtbot.mouseClick(label, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(label, Qt.MouseButton.LeftButton)

    assert boxes.team == []
    assert boxes.boxes[1] == []
