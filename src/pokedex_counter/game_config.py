"""Route-backed game configuration shared by the controller and UI."""

from pokedex_counter.services.route_service import load_route_sections

POKEMON_NAME_TO_DEX: dict[str, int] = {
    "BULBASAUR": 1, "IVYSAUR": 2, "VENUSAUR": 3, "CHARMANDER": 4,
    "CHARMELEON": 5, "CHARIZARD": 6, "SQUIRTLE": 7, "WARTORTLE": 8,
    "BLASTOISE": 9, "CATERPIE": 10, "METAPOD": 11, "BUTTERFREE": 12,
    "WEEDLE": 13, "KAKUNA": 14, "BEEDRILL": 15, "PIDGEY": 16,
    "PIDGEOTTO": 17, "PIDGEOT": 18, "RATTATA": 19, "RATICATE": 20,
    "SPEAROW": 21, "FEAROW": 22, "EKANS": 23, "ARBOK": 24, "PIKACHU": 25,
    "RAICHU": 26, "SANDSHREW": 27, "SANDSLASH": 28, "NIDORAN♀": 29,
    "NIDORINA": 30, "NIDOQUEEN": 31, "NIDORAN♂": 32, "NIDORINO": 33,
    "NIDOKING": 34, "CLEFAIRY": 35, "CLEFABLE": 36, "VULPIX": 37,
    "NINETALES": 38, "JIGGLYPUFF": 39, "WIGGLYTUFF": 40, "ZUBAT": 41,
    "GOLBAT": 42, "ODDISH": 43, "GLOOM": 44, "VILEPLUME": 45, "PARAS": 46,
    "PARASECT": 47, "VENONAT": 48, "VENOMOTH": 49, "DIGLETT": 50,
    "DUGTRIO": 51, "MEOWTH": 52, "PERSIAN": 53, "PSYDUCK": 54,
    "GOLDUCK": 55, "MANKEY": 56, "PRIMEAPE": 57, "GROWLITHE": 58,
    "ARCANINE": 59, "POLIWAG": 60, "POLIWHIRL": 61, "POLIWRATH": 62,
    "ABRA": 63, "KADABRA": 64, "ALAKAZAM": 65, "MACHOP": 66,
    "MACHOKE": 67, "MACHAMP": 68, "BELLSPROUT": 69, "WEEPINBELL": 70,
    "VICTREEBEL": 71, "TENTACOOL": 72, "TENTACRUEL": 73, "GEODUDE": 74,
    "GRAVELER": 75, "GOLEM": 76, "PONYTA": 77, "RAPIDASH": 78,
    "SLOWPOKE": 79, "SLOWBRO": 80, "MAGNEMITE": 81, "MAGNETON": 82,
    "FARFETCH'D": 83, "DODUO": 84, "DODRIO": 85, "SEEL": 86,
    "DEWGONG": 87, "GRIMER": 88, "MUK": 89, "SHELLDER": 90,
    "CLOYSTER": 91, "GASTLY": 92, "HAUNTER": 93, "GENGAR": 94,
    "ONIX": 95, "DROWZEE": 96, "HYPNO": 97, "KRABBY": 98, "KINGLER": 99,
    "VOLTORB": 100, "ELECTRODE": 101, "EXEGGCUTE": 102, "EXEGGUTOR": 103,
    "CUBONE": 104, "MAROWAK": 105, "HITMONLEE": 106, "HITMONCHAN": 107,
    "LICKITUNG": 108, "KOFFING": 109, "WEEZING": 110, "RHYHORN": 111,
    "RHYDON": 112, "CHANSEY": 113, "TANGELA": 114, "KANGASKHAN": 115,
    "HORSEA": 116, "SEADRA": 117, "GOLDEEN": 118, "SEAKING": 119,
    "STARYU": 120, "STARMIE": 121, "MR.MIME": 122, "SCYTHER": 123,
    "JYNX": 124, "ELECTABUZZ": 125, "MAGMAR": 126, "PINSIR": 127,
    "TAUROS": 128, "MAGIKARP": 129, "GYARADOS": 130, "LAPRAS": 131,
    "DITTO": 132, "EEVEE": 133, "VAPOREON": 134, "JOLTEON": 135,
    "FLAREON": 136, "PORYGON": 137, "OMANYTE": 138, "OMASTAR": 139,
    "KABUTO": 140, "KABUTOPS": 141, "AERODACTYL": 142, "SNORLAX": 143,
    "ARTICUNO": 144, "ZAPDOS": 145, "MOLTRES": 146, "DRATINI": 147,
    "DRAGONAIR": 148, "DRAGONITE": 149, "MEWTWO": 150, "MEW": 151,
}
POKEMON_DEX_TO_NAME = {number: name for name, number in POKEMON_NAME_TO_DEX.items()}

CAN_EVOLVE = {"BULBASAUR", "IVYSAUR", "CHARMANDER", "CHARMELEON", "SQUIRTLE", "WARTORTLE", "CATERPIE", "METAPOD", "WEEDLE", "KAKUNA", "PIDGEY", "PIDGEOTTO", "RATTATA", "SPEAROW", "EKANS", "PIKACHU", "SANDSHREW", "NIDORAN♀", "NIDORINA", "NIDORAN♂", "NIDORINO", "CLEFAIRY", "VULPIX", "JIGGLYPUFF", "ZUBAT", "ODDISH", "GLOOM", "PARAS", "VENONAT", "DIGLETT", "MEOWTH", "PSYDUCK", "MANKEY", "GROWLITHE", "POLIWAG", "POLIWHIRL", "ABRA", "KADABRA", "MACHOP", "MACHOKE", "BELLSPROUT", "WEEPINBELL", "TENTACOOL", "GEODUDE", "GRAVELER", "PONYTA", "SLOWPOKE", "MAGNEMITE", "DODUO", "SEEL", "GRIMER", "SHELLDER", "GASTLY", "HAUNTER", "DROWZEE", "KRABBY", "VOLTORB", "EXEGGCUTE", "CUBONE", "KOFFING", "RHYHORN", "HORSEA", "GOLDEEN", "STARYU", "MAGIKARP", "EEVEE", "OMANYTE", "KABUTO", "DRATINI", "DRAGONAIR"}

def evolutions_of(name: str) -> list[str]:
    if name == "EEVEE":
        return ["VAPOREON", "JOLTEON", "FLAREON"]
    if name in CAN_EVOLVE:
        return [POKEMON_DEX_TO_NAME[POKEMON_NAME_TO_DEX[name] + 1]]
    return []

def previous_form_of(name: str) -> str | None:
    if name in POKEMON_NAME_TO_DEX:
        if name in ("VAPOREON", "JOLTEON", "FLAREON"):
            return "EEVEE"
        previous = POKEMON_DEX_TO_NAME.get(POKEMON_NAME_TO_DEX[name] - 1)
        if previous in CAN_EVOLVE:
            return previous
    return None

ROUTE_SECTIONS = load_route_sections()

def _last_catch_section() -> int:
    for section_index in reversed(range(len(ROUTE_SECTIONS))):
        section = ROUTE_SECTIONS[section_index]
        if set(section.required) != section.evolutions:
            return section_index
    return 0
LAST_CATCH_SECTION = _last_catch_section()

def is_evolution(section_index: int, name: str) -> bool:
    return (
        section_index == len(ROUTE_SECTIONS)
        or
        section_index > LAST_CATCH_SECTION and name not in ROUTE_SECTIONS[LAST_CATCH_SECTION].bonuses
        or
        0 <= section_index < len(ROUTE_SECTIONS) and name in ROUTE_SECTIONS[section_index].evolutions
    )

def _final_section_mons() -> set[str]:
    """Return the set of Pokémon names that are not caught before the end."""
    mons = set(POKEMON_NAME_TO_DEX.keys())
    for section in ROUTE_SECTIONS:
        mons -= set(section.required)
    return mons
FINAL_SECTION = _final_section_mons()

# Dex numbers that count as a "bonus" catch. Purely cosmetic: with the
# "Highlight bonuses" setting on, catching one of these lights it up red
# instead of the usual black. Detection and routing ignore this entirely.
# Every one of these is an evolved form, so "obtained" alone doesn't make it
# a bonus - only actually catching it in the wild does, since evolving into
# it is the routine path the highlight exists to stand out from. See
# is_evolution() uses the route metadata to tell the two apart.
BONUSES: set[str] = {
    "RATICATE", "RAICHU", "SANDSLASH", "WIGGLYTUFF", "GOLBAT", "PARASECT",
    "VENOMOTH", "GOLDUCK", "KADABRA", "MACHOKE", "GRAVELER", "DODRIO",
    "DEWGONG", "MUK", "HYPNO", "KINGLER", "ELECTRODE", "MAROWAK", "RHYDON"
}
