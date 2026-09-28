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
from PySide6.QtCore import Qt

from pokedex_counter.app import (
    wire_detection,
    wire_ui_settings,
)
from pokedex_counter.boxes_window import BoxesWindow
from pokedex_counter.config import LABEL_COLOR_BONUS, LABEL_COLOR_CATCH, SPRITES_DIR
from pokedex_counter.controllers.game_controller import GameController
from pokedex_counter.game_config import BONUSES
from pokedex_counter.main_window import MainWindow
from pokedex_counter.services.capture_service import CaptureService
from pokedex_counter.services.detection_service import DetectionService
from pokedex_counter.settings_window import SettingsWindow
from pokedex_counter.ui.widgets.sprite_strip import SpriteStrip
from tests.conftest import sections_for


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


# --- found pokemon ---

# Raticate: catchable in the wild on this route, and also swept up as an
# evolution at the end of the run - so it exercises both classifications.
BOTH_WAYS = "RATICATE"


@pytest.fixture
def found_wiring(qtbot):
    controller = GameController()
    strip = SpriteStrip(SPRITES_DIR)
    boxes = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(strip)
    qtbot.addWidget(boxes)
    wire_detection(controller, DetectionService(), CaptureService(), strip, boxes)
    return controller, strip, boxes


def test_a_wild_catch_reaches_the_strip_as_a_catch(found_wiring):
    controller, strip, _ = found_wiring
    caught_in, _, _ = sections_for(BOTH_WAYS)

    controller.on_section_changed(caught_in)
    controller.on_detection(BOTH_WAYS)

    assert strip._labels_by_name[BOTH_WAYS]._caught
    assert not strip._labels_by_name[BOTH_WAYS]._evolved


def test_the_same_pokemon_reaches_the_strip_as_an_evolution_elsewhere(found_wiring):
    """Same dex number, different section - only the section it was found in
    says which of the two happened."""
    controller, strip, _ = found_wiring
    _, evolved_in, _ = sections_for(BOTH_WAYS)

    controller.on_section_changed(evolved_in)
    controller.on_detection(BOTH_WAYS)

    assert strip._labels_by_name[BOTH_WAYS]._caught
    assert strip._labels_by_name[BOTH_WAYS]._evolved


@pytest.mark.parametrize(
    "section_kind, expected_color",
    [("caught", LABEL_COLOR_BONUS), ("evolved", LABEL_COLOR_CATCH)],
)
def test_manual_bonus_click_color_follows_the_active_section(
    found_wiring, section_kind, expected_color, qtbot
):
    controller, strip, _ = found_wiring
    name = "PARASECT"
    caught_in, evolved_in, _ = sections_for(name)
    section = caught_in if section_kind == "caught" else evolved_in

    strip.set_bonus_names({name})
    controller.on_section_changed(section)

    strip._labels_by_name[name].show()
    qtbot.mouseClick(strip._labels_by_name[name], Qt.MouseButton.LeftButton)

    assert f"background-color: {expected_color};" in (
        strip._labels_by_name[name].styleSheet()
    )


def test_manual_sprite_click_and_unclick_reaches_boxes(qtbot):
    strip = SpriteStrip(SPRITES_DIR)
    boxes = BoxesWindow(SPRITES_DIR)
    controller = GameController()
    qtbot.addWidget(strip)
    qtbot.addWidget(boxes)
    wire_detection(controller, DetectionService(), CaptureService(), strip, boxes)
    label = strip._labels_by_name["BULBASAUR"]

    label.show()
    qtbot.mouseClick(label, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(label, Qt.MouseButton.LeftButton)

    assert boxes.team == []
    assert boxes.boxes[1] == []
