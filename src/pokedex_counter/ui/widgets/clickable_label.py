from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QLabel,
    QWidget,
)

from pokedex_counter.config import (
    LABEL_COLOR_BONUS,
    LABEL_COLOR_CATCH,
    LABEL_COLOR_IGNORED,
    LABEL_COLOR_SECTION_BONUS,
    LABEL_COLOR_SECTION_REQUIRED,
    LABEL_COLOR_WR_AND_PLAYER,
    LABEL_COLOR_WR_ONLY,
)


class ClickableLabel(QLabel):
    catch_clicked = Signal(Path, bool)
    ignore_clicked = Signal(Path, bool)

    def __init__(self, path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = path
        self._padding = 0
        self._caught = False
        self._ignored = False
        self._bonus = False
        self._evolved = False
        self._wr = False
        self._section_required = False
        self._section_bonus = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.catch_clicked.emit(self._path, not self._caught)
        elif event.button() == Qt.MouseButton.RightButton:
            self.ignore_clicked.emit(self._path, not self._ignored)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        event.accept()

    def set_caught(self, caught: bool, evolved: bool = False) -> None:
        if self._caught == caught:
            return
        self._caught = caught
        self._evolved = evolved
        self._ignored = False
        self._apply_style()

    def set_ignored(self, ignored: bool) -> None:
        if self._ignored == ignored:
            return
        self._ignored = ignored
        if ignored:
            self._caught = False
        self._apply_style()

    def set_bonus(self, marked: bool) -> None:
        if self._bonus == marked:
            return
        self._bonus = marked
        self._apply_style()

    def set_wr(self, marked: bool) -> None:
        if self._wr == marked:
            return
        self._wr = marked
        self._apply_style()

    def set_section_state(self, required: bool, bonus: bool) -> None:
        if self._section_required == required and self._section_bonus == bonus:
            return
        self._section_required = required
        self._section_bonus = bonus
        self._apply_style()

    def set_padding(self, padding):
        self._padding = padding
        self._apply_style()

    def _apply_style(self) -> None:
        color = "transparent"

        if self._caught:
            if self._bonus and not self._evolved:
                if self._wr:
                    color = LABEL_COLOR_WR_AND_PLAYER
                else:
                    color = LABEL_COLOR_BONUS
            else:
                color = LABEL_COLOR_CATCH
        elif self._ignored:
            color = LABEL_COLOR_IGNORED
        elif self._section_required:
            color = LABEL_COLOR_SECTION_REQUIRED
        elif self._wr:
            color = LABEL_COLOR_WR_ONLY
        elif self._section_bonus:
            color = LABEL_COLOR_SECTION_BONUS

        self.setStyleSheet(f"padding: {self._padding}px; background-color: {color};")
