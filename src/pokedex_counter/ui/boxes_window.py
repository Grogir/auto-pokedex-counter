"""Window that tracks the team and the Pokemon stored in PC boxes."""
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLayout, QVBoxLayout, QWidget

from pokedex_counter.config import SPRITES_DIR
from pokedex_counter.game_config import (
    CAN_EVOLVE,
    POKEMON_NAME_TO_DEX,
    evolutions_of,
    previous_form_of,
)

TEAM_SIZE = 6
BOX_SIZE = 20
VISIBLE_BOXES = 7
SPRITE_SIZE = 25

# If True, all Pokemon will be displayed, otherwise we display those who need to evolve
DISPLAY_ALL = False

class ClickableIcon(QLabel):
    clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class BoxesWindow(QWidget):
    manual_caught = Signal(str)

    def __init__(
        self,
        sprites_dir: Path = SPRITES_DIR,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pokémon Boxes")
        self.setMinimumWidth(100)
        self._sprites_dir = sprites_dir
        self._sprite_width = SPRITE_SIZE
        self._sprite_height = SPRITE_SIZE
        self._sprite_padding = 0
        self.boxes: list[list[str]] = [[] for _ in range(VISIBLE_BOXES + 1)]
        self.team = self.boxes[0]
        self._current_box = 1
        self._found: set[str] = set()

        self._layout = QVBoxLayout(self)
        self._rows: list[tuple[str, QHBoxLayout, list[QWidget]]] = []
        self._count_labels: list[QLabel] = []
        self._build_rows()
        self._update_rows()

    def on_pokemon_found(self, name: str, evolved: bool = False) -> None:
        """Add a Pokemon to the team or boxes, if it is not already present. If it is an evolved form, replace the previous form in the team if present."""
        self._found.add(name)

        if evolved:
            previous_form = previous_form_of(name)
            for box in self.boxes:
                if previous_form in box:
                    if box is self.team or name in CAN_EVOLVE:
                        box[box.index(previous_form)] = name
                    else:
                        box.remove(previous_form)
                        box.append(name)
                    self._update_rows()
                    return

        if len(self.team) < TEAM_SIZE:
            self.team.append(name)
        else:
            if len(self.boxes[self._current_box]) >= BOX_SIZE:
                self.change_box(self._current_box + 1)
            self.boxes[self._current_box].insert(0, name)
        self._update_rows()

    def change_box(self, box_number: int | str) -> None:
        """Change the current box to deposit into. Box numbers are 1-indexed."""
        box_number = int(box_number)
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

    def swap(self, slots: str) -> None:
        slot1, sep, slot2 = slots.partition(",")
        if slot1 and sep and slot2:
            slot1 = int(slot1) - 1
            slot2 = int(slot2) - 1
            if 0 <= slot1 < len(self.team) and 0 <= slot2 < len(self.team):
                self.team[slot1], self.team[slot2] = self.team[slot2], self.team[slot1]
                self._update_rows()

    def reset(self) -> None:
        self.boxes = [[] for _ in range(VISIBLE_BOXES + 1)]
        self.team = self.boxes[0]
        self._current_box = 1
        self._found = set()
        self._update_rows()

    def on_manual_uncaught(self, name: str) -> None:
        """Remove every occurrence of `name` from the team and all boxes."""
        self._found.discard(name)
        for box in self.boxes:
            box[:] = [pokemon for pokemon in box if pokemon != name]
        self._update_rows()

    def set_sprite_size(self, size: int) -> None:
        self.set_sprite_dimensions(size, size)

    def set_sprites_dir(self, sprites_dir: Path) -> None:
        if sprites_dir == self._sprites_dir:
            return
        self._sprites_dir = sprites_dir
        self._update_rows()

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
        icon = ClickableIcon()
        icon.setProperty("pokemon_name", "")
        icon.setFixedSize(self._sprite_width, self._sprite_height)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"padding: {self._sprite_padding}px;")
        icon.clicked.connect(self._on_icon_clicked)
        slot_label = QLabel(self._slot_string(0, slot))
        slot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slot_layout.addWidget(icon)
        slot_layout.addWidget(slot_label)
        row.addWidget(slot_widget)
        row.addItem(stretch)
        slots.append(slot_widget)

    def _is_displayed(self, name: str) -> bool:
        """Return True if `name` needs to be evolved."""
        # return bool([evo for evo in evolutions_of(name) if evo not in self._found]) or DISPLAY_ALL
        return any(evo not in self._found for evo in evolutions_of(name)) or DISPLAY_ALL

    def _on_icon_clicked(self) -> None:
        icon = self.sender()
        if isinstance(icon, QLabel):
            evolutions = evolutions_of(icon.property("pokemon_name") or "")
            for evo in evolutions:
                if evo not in self._found:
                    self.manual_caught.emit(evo)
                    break

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
        return f"{slot_index}"

    def _draw_image(self, label: QLabel, name: str) -> None:
        label.clear()
        if not name:
            return

        pixmap = QPixmap(str(self._sprites_dir / f"{POKEMON_NAME_TO_DEX[name]}.png"))
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
