import ast
import os
import re
from pathlib import Path


def update_roi_constants(config_path: Path, locked: dict[str, tuple[int, int, int, int]]) -> list[str]:
    text = config_path.read_text()
    updated = []

    for key, box in locked.items():
        const_name = key
        if const_name is None:
            continue

        expected = tuple(box)
        # Matches either a real tuple (already-calibrated value being
        # updated again) or the literal `None` placeholder written for an
        # entry that hasn't been calibrated yet (see roi_config.py).
        pattern = re.compile(rf"^{const_name}\s*=\s*(?:\([^)]*\)|None)", re.MULTILINE)
        replacement = f"{const_name} = {expected}"

        new_text, count = pattern.subn(replacement, text)
        if count == 0:
            print(f"[roi_writer] WARNING: could not find `{const_name} = (...)` in {config_path}, skipping")
            continue
        if count > 1:
            print(f"[roi_writer] WARNING: found {count} matches for `{const_name}` — updated all")

        match = pattern.search(new_text)
        actual = ast.literal_eval(match.group().split("=", 1)[1].strip())
        if actual != expected:
            raise ValueError(
                f"[roi_writer] Refusing to write {config_path}: round-trip check for "
                f"{const_name} produced {actual!r}, expected {expected!r}"
            )

        text = new_text
        updated.append(const_name)

    if updated:
        tmp_path = config_path.with_suffix(config_path.suffix + ".tmp")
        tmp_path.write_text(text)
        os.replace(tmp_path, config_path)

    return updated
