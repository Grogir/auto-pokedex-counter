"""Window that tracks the team and the Pokemon stored in PC boxes."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLayout, QVBoxLayout, QWidget

from pokedex_counter.config import SPRITES_DIR

TEAM_SIZE = 6
BOX_SIZE = 20
VISIBLE_BOXES = 7
SPRITE_SIZE = 25

# Only names in this set get a visible icon, so the window stays readable while still retaining the slot occupied by every Pokemon.
DISPLAYED_POKEMON = frozenset({"102", "29", "30", "23", "46", "92", "35", "33", "63", "147", "88", "77", "60", "61", "133", "79", "133", "133", "52", "138", "13", "14", "2", "69", "70", "56", "7", "8", "25", "100", "43", "44", "39", "104", "118", "84", "116", "140", "19", "11", "111", "4", "5", "17", "72", "37", "48", "58", "27", "96", "50", "41", "66", "74", "120", "98", "54", "90", "129", "86"})
DISPLAY_ALL = False  # If True, all Pokemon will be displayed, not just those in DISPLAYED_POKEMON.

class BoxesWindow(QWidget):
    def __init__(
        self,
        sprites_dir: Path = SPRITES_DIR,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pokémon Boxes")
        self.setMinimumWidth(100)
        self._sprites_dir = Path(sprites_dir)
        self._sprite_width = SPRITE_SIZE
        self._sprite_height = SPRITE_SIZE
        self._sprite_padding = 0
        self.boxes: list[list[str]] = [[] for _ in range(VISIBLE_BOXES + 1)]
        self.team = self.boxes[0]
        self._current_box = 1
        self._undisplayed_pokemon: set[str] = set()

        self._layout = QVBoxLayout(self)
        self._rows: list[tuple[str, QHBoxLayout, list[QWidget]]] = []
        self._count_labels: list[QLabel] = []
        self._build_rows()
        self._update_rows()

    def pokemon_found(self, name: str, evolved: bool = False) -> bool:
        """Add a Pokemon to the team or boxes, if it is not already present. If it is an evolved form, replace the previous form in the team if present."""
        self._handle_special_cases_before(name)
        previous = self.previous_form(name)
        if previous in DISPLAYED_POKEMON and previous != "133":
            self._undisplayed_pokemon.add(previous)

        if evolved:
            for box in self.boxes:
                if previous in box:
                    if box is self.team or name in DISPLAYED_POKEMON:
                        idx = box.index(previous)
                        box[idx] = name
                    else:
                        box.remove(previous)
                        box.append(name)
                    break
        else:
            if len(self.team) < TEAM_SIZE:
                self.team.append(name)
            else:
                if len(self.boxes[self._current_box]) >= BOX_SIZE:
                    self.change_box(self._current_box + 1)
                self.boxes[self._current_box].insert(0, name)

        self._handle_special_cases_after(name)
        self._update_rows()
        return True

    def previous_form(self, name: str) -> str | None:
        """Return the previous form of `name`, or None if it has no previous form."""
        if name == "135" or name == "136":
            return "133"
        return str(int(name) - 1)

    def _handle_special_cases_before(self, name: str) -> None:
        if self._current_box == 1 and name == "23":
            self.deposit("1")
            self.deposit("10")
            self.deposit("51")
        elif self._current_box == 1 and "115" in self.boxes[self._current_box] and name in ["86", "54", "98", "90", "120", "42", "55"]:
            self.change_box(2)
        elif self._current_box == 2 and "144" in self.boxes[self._current_box] and name in ["66", "74", "41", "95", "49", "75", "42", "67"]:
            self.change_box(3)
        elif self._current_box == 3 and name == "92":
            self.deposit("32")
            self.change_box(4)

    def _handle_special_cases_after(self, name: str) -> None:
        if self._current_box == 1 and name == "51":
            self.deposit("1")
            self.deposit("10")
            self.deposit("51")
        elif self._current_box == 1 and name == "23" and len(self.team) == 2:
            self.team[0], self.team[1] = self.team[1], self.team[0]
        elif self._current_box == 4 and name == "151":
            self.change_box(5)
        elif self._current_box == 5 and name == "7":
            self.deposit("16")
            if "47" in self.boxes[1]: # only deposit paras if we have parasect
                self.deposit("46")
            self.deposit("47")
            self.deposit("31")
            self.deposit("103")
            self.change_box(6)
        elif self._current_box == 6 and name == "138":
            self.change_box(7)

    def change_box(self, box_number: int) -> None:
        """Change the current box to deposit into. Box numbers are 1-indexed."""
        self._current_box = box_number
        while box_number >= len(self.boxes):
            self.boxes.append([])
            self._add_empty_row(f"Box {len(self.boxes) - 1}")
        self._update_rows()

    def deposit(self, name: str) -> bool:
        """Deposit a Pokemon into the current box, if it is in the team."""
        if name not in self.team:
            return False
        self.team.remove(name)
        self.boxes[self._current_box].append(name)
        self._update_rows()
        return True

    def reset(self) -> None:
        self.boxes = [[] for _ in range(VISIBLE_BOXES + 1)]
        self.team = self.boxes[0]
        self._current_box = 1
        self._undisplayed_pokemon = set()
        self._update_rows()

    def remove_pokemon(self, name: str) -> None:
        """Remove every occurrence of `name` from the team and all boxes."""
        for box in self.boxes:
            box[:] = [pokemon for pokemon in box if pokemon != name]
        previous = self.previous_form(name)
        if previous in self._undisplayed_pokemon:
            self._undisplayed_pokemon.discard(previous)
        self._update_rows()

    def set_sprite_size(self, size: int) -> None:
        self.set_sprite_dimensions(size, size)

    def set_sprite_dimensions(self, width: int, height: int) -> None:
        self._sprite_width = width
        self._sprite_height = height
        for _, _, slots in self._rows:
            for slot_widget in slots:
                icon = slot_widget.layout().itemAt(0).widget()
                icon.setFixedSize(width, height)
                self._draw_image(icon, icon.property("pokemon_name") or "")
        self._refresh_layout_geometry()

    def set_sprite_padding(self, padding: int) -> None:
        self._sprite_padding = padding
        for _, _, slots in self._rows:
            for slot_widget in slots:
                icon = slot_widget.layout().itemAt(0).widget()
                icon.setStyleSheet(f"padding: {padding}px;")
                self._draw_image(icon, icon.property("pokemon_name") or "")
        self._refresh_layout_geometry()

    def _refresh_layout_geometry(self) -> None:
        """Recalculate row and window geometry after changing sprite sizes."""
        self._layout.invalidate()
        for _, row, slots in self._rows:
            row.invalidate()
            for slot_widget in slots:
                slot_widget.layout().invalidate()
                slot_widget.adjustSize()
                icon = slot_widget.layout().itemAt(0).widget()
                slot_widget.setFixedWidth(icon.width())
                slot_widget.updateGeometry()
            row.activate()
        self._layout.activate()
        required_size = self._layout.sizeHint()
        self.setMinimumSize(max(100, required_size.width()), required_size.height())
        self.adjustSize()

    def _build_rows(self) -> None:
        self._add_empty_row("Team")
        for box_number in range(1, VISIBLE_BOXES + 1):
            self._add_empty_row(f"Box {box_number}")

    def _add_empty_row(self, title: str) -> None:
        row = QHBoxLayout()
        row.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        row.setSpacing(2)
        title_panel = QWidget()
        title_layout = QVBoxLayout(title_panel)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)
        title_label = QLabel(title)
        title_label.setFixedWidth(48)
        title_layout.addWidget(title_label)
        count_label = QLabel()
        count_label.setFixedWidth(48)
        count_label.setStyleSheet("color: gray;")
        title_layout.addWidget(count_label)
        row.addWidget(title_panel)
        self._count_labels.append(count_label)
        slots = []
        row.addStretch()
        self._layout.addLayout(row)
        self._rows.append((title, row, slots))

    def _add_slot(self, row: QHBoxLayout, slots: list[QWidget], slot: int) -> None:
        stretch = row.takeAt(row.count() - 1)
        slot_widget = QWidget()
        slot_layout = QVBoxLayout(slot_widget)
        slot_layout.setContentsMargins(0, 0, 0, 0)
        slot_layout.setSpacing(0)
        icon = QLabel()
        icon.setProperty("pokemon_name", "")
        icon.setFixedSize(self._sprite_width, self._sprite_height)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"padding: {self._sprite_padding}px;")
        slot_label = QLabel(self._slot_string(0, slot))
        slot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slot_layout.addWidget(icon)
        slot_layout.addWidget(slot_label)
        row.addWidget(slot_widget)
        row.addItem(stretch)
        slots.append(slot_widget)

    def _is_displayed(self, name: str) -> bool:
        """Return True if `name` is in the set of displayed Pokemon."""
        return (name in DISPLAYED_POKEMON and name not in self._undisplayed_pokemon) or DISPLAY_ALL

    def _update_rows(self) -> None:
        rows = self.boxes
        for row_index, (_, row, slots) in enumerate(self._rows):
            pokemon = rows[row_index] if row_index < len(rows) else []
            capacity = TEAM_SIZE if row_index == 0 else BOX_SIZE
            self._count_labels[row_index].setText(f"({len(pokemon)}/{capacity})")
            if row_index == 0 or DISPLAY_ALL:
                displayed = [
                    (slot, name)
                    for slot, name in enumerate(pokemon, start=1)
                    if self._is_displayed(name)
                ]
            else:
                displayed = [
                    (slot - sum(
                        self._is_displayed(previous_name)
                        for previous_name in pokemon[:slot - 1]
                    ), name)
                    for slot, name in enumerate(pokemon, start=1)
                    if self._is_displayed(name)
                ]
            while len(slots) < len(displayed):
                self._add_slot(row, slots, displayed[len(slots)][0])
            for slot, slot_widget in enumerate(slots):
                actual_slot, name = displayed[slot] if slot < len(displayed) else (0, "")
                slot_widget.setVisible(bool(name))
                icon = slot_widget.layout().itemAt(0).widget()
                icon.setProperty("pokemon_name", name)
                slot_label = slot_widget.layout().itemAt(1).widget()
                slot_label.setText(self._slot_string(row_index, actual_slot) if name else "")
                self._draw_image(icon, name)
            self.adjustSize()

    def _slot_string(self, row_index: int, slot_index: int) -> str:
        if row_index == 0 or slot_index <= 3:
            return f"{slot_index}"
        else:
            return f"1+{slot_index - 2}↓"

    def _draw_image(self, label: QLabel, name: str) -> None:
        label.clear()
        if not name:
            return

        pixmap = QPixmap(str(self._sprites_dir / f"{name}.png"))
        if pixmap.isNull():
            return
        width = self._sprite_width
        height = self._sprite_height
        if pixmap.width() > width or pixmap.height() > height:
            pixmap = pixmap.scaled(
            width,
            height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        canvas = QPixmap(width, height)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.drawPixmap((width - pixmap.width()) // 2, (height - pixmap.height()) // 2, pixmap)
        painter.end()
        label.setFixedSize(
            width + 2 * self._sprite_padding,
            height + 2 * self._sprite_padding,
        )
        label.setPixmap(canvas)
