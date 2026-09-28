"""Load and validate the user-authored section route."""

from dataclasses import dataclass, field
from pathlib import Path

from pokedex_counter.config import ROUTE_PATH


@dataclass(frozen=True)
class RouteCommand:
    name: str
    parameter: str


@dataclass(frozen=True)
class RouteSection:
    required: list[str]
    bonuses: list[str]
    minimum: int
    evolutions: set[str]
    commands_before: list[RouteCommand] = field(default_factory=list)
    commands_after: list[RouteCommand] = field(default_factory=list)


def parse_route_command(line: str) -> RouteCommand | None:
    """Parse a command line, leaving MIN:/EVO: route syntax alone."""
    line = line.strip().upper()
    name, separator, parameter = line.partition(":")
    if not separator or name in {"MIN", "EVO"}:
        return None
    if not parameter:
        raise ValueError(f"Route command {name!r} has no parameter")
    return RouteCommand(name, parameter)


def _normalize_name(name: str) -> tuple[str, bool]:
    from pokedex_counter.game_config import POKEMON_NAME_TO_DEX
    is_evolution = name.startswith("EVO:")
    if is_evolution:
        name = name[4:]
    if name not in POKEMON_NAME_TO_DEX:
        raise ValueError(f"Unknown Pokémon name in route: {name!r}")
    return name, is_evolution

def load_route_sections(
    txt_path: Path = ROUTE_PATH,
) -> list[RouteSection]:
    """Load the line-oriented TXT form.

    Pokemon lines are ``required names - bonus names``; the separator is
    optional when a section has no bonuses. Command-only lines are attached
    to the boundary after the preceding section.
    """
    if not txt_path.is_file():
        raise FileNotFoundError(f"No route file found at {txt_path}")

    try:
        lines = txt_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"Failed to load route file {txt_path}: {exc}") from exc

    raw_sections = []
    commands_before_first_section = []
    for line_number, line in enumerate(lines, 1):
        line = line.strip().upper()
        if not line:
            continue
        command = parse_route_command(line)
        if command is not None:
            if raw_sections:
                raw_sections[-1].commands_after.append(command)
            else:
                commands_before_first_section.append(command)
            continue
        parts = line.split("-", 1)
        required_part = parts[0].strip()
        minimum = None
        if required_part.startswith("MIN:"):
            minimum_text, _, required_part = required_part.partition(" ")
            try:
                minimum = int(minimum_text[4:])
            except ValueError as exc:
                raise ValueError(
                    f"Invalid minimum on route section line {line_number}: {minimum_text!r}"
                ) from exc
        required = required_part.split()
        bonuses = parts[1].split() if len(parts) == 2 else []
        if not required:
            raise ValueError(f"Route section line {line_number} has no required Pokémon")
        normalized_required = [_normalize_name(name) for name in required]
        normalized_bonuses = [_normalize_name(name) for name in bonuses]
        if minimum is None:
            minimum = len(required)
        if not 0 < minimum <= len(normalized_required):
            raise ValueError(f"Invalid minimum on route section line {line_number}")
        raw_sections.append(RouteSection(
            required=[name for name, _ in normalized_required],
            bonuses=[name for name, _ in normalized_bonuses],
            minimum=minimum,
            evolutions={
                name
                for name, marked in normalized_required + normalized_bonuses
                if marked
            },
            commands_before=commands_before_first_section,
        ))
        commands_before_first_section = []
    return raw_sections
