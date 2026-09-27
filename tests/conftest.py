"""Shared pytest fixtures. pytest-qt provides the `qtbot` fixture automatically."""

import pytest

from pokedex_counter.detection_config import DETECTION_IMAGE_TEXT_NAMES
from pokedex_counter.game_config import FINAL_SECTION, ROUTE_SECTIONS
from pokedex_counter.main_window import MainWindow


@pytest.fixture
def main_window(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def sections_for(name: str) -> tuple[int, int]:
    """(a section where `name` is caught, one where it's evolved into), read
    out of the real route so these stay honest if it gets re-authored."""
    caught = next(
        (i for i, s in enumerate(ROUTE_SECTIONS) if name in s.required or name in s.bonuses),
        None
    )
    evolved = next(
        (i for i, s in enumerate(ROUTE_SECTIONS) if name in s.evolutions),
        len(ROUTE_SECTIONS) if name in FINAL_SECTION else None,
    )
    text = next(
        (i for i, s in enumerate(ROUTE_SECTIONS) if name in s.required and name in DETECTION_IMAGE_TEXT_NAMES),
        None
    )
    return caught, evolved, text
