"""SettingsWindow is a dumb view (all wiring lives in app.py), so what's
worth locking in is that each control exists, is labeled the way app.py's
QSettings keys and the user expect, and starts in the right state."""

import pytest
from PySide6.QtWidgets import QFormLayout

from pokedex_counter.settings_window import SettingsWindow


@pytest.fixture
def settings(qtbot):
    window = SettingsWindow()
    qtbot.addWidget(window)
    return window


def label_for(settings: SettingsWindow, widget) -> str:
    form = settings.findChild(QFormLayout)
    return form.labelForField(widget).text()


def test_highlight_bonuses_checkbox_is_labeled_and_starts_off(settings):
    assert label_for(settings, settings.highlight_bonuses_checkbox) == "Highlight bonuses"
    assert not settings.highlight_bonuses_checkbox.isChecked()


def test_compare_to_wr_checkbox_is_labeled_and_starts_off(settings):
    assert label_for(settings, settings.compare_to_wr_checkbox) == "Compare to WR?"
    assert not settings.compare_to_wr_checkbox.isChecked()


def test_the_two_highlight_settings_are_independent(settings):
    """Both paint the same sprite backgrounds but are separate toggles -
    neither checkbox may drag the other along."""
    settings.highlight_bonuses_checkbox.setChecked(True)

    assert not settings.compare_to_wr_checkbox.isChecked()


def test_sprite_dimensions_are_separate_and_start_equal(settings):
    assert settings.sprite_width_spinbox.value() == 24
    assert settings.sprite_height_spinbox.value() == 24
    assert label_for(settings, settings.sprite_width_spinbox) == "Sprite width:"
    assert label_for(settings, settings.sprite_height_spinbox) == "Sprite height:"


def test_bottom_margin_spinbox_is_labeled_and_starts_at_zero(settings):
    assert label_for(settings, settings.bottom_margin_spinbox) == "Bottom margin:"
    assert settings.bottom_margin_spinbox.value() == 0
    assert settings.bottom_margin_spinbox.minimum() == 0


def test_sprite_set_dropdown_lists_all_three_sets_and_defaults(settings):
    assert label_for(settings, settings.sprite_set_combo) == "Sprite set:"
    assert [settings.sprite_set_combo.itemData(index) for index in range(settings.sprite_set_combo.count())] == [1, 2, 3]
    assert settings.sprite_set_combo.currentData() == 2

