"""App-wide constants and settings."""

import sys
from pathlib import Path

APP_NAME = "Pokédex Counter"
APP_VERSION = "0.4.0"
ORGANIZATION_NAME = APP_NAME

# When frozen by PyInstaller, data files added via --add-data are extracted
# to sys._MEIPASS (a temp dir) instead of living next to this module.
if getattr(sys, "frozen", False):
    _PACKAGE_DIR = Path(sys._MEIPASS)
else:
    _PACKAGE_DIR = Path(__file__).resolve().parent

# Directory containing sprite images shown in the main window.
RESOURCES_DIR = _PACKAGE_DIR / "resources"
SPRITES_DIR = RESOURCES_DIR / "sprites"
SPRITES_BG_DIR = RESOURCES_DIR / "sprites_background"
FONTS_DIR = RESOURCES_DIR / "fonts"
COMPARISON_DIR = RESOURCES_DIR / "comparison"
WR_JSON_PATH = COMPARISON_DIR / "WR.json"

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

THRESHOLD = 0.85

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
# glyphs are not, so this margin matters most for ROI_TEXT.
ROI_SEARCH_MARGIN = 4

FRAME_SIZE = (960, 540)
FRAME_SIZE_CALIBRATION = (1920, 1080)
