# core/controller.py
from PySide6.QtCore import QObject, Signal

from pokedex_counter.game_config import ROUTE_SECTIONS, is_evolution


class GameController(QObject):
    # (dex number, section it was found in). The section rides along because
    # the same dex number can be routed differently per section - notably as
    # a catch in one and an evolution in another - and the UI needs to know
    # which happened to color it (see is_evolution below).
    pokemon_found = Signal(str, bool)
    count_changed = Signal(int)
    section_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self.found = set()
        self.ignored = set()
        self.count = 0
        # Current run's catches grouped by section, in catch order - same
        # {section_index: [dex, ...]} shape PB.json is saved in (see
        # services/pb_service.py). Kept in sync with `_current_section` via
        # Section attribution is computed from this run's found triggers at
        # catch time, not from whatever section the run reaches later.
        self.section_catches: dict[int, list[str]] = {}

    def current_section(self) -> int:
        """Return the first incomplete section, or the section count when done."""
        obtained = self.found | self.ignored
        sections = ROUTE_SECTIONS
        section = 0
        while section < len(sections) - 1:
            route_section = sections[section]
            if len(set(route_section.required) & obtained) < route_section.minimum:
                break
            section += 1
        if len(set(sections[section].required) & obtained) >= sections[section].minimum:
            return len(sections)
        return section

    def current_count(self) -> int:
        """Return the number of unique Pokemon found in this run."""
        return self.count

    def on_section_changed(self, section: int) -> None:
        """Compatibility helper for callers that prime a run in tests.

        Production section changes are derived from ``found`` by this
        controller; this method does not represent a second section state.
        """
        self.found.update(
            name
            for route_section in ROUTE_SECTIONS[:section]
            for name in route_section.required
        )

    def on_detection(self, name: str) -> None:
        section = self.current_section()
        self._record_detection(name, section)

    def _record_detection(self, name: str, section: int) -> None:
        self.ignored.discard(name)
        is_new = name not in self.found
        self.found.add(name)
        if is_new:
            self.count += 1
            self.count_changed.emit(self.count)

        # We track repeated catches even though the Pokédex count is unique.
        is_evo = is_evolution(section, name)
        if is_evo and not is_new:
            return
        self.section_catches.setdefault(section, []).append(name)
        self.pokemon_found.emit(name, is_evo)
        new_section = self.current_section()
        if new_section != section:
            self.section_changed.emit(new_section)

    def forget(self, name: str) -> None:
        for section in list(self.section_catches):
            names = self.section_catches[section]
            names[:] = [caught_name for caught_name in names if caught_name != name]
            if not names:
                del self.section_catches[section]

        self.found.discard(name)
        self.count = len(self.found)
        self.count_changed.emit(self.count)
        self.section_changed.emit(self.current_section())

    def ignore(self, name: str) -> None:
        """Exclude a Pokémon from the global run while satisfying sections."""
        self.forget(name)
        self.ignored.add(name)
        self.section_changed.emit(self.current_section())

    def unignore(self, name: str) -> None:
        if name in self.ignored:
            self.ignored.remove(name)
            self.section_changed.emit(self.current_section())

    def force_detect_current_section(self) -> None:
        """Detect only missing required Pokémon from the current section."""
        section = self.current_section()
        sections = ROUTE_SECTIONS
        if section >= len(sections):
            return
        missing = [name for name in sections[section].required if name not in self.found and name not in self.ignored]
        done = len(sections[section].required) - len(missing)
        for name in missing[:sections[section].minimum - done]:
            self._record_detection(name, section)

    def reset(self) -> None:
        self.found.clear()
        self.ignored.clear()
        self.count = 0
        self.section_catches.clear()
        self.count_changed.emit(self.count)
        self.section_changed.emit(0)
