"""Widget that displays every image in a folder, wrapping onto new rows as the
window is resized."""
import re
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QSizePolicy,
    QWidget,
)

from pokedex_counter.game_config import POKEMON_DEX_TO_NAME
from pokedex_counter.ui.widgets.clickable_label import ClickableLabel
from pokedex_counter.ui.widgets.flow_layout import FlowLayout

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}

class SpriteStrip(QWidget):
    manual_caught = Signal(str)
    manual_uncaught = Signal(str)
    manual_ignored = Signal(str)
    manual_unignored = Signal(str)

    def __init__(self, folder: Path, sprite_size: int = 24, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._folder = folder
        self._sprite_width = sprite_size
        self._sprite_height = sprite_size
        self._sprite_padding = 0
        self._labels_by_name: dict[str, ClickableLabel] = {}
        self._pixmap_cache: dict[Path, QPixmap] = {}

        self._layout = FlowLayout(self)

        self.reload()

    def reload(self) -> None:
        previous_states = {
            name: (
                label._caught,
                label._evolved,
                label._ignored,
                label._bonus,
                label._comparison,
                label._section_required,
                label._section_bonus,
            )
            for name, label in self._labels_by_name.items()
        }
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._labels_by_name.clear()
        paths = self._discover_images()

        if not paths:
            placeholder = QLabel(f"No images found in {self._folder}")
            placeholder.setStyleSheet("color: gray; font-style: italic;")
            self._layout.addWidget(placeholder)
            return

        for path in paths:
            label = self._make_sprite_label(path)
            name = POKEMON_DEX_TO_NAME.get(int(path.stem), path.stem)
            self._labels_by_name[name] = label
            state = previous_states.get(name)
            if state is not None:
                caught, evolved, ignored, bonus, comparison, section_required, section_bonus = state
                label.set_caught(caught, evolved)
                label.set_ignored(ignored)
                label.set_bonus(bonus)
                label.set_comparison(comparison)
                label.set_section_state(section_required, section_bonus)
            self._layout.addWidget(label)

    def set_folder(self, folder: Path) -> None:
        if folder == self._folder:
            return
        self._folder = folder
        self.reload()

    @staticmethod
    def natural_key(path):
        s = path.name
        return [int(t) if t.isdigit() else t.lower()
                for t in re.split(r'(\d+)', s)]

    def _discover_images(self) -> list[Path]:
        if not self._folder.is_dir():
            return []

        return sorted(
            (p for p in self._folder.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS),
            key=lambda p: self.natural_key(p)
        )

    def _make_sprite_label(self, path: Path) -> QLabel:
        label = ClickableLabel(path)
        label.setToolTip(path.name)
        label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        label.set_padding(self._sprite_padding)

        self._draw_image_in_label(label)

        label.catch_clicked.connect(self._on_catch_clicked)
        label.ignore_clicked.connect(self._on_ignore_clicked)

        return label

    def _draw_image_in_label(self, label) -> None:
        pixmap = self._pixmap_cache.get(label._path)
        if pixmap is None:
            pixmap = QPixmap(str(label._path))
            self._pixmap_cache[label._path] = pixmap
        if pixmap.isNull():
            label.setText(f"⚠ {label._path.name}")
            return label

        # Resize down if needed
        width = self._sprite_width
        height = self._sprite_height
        if pixmap.width() > width or pixmap.height() > height:
            pixmap = pixmap.scaled(
            width,
            height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        # Create transparent image
        canvas = QPixmap(width, height)
        canvas.fill(Qt.GlobalColor.transparent)
        # Draw the centered pokémon inside
        x = (width - pixmap.width()) // 2
        y = (height - pixmap.height()) // 2
        painter = QPainter(canvas)
        painter.drawPixmap(x, y, pixmap)
        painter.end()

        label.setFixedSize(width + 2 * label._padding, height + 2 * label._padding)
        label.setPixmap(canvas)

    def set_sprite_size(self, size) -> None:
        self.set_sprite_dimensions(size, size)

    def set_sprite_dimensions(self, width: int, height: int) -> None:
        self._sprite_width = width
        self._sprite_height = height
        for label in self._labels_by_name.values():
            self._draw_image_in_label(label)

    def set_sprite_padding(self, padding) -> None:
        self._sprite_padding = padding
        for label in self._labels_by_name.values():
            label.set_padding(padding)
            self._draw_image_in_label(label)

    def set_current_section(self, required: set[str], bonuses: set[str]) -> None:
        for name, label in self._labels_by_name.items():
            label.set_section_state(name in required, name in bonuses)

    def on_pokemon_found(self, name: str, evolved: bool = False) -> bool:
        """Mark `name` as obtained. `evolved` says it was obtained by
        evolution rather than by catching it, which suppresses the bonus
        highlight. Defaults to False so a plain "it was caught" call - the
        manual click path, and every test that predates bonuses - keeps
        working unchanged."""
        label = self._labels_by_name.get(name)
        if label:
            label.set_caught(True, evolved)
            return True
        return False

    def set_comparison_names(self, names: set[str]) -> None:
        """Replace the comparison names known up to the active section."""
        for name, label in self._labels_by_name.items():
            label.set_comparison(name in names)

    def set_bonus_names(self, names: set[str]) -> None:
        """Turn bonus highlighting on for `names`; an empty set turns it off
        again. Recolors what's already caught so flipping the setting
        mid-run applies retroactively instead of only to future catches -
        anything obtained by evolving stays unhighlighted."""
        for name, label in self._labels_by_name.items():
            label.set_bonus(name in names)

    def reset(self) -> None:
        """Deselect every sprite, going through the same per-sprite deselect
        path a manual un-click takes so count/controller/detector state all
        stay consistent. Also drops any accumulated WR marks - since those
        now persist across sections, a fresh run
        needs to re-earn them section by section rather than starting with
        every section the previous run ever reached still lit up blue."""
        for label in self._labels_by_name.values():
            label.set_caught(False)
            label.set_ignored(False)
            label.set_comparison(False)

    def set_columns(self, columns: int) -> None:
        self._layout.set_columns(columns)

    def natural_width(self) -> int:
        return self._layout.natural_width()

    def sizeHint(self):
        return self._layout.sizeHint()

    def minimumSizeHint(self):
        return self._layout.minimumSize()

    # Handlers for ClickableLabel signals, which are emitted when the user clicks on a sprite.
    # The catches are bottom-up: the controller will call pokemon_found, so we only emit the signal here instead of painting the label twice.
    def _on_catch_clicked(self, path: Path, caught: bool) -> None:
        name = POKEMON_DEX_TO_NAME.get(int(path.stem), path.stem)
        label = self.sender()

        if isinstance(label, ClickableLabel):
            if caught:
                self.manual_caught.emit(name)
            else:
                label.set_caught(False)
                self.manual_uncaught.emit(name)

    def _on_ignore_clicked(self, path: Path, ignored: bool) -> None:
        name = POKEMON_DEX_TO_NAME.get(int(path.stem), path.stem)
        label = self.sender()

        if isinstance(label, ClickableLabel):
            if ignored:
                self.manual_ignored.emit(name)
            else:
                self.manual_unignored.emit(name)
            label.set_ignored(ignored)
