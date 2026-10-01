
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pokedex_counter.game_config import ROUTE_SECTIONS, previous_form_of

AVERAGE_EVO_TIME = {
    "PARAS": 18.75,
    "SEEL": 22.03,
    "PSYDUCK": 20.49,
    "KRABBY": 18.95,
    "MACHOP": 29.25,
    "GEODUDE": 21.05,
    "ZUBAT": 21.05,
    "VENONAT": 18.95,
    "SANDSHREW": 34.28,
    "DROWZEE": 49,
    "RHYHORN": 22.05,
    "RATTATA": 20.88,
    "DODUO": 37.5,
    "CUBONE": 20.45,
    "JIGGLYPUFF": 19.75,
    "VOLTORB": 19.25,
    "PIKACHU": 18.55,
    "ABRA": 36.67,
    "BELLSPROUT": 19.98,
    "GRIMER": 34.35,
    "PONYTA": 36.4,
}

SPECIFIC_EVO_TIME = {
    "SEEL": {30: 25.1, 31: 23.05, 32: 21, 33: 18.95},
    "PSYDUCK": {30: 23.05, 31: 21, 32: 18.95, 33: 18.95},
    "MACHOP": {22: 31.3, 24: 27.2},
    "SANDSHREW": {12: 37.7, 14: 33.6, 15: 31.55},
    "DROWZEE": {9: 55.15, 11: 51.05, 13: 46.95, 15: 42.85},
    "RATTATA": {18: 21.9, 20: 19.85, 21: 19.85, 22: 22.95, 23: 19.85},
    "DODUO": {18: 43.85, 20: 39.75, 22: 35.35},
    "BELLSPROUT": {19: 24.1, 22: 18.95},
    "GRIMER": {30: 36.4, 32: 32.3},
    "PONYTA": {28: 44.6, 30: 40.5, 32: 36.4, 34: 32.3},
}

CONSTANT_AFO_TIME = 799.8


class AfoWindow(QWidget):
    def __init__(self, section_provider: Callable[[], int] | None = None) -> None:
        super().__init__()
        self.setWindowTitle("AFO Prediction")
        self.setMinimumWidth(300)
        self._section_provider = section_provider or (lambda: 0)
        self.evo_time = AVERAGE_EVO_TIME.copy()
        self._selected_levels: dict[str, int] = {}
        self._awaiting_level: set[str] = set()
        self._comparison_seconds: int | None = None
        self._multiplier_percent = 0.0
        self._labels: dict[str, QLabel] = {}
        self._level_buttons: dict[str, dict[int, QPushButton]] = {}

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(0)

        self.total_time_label = QLabel()
        layout.addWidget(self.total_time_label)
        self.total_time_label.setStyleSheet("color: white; background-color: black;")
        font = QFont("Segoe UI")
        font.setPointSize(14)
        font.setBold(True)
        self.total_time_label.setFont(font)
        self.total_time_label.setFixedHeight(50)

        self.captured_evolutions_label = QLabel()
        self.captured_evolutions_label.setFixedHeight(20)
        layout.addWidget(self.captured_evolutions_label)

        for name in AVERAGE_EVO_TIME:
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(2)
            row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            pokemon_label = QLabel(name.title())
            pokemon_label.setFixedHeight(20)
            self._labels[name] = pokemon_label
            row_layout.addWidget(pokemon_label)
            buttons = {}
            for level in SPECIFIC_EVO_TIME.get(name, {}):
                button = QPushButton(f"L{level}")
                button.setFixedWidth(44)
                button.setFixedHeight(20)
                button.clicked.connect(
                    lambda checked=False, pokemon=name, selected_level=level:
                    self._select_level(pokemon, selected_level)
                )
                row_layout.addWidget(button)
                buttons[level] = button
            self._level_buttons[name] = buttons
            row_layout.addStretch()
            layout.addLayout(row_layout)
        self._update_display()

    @property
    def total_time(self) -> float:
        base_time = sum(self.evo_time.values()) + CONSTANT_AFO_TIME
        return base_time * (1 + self._multiplier_percent / 100)

    def set_afo_comparison(self, seconds: int) -> None:
        self._comparison_seconds = seconds if seconds > 0 else None
        self._update_display()

    def set_afo_multiplier(self, percent: float) -> None:
        self._multiplier_percent = percent
        self._update_display()

    @staticmethod
    def format_time(seconds: float) -> str:
        total_seconds = round(seconds)
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02}:{seconds:02}"

    @staticmethod
    def format_delta(seconds: float) -> str:
        if abs(seconds) >= 60:
            sign = "+" if seconds >= 0 else "-"
            return f"{sign}{AfoWindow.format_time(abs(seconds))}"
        else:
            return f"{seconds:+d}"

    def pokemon_found(self, name: str, evolved: bool = False) -> None:
        section = self._section_provider()
        if evolved and section >= len(ROUTE_SECTIONS) - 1:
            return

        prev = previous_form_of(name)
        if prev in self.evo_time:
            self.evo_time[prev] = 0
            self._update_display()

        elif name in SPECIFIC_EVO_TIME:
            self._selected_levels.pop(name, None)
            self._awaiting_level.add(name)
            self._update_display()

    def sprite_uncaught(self, name: str) -> None:
        prev = previous_form_of(name)
        if prev in self.evo_time:
            if prev in SPECIFIC_EVO_TIME:
                if prev in self._selected_levels:
                    self.evo_time[prev] = SPECIFIC_EVO_TIME[prev][self._selected_levels[prev]]
                else:
                    self.evo_time[prev] = AVERAGE_EVO_TIME[prev]
            else:
                self.evo_time[prev] = AVERAGE_EVO_TIME[prev]
            self._update_display()

        elif name in self.evo_time:
            self._selected_levels.pop(name, None)
            self._awaiting_level.discard(name)
            if self.evo_time[name] != 0:
                self.evo_time[name] = AVERAGE_EVO_TIME[name]
            self._update_display()

    def reset(self) -> None:
        self.evo_time = AVERAGE_EVO_TIME.copy()
        self._selected_levels.clear()
        self._awaiting_level.clear()
        self._update_display()

    def _select_level(self, pokemon: str, level: int) -> None:
        if self.evo_time[pokemon] != 0:
            self.evo_time[pokemon] = SPECIFIC_EVO_TIME[pokemon][level]
        self._selected_levels[pokemon] = level
        self._awaiting_level.discard(pokemon)
        self._update_display()

    def _update_display(self) -> None:
        total_text = f" Estimated AFO: {self.format_time(self.total_time)}"
        if self._comparison_seconds is not None:
            total_text += f" ({self.format_delta(round(self.total_time) - self._comparison_seconds)})"
        self.total_time_label.setText(total_text)
        captured_evolutions = sum(value == 0 for value in self.evo_time.values())
        self.captured_evolutions_label.setText(
            f"Bonuses caught: {captured_evolutions}"
        )
        for pokemon, label in self._labels.items():
            if (pokemon in self._awaiting_level or pokemon in self._selected_levels) and self.evo_time[pokemon] != 0:
                label.show()
                if pokemon in self._selected_levels:
                    label.setText(f"{pokemon.title()}: L{self._selected_levels[pokemon]}")
                elif pokemon in self._awaiting_level:
                    label.setText(f"{pokemon.title()}: ")
                for button in self._level_buttons[pokemon].values():
                    button.setVisible(pokemon in self._awaiting_level)
            else:
                label.hide()
                for button in self._level_buttons[pokemon].values():
                    button.hide()

        self.layout().activate()
        self.adjustSize()

