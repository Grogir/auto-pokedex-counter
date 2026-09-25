# vision/detector.py
import cv2
from PySide6.QtCore import QObject, Signal

from pokedex_counter.config import (
    GAMEBOY_SIZE,
    ROI_SEARCH_MARGIN,
    ROI_TEXTBOX,
    THRESHOLD,
)
from pokedex_counter.vision.image_io import load_gray
from pokedex_counter.vision.template_matching import canonicalize_shades

from pokedex_counter.config import RESOURCES_DIR
from pokedex_counter.game_config import POKEMON_NAME_TO_DEX
TEXTBOX_FILE_TOP = "top.png"
TEXTBOX_FILE_BOTTOM = "bottom.png"
CHARSET_FILE = "charset.png"
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


try:
    from pokedex_counter.roi_calibration import GAME_AREA
except ImportError:
    GAME_AREA = None

class DetectionService(QObject):
    detection = Signal(str)
    debug_scores = Signal(str, float)
    def __init__(self, roi_templates, threshold=THRESHOLD, debug=False, section_provider=None):
        super().__init__()
        self.threshold = threshold
        self.debug = debug
        self._detected: set[str] = set()
        self._last_detected = None
        self._section_provider = section_provider
        self._game_area = GAME_AREA

        self._textbox_top = load_gray(RESOURCES_DIR / "textbox" / TEXTBOX_FILE_TOP)
        self._textbox_bottom = load_gray(RESOURCES_DIR / "textbox" / TEXTBOX_FILE_BOTTOM)
        self._text = ""
        self._charset_templates = self._load_charset()

        # roi -> [(name, resized_template, canonical_template, section_index), ...],
        # grouped so each distinct screen region is cropped/converted only
        # once a frame. canonical_template is None when the template's
        # shades aren't well-separated enough to trust rank canonicalization
        # for (see canonicalize_shades) - matching then falls back to the
        # raw template alone for that entry.
        self._roi_groups: list[tuple[tuple[int, int, int, int], list[tuple[str, "cv2.Mat", "cv2.Mat | None", int]]]] = []
        self.update_rois(roi_templates)

    def update_rois(self, roi_templates) -> None:
        """Rebuild the ROI/template grouping in place"""
        group_by_roi = {}
        roi_groups = []
        for name, roi, template, section_index in roi_templates:
            canonical = canonicalize_shades(template)
            group = group_by_roi.get(roi)
            if group is None:
                group = []
                group_by_roi[roi] = group
                roi_groups.append((roi, group))
            group.append((name, template, canonical, section_index))
        self._roi_groups = roi_groups

    def update_game_area(self, area) -> None:
        """Move all prepared templates to a newly calibrated game area."""
        self._game_area = area

    def _active_section(self) -> int:
        if self._section_provider is None:
            raise RuntimeError("DetectionService requires a section provider")
        return self._section_provider()

    def set_section_provider(self, provider) -> None:
        self._section_provider = provider

    def _image_to_binary(self, image):
        value = 0
        for pixel in image.flat:
            value = (value << 1) | (int(pixel) & 1)
        return value

    def _load_charset(self):
        charset_templates = {}
        charset_img = load_gray(RESOURCES_DIR / "textbox" / CHARSET_FILE)
        h = charset_img.shape[0] // 8
        w = charset_img.shape[1] // 8
        for idx in range(0, w * h):
            if CHARSET[idx] != "_":
                tile_x = (idx % w) * 8
                tile_y = (idx // w) * 8
                character = charset_img[tile_y:tile_y+8, tile_x:tile_x+8]
                binary = self._image_to_binary(character)
                # cv2.imwrite("test.png", character)
                charset_templates[binary] = CHARSET[idx]
        return charset_templates

    def process_frame_textbox(self, frame):
        if self._game_area is None:
            return
        frame_h, frame_w = frame.shape[:2]
        game_x = self._game_area[0] * frame_w
        game_y = self._game_area[1] * frame_h
        game_w = self._game_area[2] * frame_w
        game_h = self._game_area[3] * frame_h
        textbox_x = game_x + game_w * ROI_TEXTBOX[0] / GAMEBOY_SIZE[0]
        textbox_y = game_y + game_h * ROI_TEXTBOX[1] / GAMEBOY_SIZE[1]
        textbox_w = game_w * ROI_TEXTBOX[2] / GAMEBOY_SIZE[0]
        textbox_h = game_h * ROI_TEXTBOX[3] / GAMEBOY_SIZE[1]

        textbox = frame[round(textbox_y):round(textbox_y + textbox_h), round(textbox_x):round(textbox_x + textbox_w)]
        # cv2.imwrite("textbox1.png", textbox)
        textbox = cv2.resize(textbox, (ROI_TEXTBOX[2], ROI_TEXTBOX[3]))
        # cv2.imwrite("textbox2.png", textbox)
        textbox = cv2.cvtColor(textbox, cv2.COLOR_BGR2GRAY)
        # cv2.imwrite("textbox3.png", textbox)
        _, textbox = cv2.threshold(textbox, 128, 255, cv2.THRESH_BINARY)
        # cv2.imwrite("textbox4.png", textbox)
        log = ""

        TEXTBOX_THRESHOLD = 20
        score = cv2.countNonZero(cv2.absdiff(textbox[0:8, 0:160], self._textbox_top)) + cv2.countNonZero(cv2.absdiff(textbox[40:48, 0:160], self._textbox_bottom))
        if score >= 160 * 16 - TEXTBOX_THRESHOLD: # inverted palette
            textbox = 255 - textbox
            score = 160 * 16 - score
        if score > TEXTBOX_THRESHOLD:
            return
        if self.debug and score > 0:
            log += f" textbox_score={score}"

        def find_character(char):
            binary = self._image_to_binary(char)
            best = self._charset_templates.get(binary)
            if best:
                return best, 0
            best_score = 64
            for template, str in self._charset_templates.items():
                score = (binary ^ template).bit_count()
                if score < best_score:
                    best, best_score = str, score
            return best, best_score

        line1, line2 = "", ""
        for c in range(8, 152, 8):
            best, score = find_character(textbox[16:24, c:c+8])
            line1 += best
            if self.debug and score != 0: log += f" [1,{c}]\"{best}\"={score}"
        for c in range(8, 152, 8):
            best, score = find_character(textbox[32:40, c:c+8])
            line2 += best
            if self.debug and score != 0: log += f" [2,{c}]\"{best}\"={score}"
        text = (line1.rstrip() + " " + line2).rstrip()
        if text != "" and text != self._text:
            print(f'"{text}"{log}')
            self._text = text

            if text.endswith(" was caught!"):
                mon = text[:-12]
            elif text.startswith("give a nickname to ") and text[-1] == "?":
                mon = text[19:-1]
            elif " evolved into " in text and text[-1] == "!":
                mon = text.split(" evolved into ")[1][:-1]
            else:
                return

            if (mon in POKEMON_NAME_TO_DEX) and mon != self._last_detected:
                self._detected.add(mon)
                self.detection.emit(mon)
                self._last_detected = mon
                print(f"Detected {mon}")

    def process_frame_image(self, frame):
        if self._game_area is None:
            return

        frame_h, frame_w = frame.shape[:2]
        game_x = self._game_area[0] * frame_w
        game_y = self._game_area[1] * frame_h
        game_w = self._game_area[2] * frame_w
        game_h = self._game_area[3] * frame_h
        game = frame[round(game_y):round(game_y + game_h), round(game_x):round(game_x + game_w)]
        game = cv2.resize(game, GAMEBOY_SIZE)

        section = self._active_section()

        if self.debug:
            print(f"[section] active={section}")

        best_value = -1
        best_name = ""

        for roi, entries in self._roi_groups:
            active = [
                (name, template, canonical)
                for name, template, canonical, section_index in entries
                if section_index == section and name not in self._detected
                # if name not in self._detected
            ]
            if not active:
                continue

            x, y, w, h = roi
            x0 = max(0, x - ROI_SEARCH_MARGIN)
            y0 = max(0, y - ROI_SEARCH_MARGIN)
            x1 = min(GAMEBOY_SIZE[0], x + w + ROI_SEARCH_MARGIN)
            y1 = min(GAMEBOY_SIZE[1], y + h + ROI_SEARCH_MARGIN)
            crop = game[y0:y1, x0:x1]

            if crop.size == 0:
                continue

            crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            crop_canonical = canonicalize_shades(crop_gray)
            crop_canonical_inverted = 255 - crop_canonical if crop_canonical is not None else None

            for name, template, canonical in active:
                result = cv2.matchTemplate(crop_gray, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)

                if canonical is not None:
                    if crop_canonical is not None:
                        result_c = cv2.matchTemplate(crop_canonical, canonical, cv2.TM_CCOEFF_NORMED)
                        max_val = max(max_val, cv2.minMaxLoc(result_c)[1])
                    if crop_canonical_inverted is not None:
                        result_ci = cv2.matchTemplate(crop_canonical_inverted, canonical, cv2.TM_CCOEFF_NORMED)
                        max_val = max(max_val, cv2.minMaxLoc(result_ci)[1])

                if max_val > best_value:
                    # cv2.imwrite("_frame.png", frame)
                    # cv2.imwrite("_game.png", game)
                    # cv2.imwrite("crop_1gray.png", crop_gray)
                    # if crop_canonical is not None: cv2.imwrite("crop_2canonical.png", crop_canonical)
                    # cv2.imwrite("template_1gray.png", template)
                    # if canonical is not None: cv2.imwrite("template_2canonical.png", canonical)
                    best_value = max_val
                    best_name = name

        if self.debug and best_name:
            self.debug_scores.emit(best_name, best_value)

        if best_value > self.threshold and best_name not in self._detected:
            self._detected.add(best_name)
            self.detection.emit(best_name)
            print(f"Detected {best_name}: {best_value}")

    def select(self, name: str) -> None:
        self._detected.add(name)

    def forget(self, name: str) -> None:
        self._detected.discard(name)
        self._last_detected = None

    def reset(self) -> None:
        self._detected.clear()
        self._last_detected = None
