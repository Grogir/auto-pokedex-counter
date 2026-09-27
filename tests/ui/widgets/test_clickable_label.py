from pathlib import Path

import pytest

from pokedex_counter.config import (
    LABEL_COLOR_BONUS,
    LABEL_COLOR_SECTION_REQUIRED,
    LABEL_COLOR_WR_AND_PLAYER,
    LABEL_COLOR_WR_ONLY,
)
from pokedex_counter.ui.widgets.clickable_label import ClickableLabel


@pytest.fixture
def label(qtbot):
    lbl = ClickableLabel(Path("42.png"))
    qtbot.addWidget(lbl)
    return lbl


def test_select_then_deselect_round_trip(label):
    assert not label._caught

    label.set_caught(True)
    assert label._caught

    label.set_caught(False)
    assert not label._caught


def test_wr_mark_shows_while_uncaught(label):
    label.set_wr(True)
    assert f"background-color: {LABEL_COLOR_WR_ONLY};" in label.styleSheet()


def test_required_section_color_wins_over_wr_mark(label):
    label.set_wr(True)
    label.set_section_state(required=True, bonus=False)
    assert f"background-color: {LABEL_COLOR_SECTION_REQUIRED};" in label.styleSheet()


def test_non_required_section_color_does_not_win_over_wr_mark(label):
    label.set_wr(True)
    label.set_section_state(required=False, bonus=True)

    assert f"background-color: {LABEL_COLOR_WR_ONLY};" in label.styleSheet()


def test_catch_color_with_wr_mark(label):
    """Bonus state wins over WR state once the sprite is caught."""
    label.set_wr(True)
    label.set_bonus(True)
    label.set_caught(True)
    assert f"background-color: {LABEL_COLOR_WR_AND_PLAYER};" in label.styleSheet()


def test_bonus_mark_is_inert_until_the_label_is_caught(label):
    label._apply_style()
    assert "background-color: transparent;" in label.styleSheet()

    label.set_bonus(True)
    assert "background-color: transparent;" in label.styleSheet()

    label.set_caught(True)
    assert f"background-color: {LABEL_COLOR_BONUS};" in label.styleSheet()


def test_deselect_drops_a_previous_catch_color(label):
    label.set_bonus(True)
    label.set_caught(True)
    label.set_caught(False)
    assert "background-color: transparent;" in label.styleSheet()
