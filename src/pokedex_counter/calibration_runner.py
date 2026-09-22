import sys
from pathlib import Path

import cv2

from pokedex_counter.config import RESOURCES_DIR
from pokedex_counter.roi_writer import update_roi_constants
from pokedex_counter.services.calibration_service import CalibrationService
from pokedex_counter.vision.image_io import load_color

# _FILENAMES = {"CATCH": "catch.png", "EVOLVE": "evolve.png", "TEXT": "text.png"}
_FILENAMES = {"FULL": "full5.png"}

# None means "not calibrated yet" - roi_config.py skips any entry whose
# type has no locked position, and app.py shows a calibration prompt
# instead of running detection until at least one is locked. This seed
# only needs to exist so roi_writer's regex has `NAME = ...` lines to find
# and replace on the first-ever calibration; the file is otherwise blank.
_SEED_TEMPLATE = """ROI_CATCH = None
ROI_EVOLVE = None
ROI_TEXT = None
ROI_FULL = None
"""


def _writable_roi_calibration_path() -> Path:
    """Where calibration persists locked ROIs for next launch.

    Source/dev runs write straight into the package's roi_calibration.py
    (the gitignored file `roi_config.py` imports ROI_CATCH/EVOLVE/TEXT
    from). A frozen exe has no such writable file — its modules are baked
    into the bundle — so it gets its own roi_calibration.py next to the
    executable instead. Either way, run_calibration() also returns the
    locked ROIs so the current run doesn't depend on this write (or a
    re-import) succeeding.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "roi_calibration.py"
    return Path(__file__).resolve().parent / "roi_calibration.py"


def _ensure_seeded(config_path: Path) -> None:
    if config_path.exists():
        return

    config_path.write_text(_SEED_TEMPLATE)


def run_calibration(camera_index=2) -> dict[str, tuple[int, int, int, int]]:
    calibration_dir = RESOURCES_DIR / "calibration"

    templates = {}
    for name, filename in _FILENAMES.items():
        path = calibration_dir / filename
        img = load_color(path)
        if img is None:
            print(f"[Calibration] ERROR: could not load reference image {path}, skipping {name}")
            continue
        templates[name] = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if not templates:
        print("[Calibration] No reference images found, skipping calibration.")
        return {}

    print(f"[Calibration] Starting up — waiting to lock: {list(templates)}")
    locked = CalibrationService(camera_index=camera_index).run(templates)  # no timeout: waits as long as needed

    if not locked:
        print("[Calibration] Nothing locked, using existing ROI_* values.")
        return {}

    config_path = _writable_roi_calibration_path()
    try:
        _ensure_seeded(config_path)
        updated = update_roi_constants(config_path, locked)
        print(f"[Calibration] Updated {updated} in {config_path}")
    except OSError as exc:
        print(f"[Calibration] Could not persist calibrated ROIs to {config_path} ({exc}); using them for this session only.")

    return locked
