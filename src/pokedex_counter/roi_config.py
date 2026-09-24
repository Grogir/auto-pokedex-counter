# ROI_CATCH/ROI_EVOLVE/ROI_TEXT live in roi_calibration.py, a sibling module
# that's gitignored (see .gitignore) rather than committed - it holds this
# machine's camera calibration, which is personal/local and shouldn't show
# up as a diff every time this app is recalibrated. calibration_runner.py's
# run_calibration() rewrites that file in place via roi_writer.py.
#
# There are deliberately no default/fallback coordinates: a fresh checkout
# (or any ROI that's never been locked) has no idea where these boxes are
# on this player's specific capture setup, so guessing would just produce
# confident-looking nonsense. None means "not calibrated yet" - app.py
# shows a calibration prompt instead of running detection until it isn't.
try:
    from pokedex_counter.roi_calibration import ROI_CATCH, ROI_EVOLVE, ROI_TEXT
except ImportError:
    ROI_CATCH = ROI_EVOLVE = ROI_TEXT = None
try:
    from pokedex_counter.roi_calibration import ROI_FULL
except ImportError:
    ROI_FULL = None

# Dex numbers whose "obtained" event is only ever confirmed via a name-text
# banner (trade evolutions etc.) rather than a sprite match against
# ROI_CATCH/ROI_EVOLVE.
TEXT_NAMES = {"NIDORINO", "CLEFAIRY", "ABRA", "HITMONLEE", "PINSIR", "LAPRAS", "EEVEE", "PORYGON", "OMANYTE", "AERODACTYL", "DRATINI"}

# Dex numbers that have an ROI_EVOLVE screen event (something evolves into
# them). Used to sweep any evolution not explicitly routed into a section
# below into the final section - see build_catch_sections().
EVOLVE_NAMES = {
    "VENUSAUR", "CHARMELEON", "CHARIZARD", "WARTORTLE", "BLASTOISE", "BUTTERFREE", "KAKUNA", "BEEDRILL", "PIDGEOT", "RATICATE", "ARBOK", "RAICHU", "SANDSLASH",
    "NIDORINA", "NIDOQUEEN", "NIDOKING", "CLEFABLE", "NINETALES", "WIGGLYTUFF", "GOLBAT", "GLOOM", "VILEPLUME", "PARASECT", "VENOMOTH", "DUGTRIO",
    "PERSIAN", "GOLDUCK", "PRIMEAPE", "ARCANINE", "POLIWHIRL", "POLIWRATH", "KADABRA", "MACHOKE", "WEEPINBELL", "VICTREEBEL", "TENTACRUEL", "GRAVELER",
    "RAPIDASH", "SLOWBRO", "DODRIO", "DEWGONG", "MUK", "CLOYSTER", "HAUNTER", "HYPNO", "KINGLER", "ELECTRODE", "EXEGGUTOR",
    "MAROWAK", "RHYDON", "SEADRA", "SEAKING", "STARMIE", "GYARADOS", "VAPOREON", "JOLTEON", "FLAREON", "OMASTAR",
    "KABUTOPS", "DRAGONAIR",
}


# Within these sections, these dex numbers refer to their ROI_EVOLVE event
# rather than the default CATCH/TEXT one.
SECTION_EVOLVE_OVERRIDES: dict[int, set[str]] = {
    7: {"NIDORINA", "NIDOQUEEN", "PARASECT", "EXEGGUTOR"},  # section 8 (0-indexed 7)
    10: {"DRAGONAIR", "HAUNTER", "ARBOK", "KADABRA", "NIDOKING", "CLEFABLE", "PARASECT"},  # section 11 (0-indexed 10)
    11: {"HAUNTER", "ARBOK", "KADABRA", "NIDOKING", "CLEFABLE", "PARASECT"},  # dedicated evolution section - same five, listed again here
}

# The dex number whose detection advances to the next section. The final
# section has none - there's nothing left to advance to.
# SECTION_TRIGGERS: list[str | None] = [
#     names[-1] if idx < len(CATCH_SECTIONS_RAW) - 1 else None
#     for idx, names in enumerate(CATCH_SECTIONS_RAW)
# ]

# The route file is the source of truth for the active section system. Keep
# the legacy names below as compatibility data for the WR/evolution views.
from pokedex_counter.game_config import POKEMON_NAME_TO_DEX, ROUTE_SECTIONS, is_evolution

CATCH_SECTIONS_RAW = [section.required + section.bonuses for section in ROUTE_SECTIONS]
SECTION_TRIGGERS = [
    required[-1] if index < len(CATCH_SECTIONS_RAW) else None
    for index, required in enumerate(CATCH_SECTIONS_RAW)
]


def _entry_type(section_index: int, name: str) -> str:
    if name in ROUTE_SECTIONS[section_index].evolutions:
        return "EVOLVE"
    if name in TEXT_NAMES:
        return "TEXT"
    return "CATCH"


def build_catch_sections() -> list[list[tuple[str, str]]]:
    """Expand CATCH_SECTIONS_RAW into (name, roi_label) pairs, then sweep
    every EVOLVE-type dex number not already placed in some section onto
    the end of the final section - evolutions not explicitly routed
    earlier all get caught up in one pass at the end of the run."""
    sections = [
        [(name, _entry_type(idx, name)) for name in names]
        for idx, names in enumerate(CATCH_SECTIONS_RAW)
    ]
    placed_evolves = {name for section in sections for name, rtype in section if rtype == "EVOLVE"}
    # sections[-1] += [(name, "EVOLVE") for name in sorted(
    #     EVOLVE_NAMES - placed_evolves, key=POKEMON_NAMES.__getitem__
    # )]
    sections += [[
        (name, "EVOLVE")
        for name in sorted(EVOLVE_NAMES - placed_evolves, key=POKEMON_NAME_TO_DEX.__getitem__)
    ]]
    return sections


CATCH_SECTIONS: list[list[tuple[str, str]]] = build_catch_sections()


def build_evolution_entries() -> list[set[str]]:
    """Per section, the dex numbers that can ONLY be obtained there by
    evolving - i.e. their entry is EVOLVE and the section offers no CATCH or
    TEXT entry for them as well. A name with both kinds of entry in one
    section is left out: it could genuinely have been caught there, and the
    detector can't say which of the two ROIs won, so it keeps the benefit of
    the doubt."""
    entries = []
    for section in CATCH_SECTIONS:
        evolved = {name for name, roi_label in section if roi_label == "EVOLVE"}
        obtained_otherwise = {name for name, roi_label in section if roi_label != "EVOLVE"}
        entries.append(evolved - obtained_otherwise)
    return entries


EVOLUTION_ENTRIES: list[set[str]] = build_evolution_entries()


def build_detection_entries(templates: dict, locked: dict[str, tuple[int, int, int, int]] | None = None):
    """Build (name, roi, template, section_index) quadruples from
    CATCH_SECTIONS, substituting freshly calibrated boxes (as returned by
    run_calibration) for ROI_CATCH/ROI_EVOLVE/ROI_TEXT in-memory for
    this session. Entries whose roi type has no calibrated position yet
    (still None) are skipped entirely - there's nowhere to look for them.

    run_calibration() persists locked ROIs back into this file on a
    best-effort basis (e.g. it can't when frozen into an exe), but this app
    run must use them regardless of whether that write succeeded - hence
    applying `locked` here instead of relying on re-importing this module.
    """
    locked = locked or {}
    effective = {
        "CATCH": locked.get("CATCH", ROI_CATCH),
        "EVOLVE": locked.get("EVOLVE", ROI_EVOLVE),
        "TEXT": locked.get("TEXT", ROI_TEXT),
    }
    return [
        (name, effective[roi_label], templates[name], section_index)
        for section_index, section in enumerate(CATCH_SECTIONS)
        for name, roi_label in section
        if effective[roi_label] is not None
    ]

def is_calibrated() -> bool:
    return ROI_FULL is not None
