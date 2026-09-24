from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QWidget,
)

class ClickableLabel(QLabel):
    clicked = Signal(Path)
    ignore_toggled = Signal(Path, bool)

    def __init__(self, path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = path
        self._padding = 0
        self._selected = False
        self._wr_marked = False
        self._section_color = None
        self._ignored = False
        self._just_unignored = False
        self._catch_color = "black"
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_selected()
        elif event.button() == Qt.MouseButton.RightButton:
            self.set_ignored(not self._ignored)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        event.accept()

    def toggle_selected(self) -> None:
        was_ignored = self._ignored
        if was_ignored:
            self._ignored = False
        self._selected = not self._selected
        if self._selected:
            self._catch_color = "black"
            self._just_unignored = was_ignored
        self._apply_style()
        self.clicked.emit(self._path)

    def select(self, color: str = "black") -> None:
        """Programmatically select (idempotent - no-op if already selected)."""
        if self._selected:
            return
        self._selected = True
        self._ignored = False
        self._catch_color = color
        self._apply_style()

    def set_ignored(self, ignored: bool) -> None:
        if self._ignored == ignored:
            return
        self._ignored = ignored
        if ignored:
            self._selected = False
        self._apply_style()
        self.ignore_toggled.emit(self._path, ignored)

    def clear_ignored(self) -> None:
        self.set_ignored(False)

    def deselect(self) -> None:
        """Programmatically deselect (idempotent - no-op if not selected)."""
        if not self._selected:
            return
        self._selected = False
        self._catch_color = "black"
        self._apply_style()

    def set_wr_marked(self, marked: bool) -> None:
        """Toggle the pre-catch "on WR route" highlight. Purely visual -
        _apply_style favors the catch color over this once selected, so
        catching a marked sprite doesn't need a separate unmark step."""
        if self._wr_marked == marked:
            return
        self._wr_marked = marked
        self._apply_style()

    def set_section_color(self, color: str | None) -> None:
        self._section_color = color
        self._apply_style()

    def set_catch_color(self, color: str) -> None:
        """Retroactively correct an already-caught sprite's color - e.g. it
        was caught out of order (before its WR section started, so it was
        colored green as off-route), and a later section reveals it was
        actually on-route all along. No-op while unselected; doesn't emit
        `clicked` since this isn't a new catch event."""
        if self._catch_color == color:
            return
        self._catch_color = color
        if self._selected:
            self._apply_style()

    def set_padding(self, padding):
        self._padding = padding
        self._apply_style()

    def _apply_style(self) -> None:
        base_style = f"padding: {self._padding}px;"
        if self._ignored:
            self.setStyleSheet(base_style + "background-color: gray;")
        elif self._selected:
            self.setStyleSheet(base_style + f"background-color: {self._catch_color};")
        elif self._wr_marked:
            self.setStyleSheet(base_style + "background-color: blue;")
        elif self._section_color:
            self.setStyleSheet(base_style + f"background-color: {self._section_color};")
        else:
            self.setStyleSheet(base_style)
