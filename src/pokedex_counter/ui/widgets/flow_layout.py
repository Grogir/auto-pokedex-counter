from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QSizePolicy, QWidget


class FlowLayout(QLayout):
    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = 0) -> None:
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)

        self.setSpacing(spacing)
        self._item_list = []
        self._columns: int | None = None

    # -------------------------
    # Core Qt contract
    # -------------------------
    def addItem(self, item) -> None:
        self._item_list.append(item)

    def count(self) -> int:
        return len(self._item_list)

    def itemAt(self, index: int):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:
        return True

    def set_columns(self, columns: int | None) -> None:
        """Set a fixed number of items per row, overriding the default
        pixel-width-based wrapping. Pass None to go back to width-based
        wrapping."""
        if columns == self._columns:
            return
        self._columns = columns
        self.invalidate()

    def natural_width(self) -> int:
        """Width needed to fit `self._columns` items in a row without
        wrapping early, based on each item's own size hint. 0 if there's no
        fixed column count or no items yet."""
        if self._columns is None or self.count() == 0:
            return 0

        spacing = self._smart_spacing()
        n = min(self._columns, self.count())
        total = sum(self.itemAt(i).sizeHint().width() for i in range(n))
        total += spacing * (n - 1)

        margins = self.contentsMargins()
        return total + margins.left() + margins.right()

    # -------------------------
    # Geometry logic
    # -------------------------
    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()

        for i in range(self.count()):
            item = self.itemAt(i)
            if item:
                size = size.expandedTo(item.minimumSize())

        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(),
                      margins.top() + margins.bottom())

        return size

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    # -------------------------
    # Layout engine
    # -------------------------
    def _smart_spacing(self) -> int:
        return self.spacing() if self.spacing() >= 0 else 8

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        x, y = rect.x(), rect.y()
        line_height = 0
        col = 0
        spacing = self._smart_spacing()

        for i in range(self.count()):
            item = self.itemAt(i)
            if not item:
                continue

            widget = item.widget()
            hint = item.sizeHint()

            space_x = spacing
            space_y = spacing

            if widget:
                space_x = widget.style().layoutSpacing(
                    QSizePolicy.ControlType.PushButton,
                    QSizePolicy.ControlType.PushButton,
                    Qt.Orientation.Horizontal,
                ) if self.spacing() < 0 else spacing

                space_y = widget.style().layoutSpacing(
                    QSizePolicy.ControlType.PushButton,
                    QSizePolicy.ControlType.PushButton,
                    Qt.Orientation.Vertical,
                ) if self.spacing() < 0 else spacing

            next_x = x + hint.width() + space_x

            if self._columns is not None:
                should_wrap = col >= self._columns
            else:
                should_wrap = next_x > rect.right() + 1 and line_height > 0

            if should_wrap:
                x = rect.x()
                y += line_height + space_y
                next_x = x + hint.width() + space_x
                line_height = 0
                col = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))

            x = next_x
            col += 1
            line_height = max(line_height, hint.height())

        return (y + line_height - rect.y())
