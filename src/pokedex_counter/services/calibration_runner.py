import sys
from pathlib import Path

import cv2

from pokedex_counter.config import CALIBRATION_FILENAMES, RESOURCES_DIR
from pokedex_counter.services.calibration_service import CalibrationService
from pokedex_counter.services.roi_writer import update_roi_constants
from pokedex_counter.vision.image_io import load_color

# None means "not calibrated yet" - app.py shows a calibration prompt
# instead of running detection until one is locked. This seedonly needs
# to exist so roi_writer's regex has `NAME = ...` lines to find and
# replace on the first-ever calibration.
_SEED_TEMPLATE = "GAME_AREA = None\n"


def _writable_saved_calibration_path() -> Path:
    """Where calibration persists locked ROIs for next launch.
    Source/dev runs write straight into the package's saved_calibration.py
    A frozen exe has no such writable file — its modules are baked
    into the bundle — so it gets its own saved_calibration.py next to the
    executable instead. Either way, run_calibration() also returns the
    locked ROIs so the current run doesn't depend on this write (or a
    re-import) succeeding.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "saved_calibration.py"
    return Path(__file__).resolve().parent.parent / "saved_calibration.py"


def _ensure_seeded(config_path: Path) -> None:
    if not config_path.exists():
        config_path.write_text(_SEED_TEMPLATE)


def run_calibration(calibration_service: CalibrationService) -> None:
    calibration_dir = RESOURCES_DIR / "calibration"
    templates = {}
    for name, filename in CALIBRATION_FILENAMES.items():
        path = calibration_dir / filename
        img = load_color(path)
        if img is None:
            print(f"[Calibration] ERROR: could not load reference image {path}, skipping {name}")
            continue
        templates[name] = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    calibration_service.start(templates)


def save_calibration_results(
    locked: dict[str, tuple[int, int, int, int]],
) -> None:
    if not locked:
        print("[Calibration] Nothing locked, using the existing values.")
        return

    config_path = _writable_saved_calibration_path()
    try:
        _ensure_seeded(config_path)
        updated = update_roi_constants(config_path, locked)
        print(f"[Calibration] Updated {updated} in {config_path}")
    except OSError as exc:
        print(f"[Calibration] Could not persist calibrated ROIs to {config_path} ({exc}); using them for this session only.")
