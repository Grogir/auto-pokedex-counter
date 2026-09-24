from pathlib import Path

from pokedex_counter.vision.image_io import load_gray
from pokedex_counter.game_config import POKEMON_DEX_TO_NAME

class TemplateService:
    def __init__(self, folder: Path):
        self.templates = {}

        for p in folder.iterdir():
            if p.suffix.lower() not in {".png", ".jpg"}:
                continue

            img = load_gray(p)

            if img is None:
                print(f"[TemplateService] WARNING: failed to load '{p.name}', skipping")
                continue

            self.templates[POKEMON_DEX_TO_NAME.get(int(p.stem), p.stem)] = img
