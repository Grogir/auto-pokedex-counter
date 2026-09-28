"""App-wide constants and settings."""

import sys
from importlib.metadata import version
from pathlib import Path

APP_NAME = "Pokédex Counter"
APP_VERSION = version("pokedex_counter")
ORGANIZATION_NAME = APP_NAME

# When frozen by PyInstaller, data files added via --add-data are extracted
# to sys._MEIPASS (a temp dir) instead of living next to this module.
if getattr(sys, "frozen", False):
    _PACKAGE_DIR = Path(sys._MEIPASS)
else:
    _PACKAGE_DIR = Path(__file__).resolve().parent

# Directory containing sprite images shown in the main window.
RESOURCES_DIR = _PACKAGE_DIR / "resources"
CALIBRATION_DIR = RESOURCES_DIR / "calibration"
COMPARISON_DIR = RESOURCES_DIR / "comparison"
DETECTION_IMAGE_DIR = RESOURCES_DIR / "detection"
FONTS_DIR = RESOURCES_DIR / "fonts"
ROUTE_DIR = RESOURCES_DIR / "route"
SPRITES_DIR = RESOURCES_DIR / "sprites_2"
DETECTION_TEXTBOX_DIR = RESOURCES_DIR / "textbox"


WR_JSON_PATH = COMPARISON_DIR / "WR.json"
ROUTE_PATH = ROUTE_DIR / "route.txt"
CALIBRATION_FILENAMES = {"GAME_AREA": "full5.png"}


# Where a completed run's per-section catch order is saved (see
# services/pb_service.py). Unlike WR_JSON_PATH (a bundled read-only
# reference), this is user-generated - and when frozen, _PACKAGE_DIR points
# at PyInstaller's ephemeral extraction dir (sys._MEIPASS), which vanishes
# when the process exits. This mirrors calibration_runner.py's writable-path
# split for roi_calibration.py: next to the executable when frozen, next to
# the comparison resources when running from source.
if getattr(sys, "frozen", False):
    PB_JSON_PATH = Path(sys.executable).resolve().parent / "comparison" / "PB.json"
else:
    PB_JSON_PATH = COMPARISON_DIR / "PB.json"

# Label background colors.
LABEL_COLOR_CATCH = "black"
LABEL_COLOR_BONUS = "red"
LABEL_COLOR_WR_ONLY = "yellow"
LABEL_COLOR_WR_AND_PLAYER = "orange"
LABEL_COLOR_IGNORED = "gray"
LABEL_COLOR_SECTION_REQUIRED = "dodgerblue"
LABEL_COLOR_SECTION_BONUS = "lightpink"
