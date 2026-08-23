# vision/detector.py
import cv2
from PySide6.QtCore import QObject, Signal

from pokedex_counter.config import FRAME_SIZE, ROI_SEARCH_MARGIN, THRESHOLD
from pokedex_counter.roi_config import SECTION_TRIGGERS
from pokedex_counter.vision.template_matching import canonicalize_shades


class DetectionService(QObject):
    detection = Signal(str)
    debug_scores = Signal(str, float)
    section_changed = Signal(int)

    def __init__(self, roi_templates, threshold=THRESHOLD, debug=False):
        super().__init__()
        self.threshold = threshold
        self.debug = debug
        self._detected: set[str] = set()
        self._section_triggers = SECTION_TRIGGERS
        self._last_section = 0

        # roi -> [(name, resized_template, canonical_template, section_index), ...],
        # grouped so each distinct screen region is cropped/converted only
        # once a frame. canonical_template is None when the template's
        # shades aren't well-separated enough to trust rank canonicalization
        # for (see canonicalize_shades) - matching then falls back to the
        # raw template alone for that entry.
        self._roi_groups: list[tuple[tuple[int, int, int, int], list[tuple[str, "cv2.Mat", "cv2.Mat | None", int]]]] = []
        self.update_rois(roi_templates)

    def update_rois(self, roi_templates) -> None:
        """Rebuild the ROI/template grouping in place (e.g. after
        recalibration). Deliberately leaves `_detected` untouched - progress
        made so far in the current run must survive a recalibration."""
        group_by_roi = {}
        roi_groups = []
        for name, roi, template, section_index in roi_templates:
            resized = cv2.resize(template, (roi[2], roi[3]))
            canonical = canonicalize_shades(resized)
            group = group_by_roi.get(roi)
            if group is None:
                group = []
                group_by_roi[roi] = group
                roi_groups.append((roi, group))
            group.append((name, resized, canonical, section_index))
        self._roi_groups = roi_groups

    def _section_cleared(self, section: int) -> bool:
        """Whether every Pokemon section `section` requires has been caught.
        An empty list would make this vacuously true, so it's rejected -
        only the final section is allowed one, and _active_section never
        asks about that one (see SECTION_TRIGGERS)."""
        required = self._section_triggers[section]
        return bool(required) and all(name in self._detected for name in required)

    def _active_section(self) -> int:
        """The currently active section, derived live from `_detected` (not
        tracked incrementally) so undoing any one of a section's required
        detections via forget() automatically rolls the active section back
        too - no separate mutable pointer to keep in sync.

        A section is only left behind once ALL of its required Pokemon are
        caught, in whatever order they come. Advancing on a single one let a
        player who caught it early strand the rest of the section: nothing
        outside the active section is ever matched, so those became
        uncatchable for the remainder of the run."""
        last = len(self._section_triggers) - 1
        section = 0
        while section < last and self._section_cleared(section):
            section += 1
        return section

    def current_section(self) -> int:
        """Public accessor for the currently active section (see
        _active_section)."""
        return self._active_section()

    def process_frame(self, frame):
        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, FRAME_SIZE)

        section = self._active_section()

        if section != self._last_section:
            self._last_section = section
            self.section_changed.emit(section)

        if self.debug:
            print(f"[section] active={section}")

        best_value = -1
        best_name = ""

        for roi, entries in self._roi_groups:
            active = [
                (name, template, canonical)
                for name, template, canonical, section_index in entries
                if section_index == section and name not in self._detected
            ]
            if not active:
                continue

            x, y, w, h = roi
            frame_h, frame_w = frame.shape[:2]
            x0 = max(0, x - ROI_SEARCH_MARGIN)
            y0 = max(0, y - ROI_SEARCH_MARGIN)
            x1 = min(frame_w, x + w + ROI_SEARCH_MARGIN)
            y1 = min(frame_h, y + h + ROI_SEARCH_MARGIN)
            crop = frame[y0:y1, x0:x1]

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
                    best_value = max_val
                    best_name = name

        if self.debug and best_name:
            self.debug_scores.emit(best_name, best_value)

        if best_value > self.threshold and best_name not in self._detected:
            self._detected.add(best_name)
            self.detection.emit(best_name)
            print(f"Detected {best_name}: {best_value}")

    def forget(self, name: str) -> None:
        self._detected.discard(name)
