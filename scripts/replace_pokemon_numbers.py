"""Replace quoted Pokédex numbers in a file with canonical Pokémon names."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from pokedex_counter.game_config import POKEMON_DEX_TO_NAME

_QUOTED_NUMBER = re.compile(
    r"""(?P<quote>["'])(?P<number>0|[1-9][0-9]?|1[0-4][0-9]|150|151)(?P=quote)(?!\s*:)"""
)


def replace_pokemon_numbers(path: Path) -> int:
    """Replace exact quoted Pokédex numbers in ``path`` and return the count."""
    content = path.read_text(encoding="utf-8")

    def replacement(match: re.Match[str]) -> str:
        name = POKEMON_DEX_TO_NAME.get(int(match.group("number")))
        return f"{match.group('quote')}{name}{match.group('quote')}" if name else match.group(0)

    converted, count = _QUOTED_NUMBER.subn(replacement, content)
    if count:
        path.write_text(converted, encoding="utf-8")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="file to update in place")
    args = parser.parse_args()
    if not args.path.is_file():
        parser.error(f"file not found: {args.path}")
    print(f"Replaced {replace_pokemon_numbers(args.path)} Pokémon number(s) in {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
