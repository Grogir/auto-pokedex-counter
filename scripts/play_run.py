import json

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from pokedex_counter.boxes_window import BoxesWindow
from pokedex_counter.config import COMPARISON_DIR
from pokedex_counter.controllers.game_controller import GameController
from pokedex_counter.game_config import BONUSES
from pokedex_counter.main_window import MainWindow

RUN_PATH = COMPARISON_DIR / "WR_noafo.json"
WAIT_MS = 50
# boxes_window.DISPLAY_ALL = True

def load_file(path) -> dict[str, list[str]] | None:
    if not path.is_file():
        print(f"PB file not found: {path}")
        return None

    try:
        with open(path, encoding="utf-8") as f:
            loaded = json.load(f)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Failed to load '{path}': {error}")
        return None

    if not isinstance(loaded, dict) or not all(
        isinstance(section, str) and isinstance(names, list)
        and all(isinstance(name, str) for name in names)
        for section, names in loaded.items()
    ):
        print(f"Invalid PB format in '{path}'")
        return None

    return loaded

def playback(loaded, controller: GameController) -> None:
    playback = [name for names in loaded.values() for name in names]
    index = 0

    def play_next() -> None:
        nonlocal index
        if index >= len(playback):
            return

        name = playback[index]
        index += 1
        controller.on_detection(name)
        QTimer.singleShot(WAIT_MS, play_next)

    QTimer.singleShot(0, play_next)

def main() -> int:
    loaded = load_file(RUN_PATH)
    if loaded is None:
        return 1

    app = QApplication([])
    controller = GameController()
    window = MainWindow()
    boxes_window = BoxesWindow()
    controller.count_changed.connect(window._update_counter)
    window.sprite_strip.set_bonus_names(BONUSES)
    from pokedex_counter.app import wire_found_pokemon
    wire_found_pokemon(controller, window.sprite_strip, boxes_window)
    window.show()
    boxes_window.move(window.x() + window.frameGeometry().width() + 10, window.y())
    boxes_window.show()

    playback(loaded, controller)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
