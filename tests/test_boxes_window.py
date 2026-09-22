import pokedex_counter.boxes_window as boxes_module
from pokedex_counter.boxes_window import BOX_SIZE, TEAM_SIZE, BoxesWindow
from pokedex_counter.config import SPRITES_DIR


def test_first_six_non_evolutions_go_to_team_then_boxes(qtbot):
    window = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(window)

    for name in map(str, range(1, TEAM_SIZE + 2)):
        window.pokemon_found(name)

    assert window.boxes[0] == ["1", "2", "3", "4", "5", "6"]
    assert window.team is window.boxes[0]
    assert window.boxes[1] == ["7"]
    assert len(window.boxes) == 1 + 7


def test_full_box_starts_the_next_box(qtbot):
    window = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(window)

    for name in map(str, range(1, TEAM_SIZE + BOX_SIZE + 2)):
        window.pokemon_found(name)

    assert len(window.boxes[1]) == BOX_SIZE
    assert window.boxes[2] == [str(TEAM_SIZE + BOX_SIZE + 1)]


def test_evolution_is_remembered_but_not_assigned_a_slot(qtbot):
    window = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(window)

    window.pokemon_found("1")
    window.pokemon_found("2", evolved=True)

    assert window.boxes[0] == ["2"]
    assert len(window.boxes) == 1 + 7
    assert all(not box for box in window.boxes[1:])


def test_hidden_pokemon_keeps_the_real_slot_number(qtbot, monkeypatch):
    monkeypatch.setattr(boxes_module, "DISPLAYED_POKEMON", frozenset({"10", "70"}))
    window = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(window)

    for name in map(str, range(10, 10 * (TEAM_SIZE + 3), 10)):
        window.pokemon_found(name)

    box_layout = window._rows[1][1]
    visible_slot = box_layout.itemAt(1).widget()
    slot_label = visible_slot.layout().itemAt(1).widget()

    assert window.boxes[1] == ["80", "70"]
    assert "2" in slot_label.text()
    assert box_layout.count() == 3  # title, visible slot 2, stretch


def test_box_slot_labels_skip_displayed_pokemon(qtbot, monkeypatch):
    monkeypatch.setattr(boxes_module, "DISPLAYED_POKEMON", frozenset({"7", "8"}))
    window = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(window)
    window.boxes[1].extend(["hidden-1", "7", "hidden-2", "8"])
    window._update_rows()

    slots = window._rows[1][2]
    labels = [slot.layout().itemAt(1).widget().text() for slot in slots]

    assert labels == ["2", "3"]


def test_team_slot_labels_keep_their_physical_positions(qtbot, monkeypatch):
    monkeypatch.setattr(boxes_module, "DISPLAYED_POKEMON", frozenset({"7", "8"}))
    window = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(window)
    window.boxes[0].extend(["hidden-1", "7", "hidden-2", "8"])
    window._update_rows()

    slots = window._rows[0][2]
    labels = [slot.layout().itemAt(1).widget().text() for slot in slots]

    assert labels == ["2", "4"]


def test_resize_updates_existing_icon_widgets(qtbot, monkeypatch):
    monkeypatch.setattr(boxes_module, "DISPLAYED_POKEMON", frozenset({"1"}))
    window = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(window)
    window.pokemon_found("1")
    icon = window._rows[0][2][0].layout().itemAt(0).widget()

    window.set_sprite_size(40)

    assert window._rows[0][2][0].layout().itemAt(0).widget() is icon
    assert icon.size().width() == 40


def test_rectangular_dimensions_resize_existing_box_icon(qtbot, monkeypatch):
    monkeypatch.setattr(boxes_module, "DISPLAYED_POKEMON", frozenset({"1"}))
    window = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(window)
    window.pokemon_found("1")
    icon = window._rows[0][2][0].layout().itemAt(0).widget()

    window.set_sprite_dimensions(40, 30)

    assert icon.size().width() == 40
    assert icon.size().height() == 30


def test_padding_expands_existing_box_icon_label(qtbot, monkeypatch):
    monkeypatch.setattr(boxes_module, "DISPLAYED_POKEMON", frozenset({"1"}))
    window = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(window)
    window.pokemon_found("1")
    icon = window._rows[0][2][0].layout().itemAt(0).widget()

    window.set_sprite_dimensions(40, 30)
    window.set_sprite_padding(5)

    assert icon.size().width() == 50
    assert icon.size().height() == 40
    assert icon.pixmap().size().width() == 40
    assert icon.pixmap().size().height() == 30


def test_resize_recalculates_geometry_for_a_populated_window(qtbot, monkeypatch):
    monkeypatch.setattr(boxes_module, "DISPLAYED_POKEMON", frozenset({"1", "7"}))
    window = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(window)

    window.team.extend(["1"] * TEAM_SIZE)
    window.boxes[1].extend(["7"] * BOX_SIZE)
    window._update_rows()
    window.set_sprite_dimensions(40, 30)
    window.set_sprite_padding(5)
    qtbot.wait(0)

    slots = [
        slot
        for _, _, row_slots in window._rows
        for slot in row_slots
        if slot.layout().itemAt(0).widget().property("pokemon_name")
    ]
    assert slots
    assert all(
        slot.geometry().width() >= 50 and slot.geometry().height() >= 40
        for slot in slots
    )
    assert window.width() >= window.minimumWidth()


def test_empty_team_and_seven_boxes_are_visible(qtbot):
    window = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(window)

    assert len(window._rows) == 1 + 7
    assert [title for title, _, _ in window._rows] == [
        "Team", "Box 1", "Box 2", "Box 3", "Box 4", "Box 5", "Box 6", "Box 7"
    ]


def test_reset_clears_history_team_and_boxes(qtbot):
    window = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(window)
    window.pokemon_found("1")
    window.pokemon_found("20", evolved=True)

    window.reset()

    assert window.boxes[0] == []
    assert len(window.boxes) == 1 + 7
    assert all(not box for box in window.boxes)


def test_counts_include_hidden_pokemon(qtbot, monkeypatch):
    monkeypatch.setattr(boxes_module, "DISPLAYED_POKEMON", frozenset({"1"}))
    window = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(window)

    for name in map(str, range(1, TEAM_SIZE + 3)):
        window.pokemon_found(name)

    team_count = window._rows[0][1].itemAt(0).widget().layout().itemAt(1).widget()
    box_count = window._rows[1][1].itemAt(0).widget().layout().itemAt(1).widget()
    assert team_count.text() == "(6/6)"
    assert box_count.text() == "(2/20)"


def test_remove_pokemon_removes_all_occurrences(qtbot):
    window = BoxesWindow(SPRITES_DIR)
    qtbot.addWidget(window)
    window.boxes[0].extend(["20", "20"])
    window.boxes[1].extend(["20", "21"])
    window._update_rows()

    window.remove_pokemon("20")

    assert window.boxes[0] == []
    assert window.boxes[1] == ["21"]
