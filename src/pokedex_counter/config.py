"""App-wide constants and settings."""

import sys
from pathlib import Path

APP_NAME = "Pokédex Counter"
APP_VERSION = "2.0"
ORGANIZATION_NAME = APP_NAME

# When frozen by PyInstaller, data files added via --add-data are extracted
# to sys._MEIPASS (a temp dir) instead of living next to this module.
if getattr(sys, "frozen", False):
    _PACKAGE_DIR = Path(sys._MEIPASS)
else:
    _PACKAGE_DIR = Path(__file__).resolve().parent

# Directory containing sprite images shown in the main window.
RESOURCES_DIR = _PACKAGE_DIR / "resources"
SPRITES_DIR = RESOURCES_DIR / "sprites_2"
SPRITES_BG_DIR = RESOURCES_DIR / "detection"
FONTS_DIR = RESOURCES_DIR / "fonts"
COMPARISON_DIR = RESOURCES_DIR / "comparison"
WR_JSON_PATH = COMPARISON_DIR / "WR.json"
ROUTE_DIR = RESOURCES_DIR / "route"
ROUTE_PATH = ROUTE_DIR / "route.txt"

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
LABEL_COLOR_WR_MARKED = "yellow"
LABEL_COLOR_OFF_ROUTE = "green"
LABEL_COLOR_BONUS = "red"
LABEL_COLOR_IGNORED = "gray"
LABEL_COLOR_REQUIRED = "dodgerblue"
LABEL_COLOR_SECTION_BONUS = "lightpink"
LABEL_COLOR_BOX_COUNT = "gray"

# Minimum gap (0-255 grayscale units) required between adjacent k-means
# shade-cluster centers for canonicalize_shades() to trust the clustering.
# Below this, treat the crop as having no reliable 4-shade structure
# (blank/transition frame) rather than rank-remapping noise into a
# fabricated full-contrast pattern.
MIN_SHADE_SEPARATION = 15.0

# Extra pixels of padding added around each calibrated ROI before matching,
# so cv2.matchTemplate can search for the best-aligned position instead of
# assuming the calibrated position is exactly right. Different capture
# sessions (even against the same physical setup) can drift by a pixel or
# two - sprite icons are blocky enough to tolerate that, but fine text
# glyphs are not, so this margin matters most for text screens.
ROI_SEARCH_MARGIN = 2

THRESHOLD = 0.85

GAMEBOY_SIZE = (160, 144)
FRAME_SIZE_DETECTION = (960, 540)
ROI_TEXTBOX = (0, 96, 160, 48)
ROI_IMG_CATCH = (8, 8, 56, 56)
ROI_IMG_EVOLVE = (56, 16, 56, 56)
ROI_IMG_TEXT = (9, 113, 62, 22)
FRAME_SIZE_CALIBRATION = (1920, 1080)
