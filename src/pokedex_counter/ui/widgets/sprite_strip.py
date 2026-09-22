"""Widget that displays every image in a folder, wrapping onto new rows as the
window is resized."""

from pathlib import Path
import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QSizePolicy,
    QWidget,
)

from pokedex_counter.ui.widgets.clickable_label import ClickableLabel
from pokedex_counter.ui.widgets.flow_layout import FlowLayout

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}

class SpriteStrip(QWidget):
    sprite_selected = Signal(Path)
    sprite_deselected = Signal(str)

    def __init__(self, folder: Path, sprite_size: int = 24, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._folder = Path(folder)
        self._sprite_size = sprite_size
        self._sprite_width = sprite_size
        self._sprite_height = sprite_size
        self._labels_by_name: dict[str, ClickableLabel] = {}
        self._pixmap_cache: dict[Path, QPixmap] = {}
        self._wr_enabled = False
        self._wr_names: set[str] = set()
        self._bonus_names: set[str] = set()
        # Caught sprites that got here by evolving rather than by being
        # caught. Remembered per sprite (not just consulted once at catch
        # time) so the retroactive recolor in set_bonus_names can tell the
        # two apart long after the fact.
        self._evolved_names: set[str] = set()

        self._layout = FlowLayout(self)

        self.reload()

    def reload(self) -> None:
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
            self._labels_by_name[path.stem] = label
            self._layout.addWidget(label)

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

        self.draw_image_in_label(label)

        label.clicked.connect(self._on_manual_click)

        return label

    def draw_image_in_label(self, label) -> None:
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
            self.draw_image_in_label(label)

    def set_sprite_padding(self, padding) -> None:
        for label in self._labels_by_name.values():
            label.set_padding(padding)
            self.draw_image_in_label(label)

    def _catch_color_for(self, name: str) -> str:
        """The background a catch of `name` should get. Bonus highlighting
        outranks the WR colors - a bonus is worth seeing whether or not it
        happens to also sit on the WR route - but only for a real catch:
        evolving into a bonus pokemon is the ordinary way to get it, so it
        gets the normal colors."""
        if name in self._bonus_names and name not in self._evolved_names:
            return "red"
        if self._wr_enabled and name not in self._wr_names:
            return "green"
        return "black"

    def select_sprite(self, name: str, evolved: bool = False) -> bool:
        """Mark `name` as obtained. `evolved` says it was obtained by
        evolution rather than by catching it, which suppresses the bonus
        highlight. Defaults to False so a plain "it was caught" call - the
        manual click path, and every test that predates bonuses - keeps
        working unchanged."""
        label = self._labels_by_name.get(name)
        if label is None:
            return False

        # Before select(), which round-trips through _on_sprite_clicked and
        # recomputes the color from _catch_color_for.
        if evolved:
            self._evolved_names.add(name)
        else:
            self._evolved_names.discard(name)

        label.select(self._catch_color_for(name))
        label.set_catch_color(self._catch_color_for(name))
        return True

    def deselect_sprite(self, name: str) -> bool:
        label = self._labels_by_name.get(name)
        if label is None:
            return False

        label.deselect()
        return True

    def mark_wr_section(self, names: set[str]) -> None:
        """Highlight `names` blue, on top of whatever's already marked from
        earlier sections - a WR pokemon missed in its own section stays
        flagged instead of silently losing its highlight once the run moves
        past it. Also remembers them so future catches are colored black
        (on-route, whenever caught) or green (never on-route).

        If one of `names` was already caught before its section came up
        (so it was colored green as apparently off-route at the time),
        correct it to black now that this section confirms it's on-route
        after all."""
        self._wr_enabled = True
        self._wr_names |= set(names)
        for name in names:
            label = self._labels_by_name.get(name)
            if label is None:
                continue
            label.set_wr_marked(True)
            if label._selected:
                label.set_catch_color(self._catch_color_for(name))

    def clear_wr_marks(self) -> None:
        """Turn off WR comparison: no more blue highlighting, and catches go
        back to the default black."""
        self._wr_enabled = False
        self._wr_names = set()
        for label in self._labels_by_name.values():
            label.set_wr_marked(False)

    def set_bonus_names(self, names: set[str]) -> None:
        """Turn bonus highlighting on for `names`; an empty set turns it off
        again. Recolors what's already caught so flipping the setting
        mid-run applies retroactively instead of only to future catches -
        anything obtained by evolving stays unhighlighted."""
        self._bonus_names = set(names)
        for name, label in self._labels_by_name.items():
            label.set_catch_color(self._catch_color_for(name))

    def reset(self) -> None:
        """Deselect every sprite, going through the same per-sprite deselect
        path a manual un-click takes so count/controller/detector state all
        stay consistent. Also drops any accumulated WR marks - since those
        now persist across sections (see mark_wr_section), a fresh run
        needs to re-earn them section by section rather than starting with
        every section the previous run ever reached still lit up blue."""
        for name in self._labels_by_name:
            self.deselect_sprite(name)
        if self._wr_enabled:
            self.clear_wr_marks()

    def set_columns(self, columns: int) -> None:
        self._layout.set_columns(columns)

    def natural_width(self) -> int:
        return self._layout.natural_width()

    def sizeHint(self):
        return self._layout.sizeHint()

    def minimumSizeHint(self):
        return self._layout.minimumSize()

    def _on_manual_click(self, path: Path) -> None:
        label = self.sender()

        if isinstance(label, ClickableLabel):
            if label._selected:
                label.set_catch_color(self._catch_color_for(path.stem))
                self.sprite_selected.emit(path.stem)
            else:
                self._evolved_names.discard(path.stem)
                self.sprite_deselected.emit(path.stem)
