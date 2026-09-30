import json
from dataclasses import dataclass

from pokedex_counter.config import COMPARISON_DIRS
from pokedex_counter.controllers.game_controller import GameController
from pokedex_counter.game_config import BONUSES, ROUTE_SECTIONS


@dataclass(frozen=True)
class Comparison:
    key: str
    name: str
    cumulative_bonuses: dict[int, set[str]]


def load_comparisons() -> list[Comparison]:
    """Load structurally valid comparison JSON files from all configured folders."""
    files = []
    source_names = ("bundled", "external") if len(COMPARISON_DIRS) > 1 else ("comparison",)
    for source_index, directory in enumerate(COMPARISON_DIRS):
        if not directory.is_dir():
            continue
        paths = (path for path in directory.iterdir() if path.is_file() and path.suffix.casefold() == ".json")
        for path in sorted(paths, key=lambda item: item.name.casefold()):
            try:
                with path.open(encoding="utf-8") as comparison_file:
                    raw = json.load(comparison_file)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                print(f"[comparison_service] WARNING: failed to load '{path}': {error}")
                continue
            if not isinstance(raw, dict) or any(
                not isinstance(section, str)
                or not isinstance(names, list)
                or any(not isinstance(name, str) for name in names)
                for section, names in raw.items()
            ):
                print(f"[comparison_service] WARNING: invalid comparison format in '{path}'")
                continue
            files.append((source_index, path, raw))

    name_counts: dict[str, int] = {}
    for _, path, _ in files:
        name_counts[path.stem] = name_counts.get(path.stem, 0) + 1

    comparisons = []
    for source_index, path, raw in files:
        name = path.stem
        if name_counts[name] > 1:
            name = f"{name} ({source_names[source_index]})"
        key = f"{source_index}:{path.name}"
        comparisons.append(Comparison(key, name, _cumulated_bonuses(raw)))
    return comparisons


def _cumulated_bonuses(raw: dict[str, list[str]]) -> dict[int, set[str]]:
    controller = GameController()
    for names in raw.values():
        for name in names:
            controller.on_detection(name)

    sections = {}
    for section in range(len(ROUTE_SECTIONS)):
        names = set(controller.section_catches.get(section, [])) & BONUSES
        if section == 0:
            sections[section] = names
        else:
            sections[section] = sections[section - 1] | names
    return sections
