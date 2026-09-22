from pathlib import Path

from pokedex_counter.vision.image_io import load_gray

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

            self.templates[p.stem] = img
