"""Load and validate the user-authored section route."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pokedex_counter.config import ROUTE_PATH


@dataclass(frozen=True)
class RouteSection:
    required: list[str]
    bonuses: list[str]
    minimum: int
    evolutions: set[str]


def _pokemon_number(name: str, pokemon_names: dict[str, str]) -> str:
    normalized = name.strip().upper()
    try:
        return pokemon_names[normalized]
    except KeyError as exc:
        raise ValueError(f"Unknown Pokémon name in route: {name!r}") from exc


def _normalize_name(value: str, pokemon_names: dict[str, str]) -> tuple[str, bool]:
    is_evolution = value.lower().startswith("evo:")
    if is_evolution:
        value = value[4:]
    return _pokemon_number(value, pokemon_names), is_evolution


def _normalize_sections(raw_sections, pokemon_names: dict[str, str]) -> list[RouteSection]:
    if not isinstance(raw_sections, list):
        raise ValueError("The route must contain a list of sections")

    sections: list[RouteSection] = []
    for index, raw_section in enumerate(raw_sections):
        if not isinstance(raw_section, (list, tuple)) or len(raw_section) != 2:
            raise ValueError(f"Route section {index} must contain two lists")
        required, bonuses = raw_section
        if not isinstance(required, list) or not isinstance(bonuses, list):
            raise ValueError(f"Route section {index} must contain two lists")
        normalized_required = [_normalize_name(name, pokemon_names) for name in required]
        normalized_bonuses = [_normalize_name(name, pokemon_names) for name in bonuses]
        sections.append(RouteSection(
            required=[name for name, _ in normalized_required],
            bonuses=[name for name, _ in normalized_bonuses],
            minimum=len(required),
            evolutions={
                name
                for name, marked in normalized_required + normalized_bonuses
                if marked
            },
        ))
    if not sections:
        raise ValueError("The route must contain at least one section")
    return sections


def load_route_sections(
    txt_path: Path = ROUTE_PATH,
) -> list[RouteSection]:
    """Load the line-oriented TXT form.

    Each TXT line is ``required names - bonus names``; the separator is
    optional when a section has no bonuses.
    """
    from pokedex_counter.services.detection_service import POKEMON_NAMES

    if not txt_path.is_file():
        raise FileNotFoundError(f"No route file found at {txt_path}")

    try:
        lines = txt_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"Failed to load route file {txt_path}: {exc}") from exc

    raw_sections = []
    for line_number, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        parts = line.split("-", 1)
        required_part = parts[0].strip()
        minimum = None
        if required_part.lower().startswith("min:"):
            minimum_text, _, required_part = required_part.partition(" ")
            try:
                minimum = int(minimum_text[4:])
            except ValueError as exc:
                raise ValueError(
                    f"Invalid minimum on route section {line_number}: {minimum_text!r}"
                ) from exc
        required = required_part.split()
        bonuses = parts[1].split() if len(parts) == 2 else []
        if not required:
            raise ValueError(f"Route section {line_number} has no required Pokémon")
        normalized_required = [_normalize_name(name, POKEMON_NAMES) for name in required]
        normalized_bonuses = [_normalize_name(name, POKEMON_NAMES) for name in bonuses]
        if minimum is None:
            minimum = len(required)
        if not 0 < minimum <= len(set(name for name, _ in normalized_required)):
            raise ValueError(f"Invalid minimum on route section {line_number}")
        raw_sections.append(RouteSection(
            required=[name for name, _ in normalized_required],
            bonuses=[name for name, _ in normalized_bonuses],
            minimum=minimum,
            evolutions={
                name
                for name, marked in normalized_required + normalized_bonuses
                if marked
            },
        ))
    return raw_sections
