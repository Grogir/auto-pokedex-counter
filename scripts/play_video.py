import cv2
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from pokedex_counter.config import (
    CALIBRATION_DIR,
    CALIBRATION_FILENAMES,
    DETECTION_IMAGE_DIR,
)
from pokedex_counter.game_config import BONUSES
from pokedex_counter.game_controller import GameController
from pokedex_counter.services.capture_service import CaptureService
from pokedex_counter.services.detection_service import DetectionService
from pokedex_counter.services.pb_service import save_pb
from pokedex_counter.services.template_service import TemplateService
from pokedex_counter.ui.boxes_window import BoxesWindow
from pokedex_counter.ui.main_window import MainWindow
from pokedex_counter.vision.image_io import load_gray
from pokedex_counter.vision.template_matching import find_best_match

TEMPLATE_PATH = CALIBRATION_DIR / CALIBRATION_FILENAMES["GAME_AREA"]

# VIDEO_PATH = "E:\\_ananan_12726.mp4"
VIDEO_PATH = "E:\\_sid_130.mp4"
# VIDEO_PATH = "E:\\2026-09-10 20-10-18 12809.mp4"
CALIBRATION_TIME = 30.0
CALIBRATE_SKIP_FRAMES = 120


def main() -> int:
    capture = CaptureService(source = VIDEO_PATH)

    print("Calibrating...")
    template = load_gray(TEMPLATE_PATH)
    best_score, best_box = 0, None
    for current_frame in range(round(CALIBRATION_TIME * 60)):
        ret, frame = capture.cap.read()
        if not ret:
            raise RuntimeError(f"Could not read frame {current_frame} from {VIDEO_PATH}")
        if current_frame % CALIBRATE_SKIP_FRAMES == 0:
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            score, box = find_best_match(frame_gray, template)
            print(current_frame, score, box)
            if score > best_score:
                best_score, best_box = score, box
                if best_score > 0.95:
                    break
    print(f"Best match score: {best_score}, box: {best_box}")
    frame_h, frame_w = frame.shape[:2]
    game_area = (best_box[0] / frame_w, best_box[1] / frame_h, best_box[2] / frame_w, best_box[3] / frame_h)

    app = QApplication([])
    controller = GameController()
    detector = DetectionService([])
    detector.update_game_area(game_area)
    window = MainWindow()
    boxes_window = BoxesWindow()
    controller.count_changed.connect(window.update_counter)
    window.sprite_strip.set_bonus_names(BONUSES)
    from pokedex_counter.app import wire_found_pokemon
    wire_found_pokemon(controller, window.sprite_strip, boxes_window)
    window.show()
    boxes_window.move(window.x() + window.frameGeometry().width() + 10, window.y())
    boxes_window.show()

    detector.build_roi_groups(TemplateService(DETECTION_IMAGE_DIR).templates)
    capture.frame_ready.connect(detector.process_frame_textbox, Qt.ConnectionType.DirectConnection)
    detector.detected.connect(controller.on_caught)
    detector.set_section_provider(controller.current_section)
    capture.frame_skip = 3
    capture.start()
    app.aboutToQuit.connect(lambda: save_pb(controller.section_catches))

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
