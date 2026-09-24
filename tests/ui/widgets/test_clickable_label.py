from pathlib import Path

import pytest

from pokedex_counter.config import (
    LABEL_COLOR_BONUS,
    LABEL_COLOR_CATCH,
    LABEL_COLOR_REQUIRED,
    LABEL_COLOR_SECTION_BONUS,
    LABEL_COLOR_WR_MARKED,
)
from pokedex_counter.ui.widgets.clickable_label import ClickableLabel


@pytest.fixture
def label(qtbot):
    lbl = ClickableLabel(Path("42.png"))
    qtbot.addWidget(lbl)
    return lbl


def test_select_then_deselect_round_trip(label):
    assert not label._selected

    label.select()
    assert label._selected

    label.deselect()
    assert not label._selected


def test_deselect_is_a_noop_when_not_selected(label, qtbot):
    with qtbot.assertNotEmitted(label.clicked):
        label.deselect()

    assert not label._selected


def test_deselect_does_not_emit_clicked(label, qtbot):
    label.select()

    with qtbot.assertNotEmitted(label.clicked):
        label.deselect()


def test_wr_mark_shows_blue_while_uncaught(label):
    label.set_wr_marked(True)

    assert f"background-color: {LABEL_COLOR_WR_MARKED};" in label.styleSheet()


def test_required_section_color_wins_over_wr_mark(label):
    label.set_wr_marked(True)
    label.set_section_color(LABEL_COLOR_REQUIRED)

    assert f"background-color: {LABEL_COLOR_REQUIRED};" in label.styleSheet()


def test_non_required_section_color_does_not_win_over_wr_mark(label):
    label.set_wr_marked(True)
    label.set_section_color(LABEL_COLOR_SECTION_BONUS)

    assert f"background-color: {LABEL_COLOR_WR_MARKED};" in label.styleSheet()


def test_catch_color_wins_over_the_wr_mark(label):
    """_apply_style favors the catch color over the WR mark, which is what
    lets SpriteStrip skip a separate unmark step when a marked sprite is
    caught - and what lets a bonus red show through on a WR-route sprite."""
    label.set_wr_marked(True)

    label.select(LABEL_COLOR_BONUS)

    assert f"background-color: {LABEL_COLOR_BONUS};" in label.styleSheet()


def test_set_catch_color_is_inert_on_an_uncaught_label(label):
    """SpriteStrip.set_bonus_names pushes a color at every label, caught or
    not. On an uncaught one that must neither repaint it nor survive into
    the next catch - select() always states the color it wants, so callers
    can't rely on a color pushed ahead of time."""
    label.set_catch_color(LABEL_COLOR_BONUS)
    assert "background-color" not in label.styleSheet()

    label.select()

    assert "background-color: black;" in label.styleSheet()


def test_deselect_drops_a_previous_catch_color(label):
    label.select(LABEL_COLOR_BONUS)
    label.deselect()

    assert "background-color" not in label.styleSheet()
