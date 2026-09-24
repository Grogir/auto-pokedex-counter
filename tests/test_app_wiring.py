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
    wire_bonus_highlight,
    wire_found_pokemon,
)
from pokedex_counter.boxes_window import BoxesWindow
from pokedex_counter.config import LABEL_COLOR_BONUS, LABEL_COLOR_CATCH, SPRITES_DIR
from pokedex_counter.controllers.game_controller import GameController
from pokedex_counter.roi_config import CATCH_SECTIONS
from pokedex_counter.settings_window import SettingsWindow
from pokedex_counter.ui.widgets.sprite_strip import SpriteStrip

BONUSES = {"CHARMANDER"}


@pytest.fixture
def wired(qtbot):
    settings = SettingsWindow()
    strip = SpriteStrip(SPRITES_DIR)
    qtbot.addWidget(settings)
    qtbot.addWidget(strip)
    return settings, strip


def test_checking_the_box_highlights_bonuses(wired):
    settings, strip = wired
    wire_bonus_highlight(settings, strip, BONUSES)

    settings.highlight_bonuses_checkbox.setChecked(True)

    assert strip._bonus_names == BONUSES


def test_unchecking_the_box_turns_highlighting_off(wired):
    settings, strip = wired
    wire_bonus_highlight(settings, strip, BONUSES)
    settings.highlight_bonuses_checkbox.setChecked(True)

    settings.highlight_bonuses_checkbox.setChecked(False)

    assert strip._bonus_names == set()


def test_a_restored_checked_setting_applies_without_a_toggle(wired):
    """app.py restores the checkbox from QSettings before wiring it, so a
    session that had the setting on must come up highlighting already -
    waiting for a toggle would silently lose the preference."""
    settings, strip = wired
    settings.highlight_bonuses_checkbox.setChecked(True)  # as restored from QSettings

    wire_bonus_highlight(settings, strip, BONUSES)

    assert strip._bonus_names == BONUSES


def test_starts_off_when_the_setting_is_off(wired):
    settings, strip = wired

    wire_bonus_highlight(settings, strip, BONUSES)

    assert strip._bonus_names == set()


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
    wire_found_pokemon(controller, strip, boxes)
    return controller, strip, boxes


def _sections_for(name: str) -> tuple[int, int]:
    """(a section where `name` is caught, one where it's evolved into), read
    out of the real route so these stay honest if it gets re-authored."""
    caught = next(i for i, s in enumerate(CATCH_SECTIONS) if (name, "CATCH") in s)
    evolved = next(i for i, s in enumerate(CATCH_SECTIONS) if (name, "EVOLVE") in s)
    return caught, evolved


def test_a_wild_catch_reaches_the_strip_as_a_catch(found_wiring):
    controller, strip, _ = found_wiring
    caught_in, _ = _sections_for(BOTH_WAYS)

    controller.on_section_changed(caught_in)
    controller.on_detection(BOTH_WAYS)

    assert strip._labels_by_name[BOTH_WAYS]._selected
    assert BOTH_WAYS not in strip._evolved_names


def test_the_same_pokemon_reaches_the_strip_as_an_evolution_elsewhere(found_wiring):
    """Same dex number, different section - only the section it was found in
    says which of the two happened."""
    controller, strip, _ = found_wiring
    _, evolved_in = _sections_for(BOTH_WAYS)

    controller.on_section_changed(evolved_in)
    controller.on_detection(BOTH_WAYS)

    assert strip._labels_by_name[BOTH_WAYS]._selected
    assert BOTH_WAYS in strip._evolved_names


@pytest.mark.parametrize(
    "section_kind, expected_color",
    [("caught", LABEL_COLOR_BONUS), ("evolved", LABEL_COLOR_CATCH)],
)
def test_manual_bonus_click_color_follows_the_active_section(
    found_wiring, section_kind, expected_color, qtbot
):
    controller, strip, boxes = found_wiring
    name = "PARASECT"
    caught_in, evolved_in = _sections_for(name)
    section = caught_in if section_kind == "caught" else evolved_in

    strip.set_bonus_names({name})
    wire_found_pokemon(controller, strip, boxes)
    strip.sprite_selected.connect(controller.on_detection)
    controller.on_section_changed(section)

    strip._labels_by_name[name].show()
    qtbot.mouseClick(strip._labels_by_name[name], Qt.MouseButton.LeftButton)

    assert f"background-color: {expected_color};" in (
        strip._labels_by_name[name].styleSheet()
    )


def test_manual_sprite_click_reaches_boxes_but_unclick_does_not(qtbot):
    strip = SpriteStrip(SPRITES_DIR)
    boxes = BoxesWindow(SPRITES_DIR)
    controller = GameController()
    qtbot.addWidget(strip)
    qtbot.addWidget(boxes)
    wire_found_pokemon(controller, strip, boxes)
    strip.sprite_selected.connect(controller.on_detection)
    label = strip._labels_by_name["BULBASAUR"]

    label.show()
    qtbot.mouseClick(label, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(label, Qt.MouseButton.LeftButton)

    assert boxes.team == []
    assert boxes.boxes[1] == []
