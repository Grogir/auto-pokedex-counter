# core/controller.py
from PySide6.QtCore import QObject, Signal

from pokedex_counter.roi_config import SECTION_TRIGGERS, is_evolution

class GameController(QObject):
    # (dex number, section it was found in). The section rides along because
    # the same dex number can be routed differently per section - notably as
    # a catch in one and an evolution in another - and the UI needs to know
    # which happened to color it (see roi_config.is_evolution).
    pokemon_found = Signal(str, int, bool)
    count_changed = Signal(int)
    section_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self.found = set()
        self.count = 0
        # Current run's catches grouped by section, in catch order - same
        # {section_index: [dex, ...]} shape PB.json is saved in (see
        # services/pb_service.py). Kept in sync with `_current_section` via
        # Section attribution is computed from this run's found triggers at
        # catch time, not from whatever section the run reaches later.
        self.section_catches: dict[int, list[str]] = {}

    def current_section(self) -> int:
        """Return the active route section from this run's found Pokemon."""
        last = len(SECTION_TRIGGERS) - 1
        section = 0
        while section < last and SECTION_TRIGGERS[section] in self.found:
            section += 1
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
            trigger
            for trigger in SECTION_TRIGGERS[:section]
            if trigger is not None
        )

    def on_detection(self, name: str) -> None:
        section = self.current_section()
        is_new = name not in self.found
        self.found.add(name)
        if is_new:
            self.count += 1
            self.count_changed.emit(self.count)

        # This is an event log, so repeated catches must remain visible to the
        # boxes even though the Pokédex count is unique.
        self.section_catches.setdefault(section, []).append(name)
        self.pokemon_found.emit(name, section, is_evolution(section, name))
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

    def reset(self) -> None:
        self.found.clear()
        self.count = 0
        self.section_catches.clear()
        self.count_changed.emit(self.count)
        self.section_changed.emit(0)
