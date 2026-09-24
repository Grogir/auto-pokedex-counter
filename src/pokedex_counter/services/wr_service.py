import json

from pokedex_counter.config import WR_JSON_PATH
from pokedex_counter.controllers.game_controller import GameController


def load_wr_sections() -> dict[int, set[str]]:
    """Rebuild WR sections according to the currently configured route.

    The section keys in WR.json describe the route used to record the
    comparison and are deliberately ignored. Feeding the recorded Pokémon to
    a temporary controller lets the active route determine each Pokémon's
    actual section, including the dedicated evolution section.
    """
    if not WR_JSON_PATH.is_file():
        return {}

    try:
        with open(WR_JSON_PATH, encoding="utf-8") as f:
            raw: dict[str, list[str]] = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[wr_service] WARNING: failed to load '{WR_JSON_PATH}', compare-to-WR disabled: {e}")
        return {}

    controller = GameController()
    for names in raw.values():
        for name in names:
            controller.on_detection(name)

    return {
        section: set(names)
        for section, names in controller.section_catches.items()
    }
