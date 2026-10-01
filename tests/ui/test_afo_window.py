import pytest

from pokedex_counter.game_config import ROUTE_SECTIONS
from pokedex_counter.ui.afo_window import (
    AVERAGE_EVO_TIME,
    CONSTANT_AFO_TIME,
    SPECIFIC_EVO_TIME,
    AfoWindow,
)


def test_initializes_with_a_copy_and_formats_total_time(qtbot):
    window = AfoWindow()
    qtbot.addWidget(window)

    assert window.evo_time == AVERAGE_EVO_TIME
    assert window.evo_time is not AVERAGE_EVO_TIME
    assert window.total_time == sum(AVERAGE_EVO_TIME.values()) + CONSTANT_AFO_TIME
    assert window.total_time_label.text().endswith(window.format_time(window.total_time))
    assert window.format_time(125.4) == "02:05"
    assert window.captured_evolutions_label.text().endswith(" 0")


def test_captured_evolution_counter_tracks_zero_evo_times(qtbot):
    window = AfoWindow()
    qtbot.addWidget(window)

    window.on_pokemon_found("RAPIDASH")

    assert window.evo_time["PONYTA"] == 0
    assert window.captured_evolutions_label.text().endswith(" 1")


def test_comparison_shows_signed_delta_in_seconds(qtbot):
    window = AfoWindow()
    qtbot.addWidget(window)

    assert "(" not in window.total_time_label.text()
    window.set_afo_comparison(round(window.total_time) - 33)
    assert window.total_time_label.text().endswith("(+33)")

    window.set_afo_comparison(round(window.total_time) + 18)
    assert window.total_time_label.text().endswith("(-18)")

    window.set_afo_comparison(round(window.total_time) - 60)
    assert window.total_time_label.text().endswith("(+01:00)")

    window.set_afo_comparison(round(window.total_time) + 60)
    assert window.total_time_label.text().endswith("(-01:00)")


def test_multiplier_of_one_applies_101_percent(qtbot):
    window = AfoWindow()
    qtbot.addWidget(window)
    base_total = window.total_time

    window.set_afo_multiplier(1)

    assert window.total_time == pytest.approx(base_total * 1.01)


def test_level_choices_and_selected_time(qtbot):
    window = AfoWindow()
    qtbot.addWidget(window)

    window.on_pokemon_found("PONYTA")

    assert set(window._level_buttons["PONYTA"]) == set(SPECIFIC_EVO_TIME["PONYTA"])
    assert all(not button.isHidden() for button in window._level_buttons["PONYTA"].values())

    window._level_buttons["PONYTA"][28].click()

    assert window.evo_time["PONYTA"] == 44.6
    assert window._labels["PONYTA"].text() == "Ponyta: L28"
    assert all(button.isHidden() for button in window._level_buttons["PONYTA"].values())


def test_only_pending_or_selected_level_rows_are_visible(qtbot):
    window = AfoWindow()
    qtbot.addWidget(window)

    assert all(row.isHidden() for row in window._labels.values())

    window.on_pokemon_found("PONYTA")

    assert not window._labels["PONYTA"].isHidden()
    assert window._labels["DODUO"].isHidden()
    buttons = window._level_buttons["PONYTA"].values()
    assert all(button.minimumWidth() == button.maximumWidth() == 44 for button in buttons)

    window._level_buttons["PONYTA"][28].click()

    assert not window._labels["PONYTA"].isHidden()
    assert all(button.isHidden() for button in window._level_buttons["PONYTA"].values())




def test_window_shrinks_when_a_level_row_is_removed(qtbot):
    window = AfoWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(0)
    initial_height = window.height()

    window.on_pokemon_found("PONYTA")
    qtbot.wait(0)
    expanded_height = window.height()

    window.on_manual_uncaught("PONYTA")
    qtbot.wait(0)

    assert expanded_height > initial_height
    assert window.height() == initial_height


def test_uncatching_evolution_restores_average(qtbot):
    window = AfoWindow()
    qtbot.addWidget(window)
    window.on_pokemon_found("RAPIDASH")
    assert window.evo_time["PONYTA"] == 0

    window.on_manual_uncaught("RAPIDASH")
    assert window.evo_time["PONYTA"] == AVERAGE_EVO_TIME["PONYTA"]


def test_uncatching_before_level_selection_restores_average(qtbot):
    window = AfoWindow()
    qtbot.addWidget(window)
    window.on_pokemon_found("RAPIDASH", evolved=True)

    window.on_manual_uncaught("RAPIDASH")

    assert window.evo_time["PONYTA"] == AVERAGE_EVO_TIME["PONYTA"]
    assert all(button.isHidden() for button in window._level_buttons["PONYTA"].values())


def test_late_route_evolution_does_not_change_prediction(qtbot):
    section = len(ROUTE_SECTIONS) - 1
    window = AfoWindow(lambda: section)
    qtbot.addWidget(window)
    original_total = window.total_time

    window.on_pokemon_found("RAPIDASH", evolved=True)

    assert window.evo_time["PONYTA"] == AVERAGE_EVO_TIME["PONYTA"]
    assert window.total_time == original_total
    assert not any(button.isVisible() for button in window._level_buttons["PONYTA"].values())


def test_reset_restores_all_average_values_and_clears_pending_choices(qtbot):
    window = AfoWindow()
    qtbot.addWidget(window)
    window.on_pokemon_found("RAPIDASH", evolved=True)
    window._level_buttons["PONYTA"][28].click()
    window.on_pokemon_found("ELECTRODE", evolved=True)

    window.reset()

    assert window.evo_time == AVERAGE_EVO_TIME
    assert window._selected_levels == {}
    assert window._awaiting_level == set()
    assert all(
        button.isHidden()
        for buttons in window._level_buttons.values()
        for button in buttons.values()
    )
