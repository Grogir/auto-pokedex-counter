from pathlib import Path

from pokedex_counter.vision.image_io import load_gray
from pokedex_counter.game_config import POKEMON_DEX_TO_NAME
from pokedex_counter.vision.template_matching import canonicalize_shades

class TemplateService:
    def __init__(self, folder: Path):
        self.templates = {}

        for p in folder.iterdir():
            if p.suffix.lower() not in {".png", ".jpg"}:
                continue

            name = POKEMON_DEX_TO_NAME.get(int(p.stem));
            if name is None:
                print(f"[TemplateService] WARNING: no Pokémon name for dex number {p.stem}, skipping")
                continue

            gray = load_gray(p)
            if gray is None:
                print(f"[TemplateService] WARNING: failed to load '{p.name}', skipping")
                continue

            canonical = canonicalize_shades(gray)

            self.templates[name] = (gray, canonical)
