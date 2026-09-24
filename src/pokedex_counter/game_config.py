"""Route-backed game configuration shared by the controller and UI."""

from pokedex_counter.services.route_service import load_route_sections

ROUTE_SECTIONS = load_route_sections()

def is_evolution(section_index: int, name: str) -> bool:
    return (
        section_index == len(ROUTE_SECTIONS)
        or (
            0 <= section_index < len(ROUTE_SECTIONS)
            and name in ROUTE_SECTIONS[section_index].evolutions
        )
    )

# Dex numbers that count as a "bonus" catch. Purely cosmetic: with the
# "Highlight bonuses" setting on, catching one of these lights it up red
# instead of the usual black. Detection and routing ignore this entirely,
# so a number listed here doesn't have to appear in CATCH_SECTIONS_RAW.
#
# Every one of these is an evolved form, so "obtained" alone doesn't make it
# a bonus - only actually catching it in the wild does, since evolving into
# it is the routine path the highlight exists to stand out from. See
# GameController.is_evolution() uses the route metadata to tell the two apart.
#
# In dex order: Raticate, Raichu, Sandslash, Wigglytuff, Golbat, Parasect,
# Venomoth, Golduck, Kadabra, Machoke, Graveler, Dodrio, Dewgong, Muk,
# Hypno, Kingler, Electrode, Marowak, Rhydon.
BONUSES: set[str] = {
    "20", "26", "28", "40", "42", "47", "49", "55", "64", "67",
    "75", "85", "87", "89", "97", "99", "101", "105", "112",
}
