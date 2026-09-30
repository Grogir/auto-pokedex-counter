"""Settings window shown alongside MainWindow - the counter window sits in
a stream layout, so no button/menu can live there without appearing on
stream; this window carries all the controls instead.

This is a dumb view: it holds no references to GameController/
DetectionService/CaptureService. All cross-object wiring happens in
app.py, matching the existing convention there.
"""
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pokedex_counter.config import APP_NAME, SPRITES_DIR, SPRITES_DIRS
from pokedex_counter.detection_config import DETECTION_TYPE

DEFAULT_SPRITES_PER_ROW = 10
DEFAULT_FONT_SIZE = 24
DEFAULT_SPRITE_SIZE = 24
DEFAULT_SPRITE_PADDING = 3
DEFAULT_BOTTOM_MARGIN = 0

class SettingsWindow(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} Settings")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.columns_spinbox = QSpinBox()
        self.columns_spinbox.setRange(1, 30)
        self.columns_spinbox.setValue(DEFAULT_SPRITES_PER_ROW)
        form.addRow("Sprites per row:", self.columns_spinbox)

        self.sprite_width_spinbox = QSpinBox()
        self.sprite_width_spinbox.setRange(20, 60)
        self.sprite_width_spinbox.setValue(DEFAULT_SPRITE_SIZE)
        form.addRow("Sprite width:", self.sprite_width_spinbox)

        self.sprite_height_spinbox = QSpinBox()
        self.sprite_height_spinbox.setRange(20, 60)
        self.sprite_height_spinbox.setValue(DEFAULT_SPRITE_SIZE)
        form.addRow("Sprite height:", self.sprite_height_spinbox)

        self.sprite_padding_spinbox = QSpinBox()
        self.sprite_padding_spinbox.setRange(0, 10)
        self.sprite_padding_spinbox.setValue(DEFAULT_SPRITE_PADDING)
        form.addRow("Sprite padding:", self.sprite_padding_spinbox)

        self.box_sprite_width_spinbox = QSpinBox()
        self.box_sprite_width_spinbox.setRange(20, 60)
        self.box_sprite_width_spinbox.setValue(DEFAULT_SPRITE_SIZE)
        form.addRow("Box sprite width:", self.box_sprite_width_spinbox)

        self.box_sprite_height_spinbox = QSpinBox()
        self.box_sprite_height_spinbox.setRange(20, 60)
        self.box_sprite_height_spinbox.setValue(DEFAULT_SPRITE_SIZE)
        form.addRow("Box sprite height:", self.box_sprite_height_spinbox)

        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(8, 96)
        self.font_size_spinbox.setValue(DEFAULT_FONT_SIZE)
        form.addRow("Counter font size:", self.font_size_spinbox)

        self.bottom_margin_spinbox = QSpinBox()
        self.bottom_margin_spinbox.setRange(0, 200)
        self.bottom_margin_spinbox.setValue(DEFAULT_BOTTOM_MARGIN)
        form.addRow("Bottom margin:", self.bottom_margin_spinbox)

        self.sprite_set_combo = QComboBox()
        for sprite_set, folder in enumerate(SPRITES_DIRS, start=1):
            self.sprite_set_combo.addItem(folder.name.replace("_", " ").title(), sprite_set)
        self.sprite_set_combo.setCurrentIndex(self.sprite_set_combo.findData(SPRITES_DIRS.index(SPRITES_DIR) + 1))
        form.addRow("Sprite set:", self.sprite_set_combo)

        self.detection_type_combo = QComboBox()
        self.detection_type_combo.addItem("No detection", DETECTION_TYPE["NONE"])
        self.detection_type_combo.addItem("Text detection", DETECTION_TYPE["TEXT"])
        self.detection_type_combo.addItem("Sprite detection", DETECTION_TYPE["SPRITE"])
        self.detection_type_combo.setCurrentIndex(1)
        form.addRow("Detection type:", self.detection_type_combo)

        self.comparison_combo = QComboBox()
        self.comparison_combo.addItem("None", None)
        form.addRow("Compare to:", self.comparison_combo)

        self.highlight_bonuses_checkbox = QCheckBox()
        form.addRow("Highlight bonuses", self.highlight_bonuses_checkbox)

        self.frameless_checkbox = QCheckBox()
        form.addRow("Remove title bar", self.frameless_checkbox)

        layout.addLayout(form)

        self.reset_button = QPushButton("Reset counter")
        layout.addWidget(self.reset_button)

        self.calibrate_button = QPushButton("Calibrate")
        layout.addWidget(self.calibrate_button)
