"""Covers reset plus the sprite coloring rules, which are the strip's most
easily-broken behavior because three independent features paint the same
label background (see SpriteStrip._catch_color_for):

    blue   - on the WR route for a section already reached, not caught yet
    black  - caught, and nothing special about it
    green  - caught, but never on the WR route (only while comparing to WR)
    red    - caught (not evolved into), and listed in roi_config.BONUSES
             (only while "Highlight bonuses" is on)

Tests assert on the rendered stylesheet rather than the private
_catch_color, since a label that isn't selected keeps a catch color it
isn't currently showing.
"""

import re

import pytest
from PySide6.QtCore import Qt
from pokedex_counter.config import (
    LABEL_COLOR_BONUS,
    LABEL_COLOR_CATCH,
    LABEL_COLOR_OFF_ROUTE,
    LABEL_COLOR_WR_MARKED,
)

from pokedex_counter.config import SPRITES_DIR
from pokedex_counter.ui.widgets import sprite_strip as sprite_strip_module
from pokedex_counter.ui.widgets.sprite_strip import SpriteStrip


@pytest.fixture
def sprite_strip(qtbot):
    strip = SpriteStrip(SPRITES_DIR)
    qtbot.addWidget(strip)
    return strip


def color_of(strip: SpriteStrip, name: str) -> str | None:
    """The background color `name`'s label is actually rendering, or None
    when it's showing no highlight at all."""
    match = re.search(r"background-color:\s*(\w+);", strip._labels_by_name[name].styleSheet())
    return match.group(1) if match else None


def test_reset_deselects_everything_and_zeroes_the_count(sprite_strip):
    some_names = list(sprite_strip._labels_by_name)[:3]
    for name in some_names:
        sprite_strip.select_sprite(name)

    deselected = []
    sprite_strip.sprite_deselected.connect(deselected.append)

    sprite_strip.reset()

    assert all(not label._selected for label in sprite_strip._labels_by_name.values())
    assert not deselected


def test_reset_on_already_empty_strip_is_a_noop(sprite_strip):
    sprite_strip.reset()


def test_rectangular_dimensions_resize_sprite_labels(sprite_strip):
    label = sprite_strip._labels_by_name["1"]

    sprite_strip.set_sprite_dimensions(40, 30)

    assert label.size().width() == 40
    assert label.size().height() == 30
    assert label.pixmap().size().width() == 40
    assert label.pixmap().size().height() == 30


def test_padding_expands_sprite_labels_without_changing_icon_canvas(sprite_strip):
    label = sprite_strip._labels_by_name["1"]
    sprite_strip.set_sprite_dimensions(40, 30)

    sprite_strip.set_sprite_padding(5)

    assert label.size().width() == 50
    assert label.size().height() == 40
    assert label.pixmap().size().width() == 40
    assert label.pixmap().size().height() == 30


def test_reload_reuses_cached_pixmaps(qtbot, monkeypatch):
    sprite_strip = SpriteStrip(SPRITES_DIR, 64)
    qtbot.addWidget(sprite_strip)
    original_pixmap = sprite_strip_module.QPixmap
    loaded_paths = []
    sprite_strip._pixmap_cache.clear()

    def tracking_pixmap(*args):
        if len(args) == 1:
            loaded_paths.append(args[0])
        return original_pixmap(*args)

    monkeypatch.setattr(sprite_strip_module, "QPixmap", tracking_pixmap)

    sprite_strip.reload()
    first_load_count = len(loaded_paths)

    sprite_strip.reload()

    assert first_load_count > 0
    assert len(loaded_paths) == first_load_count


# --- WR comparison colors ---

def test_catch_is_black_when_no_feature_is_on(sprite_strip):
    sprite_strip.select_sprite("1")
    assert color_of(sprite_strip, "1") == LABEL_COLOR_CATCH


def test_wr_route_sprite_is_blue_until_it_is_caught(sprite_strip):
    sprite_strip.mark_wr_section({"1"})
    assert color_of(sprite_strip, "1") == LABEL_COLOR_WR_MARKED

    sprite_strip.select_sprite("1")
    assert color_of(sprite_strip, "1") == LABEL_COLOR_CATCH


def test_off_route_catch_is_green_while_comparing_to_wr(sprite_strip):
    sprite_strip.mark_wr_section({"1"})

    sprite_strip.select_sprite("4")

    assert color_of(sprite_strip, "4") == LABEL_COLOR_OFF_ROUTE


def test_returning_to_an_earlier_section_removes_future_wr_names(sprite_strip):
    sprite_strip.set_wr_names({"1", "4"})
    sprite_strip.set_wr_names({"1"})

    sprite_strip.select_sprite("4")

    assert color_of(sprite_strip, "4") == LABEL_COLOR_OFF_ROUTE


def test_wr_route_remains_active_after_the_last_section(sprite_strip):
    sprite_strip.set_wr_names({"1"})
    sprite_strip.set_current_section(set(), set())

    sprite_strip.select_sprite("4")

    assert color_of(sprite_strip, "4") == LABEL_COLOR_OFF_ROUTE


# --- bonus highlighting ---

def test_bonus_catch_is_red(sprite_strip):
    sprite_strip.set_bonus_names({"4"})

    sprite_strip.select_sprite("4")

    assert color_of(sprite_strip, "4") == LABEL_COLOR_BONUS


def test_bonus_is_not_highlighted_before_it_is_caught(sprite_strip):
    """Unlike a WR mark, a bonus is only a catch color - listing one must
    not pre-highlight it as something still to get."""
    sprite_strip.set_bonus_names({"4"})

    assert color_of(sprite_strip, "4") is None


def test_bonus_outranks_both_wr_catch_colors(sprite_strip):
    sprite_strip.set_bonus_names({"1", "4"})
    sprite_strip.mark_wr_section({"1"})  # 1 on route, 4 off it

    sprite_strip.select_sprite("1")
    sprite_strip.select_sprite("4")

    assert color_of(sprite_strip, "1") == LABEL_COLOR_BONUS
    assert color_of(sprite_strip, "4") == LABEL_COLOR_BONUS


def test_enabling_bonuses_recolors_catches_already_made(sprite_strip):
    sprite_strip.select_sprite("4")
    assert color_of(sprite_strip, "4") == LABEL_COLOR_CATCH

    sprite_strip.set_bonus_names({"4"})

    assert color_of(sprite_strip, "4") == LABEL_COLOR_BONUS


def test_disabling_bonuses_puts_catches_back_to_their_wr_color(sprite_strip):
    sprite_strip.mark_wr_section({"1"})
    sprite_strip.set_bonus_names({"1", "4"})
    sprite_strip.select_sprite("1")
    sprite_strip.select_sprite("4")

    sprite_strip.set_bonus_names(set())

    assert color_of(sprite_strip, "1") == LABEL_COLOR_CATCH  # on route
    assert color_of(sprite_strip, "4") == LABEL_COLOR_OFF_ROUTE  # off route


def test_reaching_a_bonus_wr_section_does_not_clobber_its_red(sprite_strip):
    """mark_wr_section retroactively corrects a catch made before its
    section came up. That correction has to respect bonus highlighting
    instead of forcing the on-route black."""
    sprite_strip.set_bonus_names({"4"})
    sprite_strip.mark_wr_section({"1"})
    sprite_strip.select_sprite("4")  # caught early, off route so far

    sprite_strip.mark_wr_section({"4"})  # its section arrives: on route after all

    assert color_of(sprite_strip, "4") == LABEL_COLOR_BONUS


def test_bonus_names_missing_from_the_strip_are_ignored(sprite_strip):
    """BONUSES is hand-edited and doesn't have to line up with the sprite
    folder, so an unknown entry must not blow up."""
    sprite_strip.set_bonus_names({"4", "not-a-sprite"})

    sprite_strip.select_sprite("4")

    assert color_of(sprite_strip, "4") == LABEL_COLOR_BONUS


def test_bonus_highlighting_survives_a_reset(sprite_strip):
    """reset() clears WR marks so a fresh run re-earns them section by
    section, but BONUSES is static - it stays on for the next run."""
    sprite_strip.set_bonus_names({"4"})
    sprite_strip.select_sprite("4")

    sprite_strip.reset()
    assert color_of(sprite_strip, "4") is None

    sprite_strip.select_sprite("4")
    assert color_of(sprite_strip, "4") == LABEL_COLOR_BONUS


# --- evolutions are not bonuses ---

def test_evolving_into_a_bonus_is_not_highlighted(sprite_strip):
    """Every bonus is an evolved form, so obtaining one says nothing on its
    own - only catching it in the wild is the bonus."""
    sprite_strip.set_bonus_names({"4"})

    sprite_strip.select_sprite("4", evolved=True)

    assert color_of(sprite_strip, "4") == LABEL_COLOR_CATCH


def test_an_evolved_bonus_stays_black_when_highlighting_is_turned_on_later(sprite_strip):
    """set_bonus_names recolors past catches, so it has to remember which of
    them were evolutions rather than re-deciding from the name alone."""
    sprite_strip.select_sprite("4", evolved=True)

    sprite_strip.set_bonus_names({"4"})

    assert color_of(sprite_strip, "4") == LABEL_COLOR_CATCH


def test_an_evolved_bonus_still_gets_its_wr_color(sprite_strip):
    """Suppressing the red must fall through to the normal catch colors, not
    force black."""
    sprite_strip.set_bonus_names({"4"})
    sprite_strip.mark_wr_section({"1"})  # 4 is off route

    sprite_strip.select_sprite("4", evolved=True)

    assert color_of(sprite_strip, "4") == LABEL_COLOR_OFF_ROUTE


def test_forgetting_an_evolved_sprite_lets_it_be_a_bonus_again(sprite_strip):
    sprite_strip.set_bonus_names({"4"})
    sprite_strip.select_sprite("4", evolved=True)

    sprite_strip.deselect_sprite("4")
    sprite_strip.select_sprite("4")

    assert color_of(sprite_strip, "4") == LABEL_COLOR_BONUS


def test_reset_forgets_that_a_bonus_was_evolved(sprite_strip):
    sprite_strip.set_bonus_names({"4"})
    sprite_strip.select_sprite("4", evolved=True)

    sprite_strip.reset()
    sprite_strip.select_sprite("4")

    assert color_of(sprite_strip, "4") == LABEL_COLOR_BONUS


# --- hand-clicked catches ---

def test_manual_click_gets_the_same_colors_a_detected_catch_gets(sprite_strip, qtbot):
    """A ClickableLabel can only paint itself black on click - it knows
    nothing about WR or bonus state - so the strip fixes the color up
    afterwards. Without that, hand-marking a catch the detector missed
    would mis-color it."""
    sprite_strip.set_bonus_names({"4"})
    sprite_strip.mark_wr_section({"1"})

    for name in ("1", "4", "7"):
        label = sprite_strip._labels_by_name[name]
        label.show()
        qtbot.mouseClick(label, Qt.MouseButton.LeftButton)

    assert color_of(sprite_strip, "4") == LABEL_COLOR_BONUS  # bonus
    assert color_of(sprite_strip, "1") == LABEL_COLOR_CATCH  # on route
    assert color_of(sprite_strip, "7") == LABEL_COLOR_OFF_ROUTE  # off route


def test_manual_unclick_clears_the_highlight_and_the_count(sprite_strip, qtbot):
    sprite_strip.set_bonus_names({"4"})
    label = sprite_strip._labels_by_name["4"]

    label.show()
    qtbot.mouseClick(label, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(label, Qt.MouseButton.LeftButton)

    assert color_of(sprite_strip, "4") is None
