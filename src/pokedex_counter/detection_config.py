from pokedex_counter.config import DETECTION_TEXTBOX_DIR

# GAME_AREA lives in roi_calibration.py, a sibling module that's gitignored.
# It holds this machine's camera calibration, which is personal/local and shouldn't show up as a diff every time this app is recalibrated.
# calibration_runner.py's run_calibration() rewrites that file in place via roi_writer.py.
# There are deliberately no default/fallback coordinates. None means "not calibrated yet".
try:
    from pokedex_counter.roi_calibration import GAME_AREA
except ImportError:
    GAME_AREA = None

def is_calibrated() -> bool:
    return GAME_AREA is not None


GAMEBOY_SIZE = (160, 144)
FRAME_SIZE_DETECTION = (960, 540)
FRAME_SIZE_CALIBRATION = (1920, 1080)


DETECTION_TYPE = {"NONE": 0, "TEXT": 1, "SPRITE": 2}


ROI_TEXTBOX = (0, 96, 160, 48)
TEXTBOX_TOP_FILE_PATH = DETECTION_TEXTBOX_DIR / "top.png"
TEXTBOX_BOTTOM_FILE_PATH = DETECTION_TEXTBOX_DIR / "bottom.png"
CHARSET_FILE_PATH = DETECTION_TEXTBOX_DIR / "charset.png"
CHARSET = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P",
    "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "(", ")", ":", ";", "[", "]",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p",
    "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "é","'d","'l","'s","'t","'v",
    " ", "_", "_", "_", "_", "_", "_", "_", "_", "_", "_", "_", "_", "_", "_", "_",
    "_", "_", "_", "_", "_", "_", "_", "_", "_", "_", "_", "_", "_", "_", "_", "_",
    "'","PK","MN", "-","'r","'m", "?", "!", ".", "_", "_", "_", "_", "_", " ", "♂",
    "₽", "×", ".", "/", ",", "♀", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
]


ROI_IMAGE = {
    "CATCH": (8, 8, 56, 56),
    "EVOLVE": (56, 16, 56, 56),
    "TEXT": (9, 113, 62, 22),
}

DETECTION_IMAGE_THRESHOLD = 0.85

# Extra pixels of padding added around each calibrated ROI before matching,
# so cv2.matchTemplate can search for the best-aligned position instead of
# assuming the calibrated position is exactly right. Different capture
# sessions (even against the same physical setup) can drift by a pixel or
# two - sprite icons are blocky enough to tolerate that, but fine text
# glyphs are not, so this margin matters most for text screens.
ROI_SEARCH_MARGIN = 2

# Dex numbers whose "obtained" event is only ever confirmed via a name-text
# banner (trade evolutions etc.) rather than a sprite match against.
DETECTION_IMAGE_TEXT_NAMES = {"NIDORINO", "CLEFAIRY", "ABRA", "HITMONLEE", "PINSIR", "LAPRAS", "EEVEE", "PORYGON", "OMANYTE", "AERODACTYL", "DRATINI"}
