"""Main application window."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QFont, QFontDatabase, QResizeEvent
from PySide6.QtWidgets import QGridLayout, QLabel, QMainWindow, QWidget

from pokedex_counter.config import APP_NAME, FONTS_DIR, SPRITES_DIR
from pokedex_counter.ui.widgets.sprite_strip import SpriteStrip

DEFAULT_COUNTER_FONT_SIZE = 24
CALIBRATION_MESSAGE_FONT_SIZE = 12
CALIBRATION_NEEDED_MESSAGE = (
    "Please calibrate your layout by showing the title screen "
    "with Squirtle as the visible Pokémon"
)


class MainWindow(QMainWindow):
    close_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(300, 600)
        self._calibrated = True
        self._counter_font_size = DEFAULT_COUNTER_FONT_SIZE
        self._count_provider = None

        self._build_ui()

        QTimer.singleShot(0, self._sync_height_to_width)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.close_requested.emit()
        event.accept()

    def _build_ui(self) -> None:
        self._central_widget = QWidget()
        self.setStyleSheet("QMainWindow { background-color: #FFFFFF; }")
        layout = QGridLayout(self._central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sprite_strip = SpriteStrip(SPRITES_DIR)

        layout.addWidget(self.sprite_strip)

        self.counter_label = QLabel("0")
        self.counter_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.counter_label.setContentsMargins(1, 1, 1, 1)
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font_id = QFontDatabase.addApplicationFont(str(FONTS_DIR / "Pokemon Solid.ttf"))
        families = QFontDatabase.applicationFontFamilies(font_id)
        self._counter_font_family = families[0] if families else self.counter_label.font().family()
        self._apply_counter_font(self._counter_font_size)

        layout.addWidget(self.counter_label, 0, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        self.setCentralWidget(self._central_widget)

    def set_count_provider(self, count_provider):
        self._count_provider = count_provider
        self._update_counter(count_provider())

    def _apply_counter_font(self, points: int) -> None:
        font = QFont(self._counter_font_family)
        font.setPointSize(points)
        self.counter_label.setFont(font)
        if self._calibrated:
            self.counter_label.setFixedHeight(self.counter_label.fontMetrics().ascent() + 3)
        else:
            self.counter_label.setMinimumHeight(0)
            self.counter_label.setMaximumHeight(16777215)

    def _update_counter(self, value: int):
        if not self._calibrated:
            return
        self.counter_label.setText(f" {value}")

    def set_calibrated(self, calibrated: bool) -> None:
        """Toggle between the normal "N caught" counter and a prompt to
        calibrate - detection can't run without calibration, so showing "0
        caught" in that state would misleadingly suggest it's working."""
        self._calibrated = calibrated
        self.counter_label.setWordWrap(not calibrated)
        if calibrated:
            self._apply_counter_font(self._counter_font_size)
            self._update_counter(self._count_provider() if self._count_provider is not None else 0)
        else:
            self._apply_counter_font(CALIBRATION_MESSAGE_FONT_SIZE)
            self.counter_label.setText(CALIBRATION_NEEDED_MESSAGE)
        QTimer.singleShot(0, self._sync_height_to_width)

    def set_sprites_per_row(self, columns: int) -> None:
        self.sprite_strip.set_columns(columns)
        self.refresh_size()

    def refresh_size(self) -> None:
        width = self.sprite_strip.natural_width()
        if width > 0:
            margins = self._central_widget.layout().contentsMargins()
            self.setFixedWidth(width + margins.left() + margins.right())
        QTimer.singleShot(0, self._sync_height_to_width)

    def set_sprite_size(self, size: int) -> None:
        self.set_sprite_dimensions(size, size)

    def set_sprite_dimensions(self, width: int, height: int) -> None:
        self.sprite_strip.set_sprite_dimensions(width, height)
        self.refresh_size()

    def set_sprite_padding(self, size: int) -> None:
        self.sprite_strip.set_sprite_padding(size)
        self.refresh_size()

    def set_counter_font_size(self, points: int) -> None:
        self._counter_font_size = points
        if self._calibrated:
            self._apply_counter_font(points)
        QTimer.singleShot(0, self._sync_height_to_width)

    def resizeEvent(self, event: QResizeEvent) -> None:
        QTimer.singleShot(0, self._sync_height_to_width)

    def _sync_height_to_width(self) -> None:
        layout = self._central_widget.layout()
        content_width = self._central_widget.width()
        needed_content_height = layout.totalHeightForWidth(content_width)

        # chrome_height = self.frameGeometry().height() - self.geometry().height()
        target_height = needed_content_height

        if target_height != self.height():
            self.resize(self.width(), target_height)

    def set_frameless_flag(self, checked: bool) -> None:
        if checked:
            self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        else:
            self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.MSWindowsFixedSizeDialogHint)

    def on_frameless_toggled(self, checked: bool) -> None:
        self.set_frameless_flag(checked)
        self.show()
        self.resize(300, 600)

    def mousePressEvent(self, event):
        """Intercepte le clic de souris initial."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Calcule la distance entre le clic global et le coin supérieur gauche de la fenêtre
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Déplace la fenêtre lorsque la souris glisse."""
        if event.buttons() == Qt.MouseButtons.LeftButton:
            # Déplace la fenêtre en soustrayant le décalage initial
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
