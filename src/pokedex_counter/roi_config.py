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

# Dex numbers whose "obtained" event is only ever confirmed via a name-text
# banner (trade evolutions etc.) rather than a sprite match against
# ROI_CATCH/ROI_EVOLVE.
TEXT_NAMES = {"33", "35", "63", "106", "127", "131", "133", "137", "138", "142", "147"}

# Dex numbers that have an ROI_EVOLVE screen event (something evolves into
# them). Used to sweep any evolution not explicitly routed into a section
# below into the final section - see build_catch_sections().
EVOLVE_NAMES = {
    "3", "5", "6", "8", "9", "12", "14", "15", "18", "20", "24", "26", "28",
    "30", "31", "34", "36", "38", "40", "42", "44", "45", "47", "49", "51",
    "53", "55", "57", "59", "61", "62", "64", "67", "70", "71", "73", "75",
    "78", "80", "85", "87", "89", "91", "93", "97", "99", "101", "103",
    "105", "112", "117", "119", "121", "130", "134", "135", "136", "139",
    "141", "148",
}

# Dex numbers that count as a "bonus" catch. Purely cosmetic: with the
# "Highlight bonuses" setting on, catching one of these lights it up red
# instead of the usual black. Detection and routing ignore this entirely,
# so a number listed here doesn't have to appear in CATCH_SECTIONS_RAW.
#
# Every one of these is an evolved form, so "obtained" alone doesn't make it
# a bonus - only actually catching it in the wild does, since evolving into
# it is the routine path the highlight exists to stand out from. See
# is_evolution() for how the two are told apart.
#
# In dex order: Raticate, Raichu, Sandslash, Wigglytuff, Golbat, Parasect,
# Venomoth, Golduck, Kadabra, Machoke, Graveler, Dodrio, Dewgong, Muk,
# Hypno, Kingler, Electrode, Marowak, Rhydon.
BONUSES: set[str] = {
    "20", "26", "28", "40", "42", "47", "49", "55", "64", "67",
    "75", "85", "87", "89", "97", "99", "101", "105", "112",
}

# Hand-authored catch route: this specific playthrough's actual order,
# which does NOT follow ascending dex-number order (some Pokemon are only
# reachable well out of dex order, or via a detour). Detection only looks
# for the Pokemon in the currently active section (see DetectionService);
# what advances to the next one is SECTION_TRIGGERS, not position in this
# list, so order within a section doesn't matter. A dex number may repeat
# across sections if it can legitimately be caught in more than one of
# them.
CATCH_SECTIONS_RAW: list[list[str]] = [
    ["1", "16", "10", "50", "51", "46", "29", "32", "102", "23", "122"],
    ["76", "97", "42", "28", "47", "64", "82", "40", "128", "113", "101",
     "85", "49", "26", "65", "112", "105", "150", "115"],
    ["90", "54", "55", "42", "98", "99", "86", "87", "120", "129", "144"],
    ["66", "67", "74", "75", "42", "105", "49", "41", "95", "67", "68", "123"],
    ["21", "96", "27", "107", "58", "50", "109", "146", "11", "48"],
    ["92", "126", "94", "22", "37", "19", "20", "17", "72", "4", "114"],
    ["21", "19", "84", "20", "111", "11", "140", "116", "149", "143", "151"],
    ["118", "39", "104", "47", "103", "30", "31", "43"],
    ["25", "81", "26", "100", "145", "83", "106", "7"],
    ["33", "35", "63", "127", "137", "147", "69", "56", "2", "131", "13"],
    ["138", "142", "133", "124", "132", "52", "77", "88", "89", "110", "125",
     "60", "79", "108", "93", "24", "64", "34", "36", "148"],
    ["93", "24", "64", "34", "36"],  # dedicated evolution section - these
    # five repeat from the section above (still catchable there too); the
    # rest is filled in by build_catch_sections()'s sweep
]

# Within these sections, these dex numbers refer to their ROI_EVOLVE event
# rather than the default CATCH/TEXT one.
SECTION_EVOLVE_OVERRIDES: dict[int, set[str]] = {
    7: {"30", "31", "47", "103"},  # section 8 (0-indexed 7)
    10: {"148", "93", "24", "64", "34", "36"},  # section 11 (0-indexed 10)
    11: {"93", "24", "64", "34", "36"},  # dedicated evolution section - same five, listed again here
}


def _entry_type(section_index: int, name: str) -> str:
    if name in SECTION_EVOLVE_OVERRIDES.get(section_index, ()):
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
    sections[-1] += [(name, "EVOLVE") for name in sorted(EVOLVE_NAMES - placed_evolves, key=int)]
    return sections


CATCH_SECTIONS: list[list[tuple[str, str]]] = build_catch_sections()


def build_section_triggers() -> list[list[str]]:
    """The dex numbers that must ALL be caught before the run moves on to
    the next section: every Pokemon this is the LAST section to offer.
    Order among them doesn't matter - the section ends once none are left.

    This replaced a single trigger, taken as the section's last entry, which
    quietly assumed the route is always walked in order. Catching that one
    Pokemon early ended the section while the rest were still uncaught, and
    DetectionService only ever matches the active section's templates (see
    _active_section), so anything skipped that way stayed invisible for the
    rest of the run.

    Keying on the last chance rather than on the whole section is what makes
    this safe for a dex number the route offers more than once: requiring it
    the first time round would stall a run that legitimately saves it for
    later, but by its final appearance there is no later left to save it
    for. Catching it early still counts - the check is just membership in
    what's been detected, so an earlier catch satisfies it immediately.

    Sections are read from CATCH_SECTIONS rather than CATCH_SECTIONS_RAW so
    the final section's swept-in evolutions count as an appearance too: a
    Pokemon catchable early but evolvable at the end has its last chance
    there, and so holds no earlier section open.

    BONUSES are excluded outright. A bonus is an optional wild catch of
    something you'd otherwise evolve into, so the section has to end whether
    or not it was taken. Today every bonus is also an evolution, so the rule
    above would already drop it - but one that isn't would silently become
    mandatory.

    Derived rather than hand-listed so re-authoring the route can't leave a
    stale trigger behind. The final section gets an empty list; there's
    nothing left to advance to."""
    last_chance: dict[str, int] = {}
    for section_index, section in enumerate(CATCH_SECTIONS):
        for name, _roi_label in section:
            if name not in BONUSES:
                last_chance[name] = section_index

    triggers = [
        [
            name
            for name in dict.fromkeys(name for name, _roi_label in section)
            if last_chance.get(name) == section_index
        ]
        for section_index, section in enumerate(CATCH_SECTIONS)
    ]
    triggers[-1] = []
    return triggers


SECTION_TRIGGERS: list[list[str]] = build_section_triggers()


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


def is_evolution(section_index: int, name: str) -> bool:
    """Whether obtaining `name` while section `section_index` is active means
    it evolved rather than that it was caught."""
    if not 0 <= section_index < len(EVOLUTION_ENTRIES):
        return False
    return name in EVOLUTION_ENTRIES[section_index]


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
