from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import (
    QPoint,
    Qt,
    QSettings,
)

from pokedex_counter.calibration_runner import run_calibration
from pokedex_counter.camera import resolve_camera_index
from pokedex_counter.config import APP_NAME, ORGANIZATION_NAME, SPRITES_BG_DIR
from pokedex_counter.controllers.game_controller import GameController
from pokedex_counter.boxes_window import BoxesWindow
from pokedex_counter.main_window import MainWindow
from pokedex_counter.services.capture_service import CaptureService
from pokedex_counter.services.detection_service import DetectionService
from pokedex_counter.services.pb_service import save_pb
from pokedex_counter.services.template_service import TemplateService
from pokedex_counter.services.wr_service import load_wr_sections
from pokedex_counter.services.global_keybind import GlobalKeybind
from pokedex_counter.game_config import ROUTE_SECTIONS, BONUSES
from pokedex_counter.settings_window import SettingsWindow

def wire_bonus_highlight(settings: SettingsWindow, sprite_strip, bonuses: set[str]) -> None:
    """Point the "Highlight bonuses" checkbox at the sprite strip, and apply
    whatever state the checkbox was restored in.

    Unlike the WR marks there's nothing to re-apply per section or after a
    reset: `bonuses` is a static list, so the strip only ever needs to know
    whether the setting is on. Lives out here (rather than inline in run()
    like the WR wiring) purely so it can be tested without standing up a
    camera and the whole app."""
    def apply(checked: bool) -> None:
        sprite_strip.set_bonus_names(bonuses if checked else set())

    settings.highlight_bonuses_checkbox.toggled.connect(apply)
    apply(settings.highlight_bonuses_checkbox.isChecked())


def wire_found_pokemon(controller: GameController, sprite_strip, boxes_window) -> None:
    """Project controller findings into the UI views."""
    def on_pokemon_found(name: str, section_index: int, evolved: bool) -> None:
        sprite_strip.select_sprite(name, evolved=evolved)
        boxes_window.pokemon_found(name, evolved=evolved)

    controller.pokemon_found.connect(on_pokemon_found)
    sprite_strip.sprite_deselected.connect(boxes_window.remove_pokemon)
    def on_ignore_toggled(name: str, ignored: bool) -> None:
        if ignored:
            boxes_window.remove_pokemon(name)

    sprite_strip.sprite_ignored.connect(on_ignore_toggled)


def run() -> int:
    # frame = cv2.imread("test1.png")
    # frame = cv2.resize(frame, (256, 144), interpolation=cv2.INTER_NEAREST_EXACT)
    # cv2.imwrite("test2.png", frame)
    # return

    camera_index = resolve_camera_index()

    from pokedex_counter.roi_config import build_detection_entries, is_calibrated

    app = QApplication([])

    # --- core ---
    controller = GameController()

    # --- vision ---
    templates = TemplateService(Path(SPRITES_BG_DIR)).templates
    roi_templates = build_detection_entries(templates)  # defaults; no boot-time calibration

    detector = DetectionService(roi_templates)
    detector.set_section_provider(controller.current_section)

    capture = CaptureService(source=camera_index)

    # --- UI ---
    window = MainWindow()
    boxes_window = BoxesWindow()
    settings = SettingsWindow()
    controller.count_changed.connect(window._update_counter)
    window.set_count_provider(controller.current_count)
    window.close_requested.connect(app.quit)
    # window.set_calibrated(bool(roi_templates))
    window.set_calibrated(is_calibrated())

    # --- persisted settings ---
    prefs = QSettings(ORGANIZATION_NAME, APP_NAME)
    settings.columns_spinbox.setValue(int(prefs.value("sprites_per_row", settings.columns_spinbox.value())))
    settings.columns_spinbox.valueChanged.connect(lambda v: prefs.setValue("sprites_per_row", v))
    settings.font_size_spinbox.setValue(int(prefs.value("counter_font_size", settings.font_size_spinbox.value())))
    settings.font_size_spinbox.valueChanged.connect(lambda v: prefs.setValue("counter_font_size", v))
    settings.compare_to_wr_checkbox.setChecked(prefs.value("compare_to_wr", settings.compare_to_wr_checkbox.isChecked(), type=bool))
    settings.compare_to_wr_checkbox.toggled.connect(lambda checked: prefs.setValue("compare_to_wr", checked))
    settings.highlight_bonuses_checkbox.setChecked(prefs.value("highlight_bonuses", settings.highlight_bonuses_checkbox.isChecked(), type=bool))
    settings.highlight_bonuses_checkbox.toggled.connect(lambda checked: prefs.setValue("highlight_bonuses", checked))
    window.move(prefs.value("window_position", QPoint(10, 10)))
    app.aboutToQuit.connect(lambda: prefs.setValue("window_position", window.pos()))
    boxes_window.move(prefs.value("boxes_window_position", QPoint(10, 530)))
    app.aboutToQuit.connect(lambda: prefs.setValue("boxes_window_position", boxes_window.pos()))
    settings.frameless_checkbox.setChecked(prefs.value("frameless", settings.frameless_checkbox.isChecked(), type=bool))
    settings.frameless_checkbox.toggled.connect(lambda checked: prefs.setValue("frameless", checked))
    settings.sprite_width_spinbox.setValue(int(prefs.value("sprite_width", settings.sprite_width_spinbox.value())))
    settings.sprite_width_spinbox.valueChanged.connect(lambda v: prefs.setValue("sprite_width", v))
    settings.sprite_height_spinbox.setValue(int(prefs.value("sprite_height", settings.sprite_height_spinbox.value())))
    settings.sprite_height_spinbox.valueChanged.connect(lambda v: prefs.setValue("sprite_height", v))
    settings.sprite_padding_spinbox.setValue(int(prefs.value("sprite_padding", settings.sprite_padding_spinbox.value())))
    settings.sprite_padding_spinbox.valueChanged.connect(lambda v: prefs.setValue("sprite_padding", v))
    settings.box_sprite_width_spinbox.setValue(int(prefs.value("box_sprite_width", settings.box_sprite_width_spinbox.value())))
    settings.box_sprite_width_spinbox.valueChanged.connect(lambda v: prefs.setValue("box_sprite_width", v))
    settings.box_sprite_height_spinbox.setValue(int(prefs.value("box_sprite_height", settings.box_sprite_height_spinbox.value())))
    settings.box_sprite_height_spinbox.valueChanged.connect(lambda v: prefs.setValue("box_sprite_height", v))

    # --- WR (world record) comparison ---
    wr_sections = load_wr_sections()

    def wr_names_up_to(section_index: int) -> set[str]:
        return set().union(
            *(wr_sections.get(index, set()) for index in range(section_index + 1))
        )

    def apply_section(section_index: int) -> None:
        sections = ROUTE_SECTIONS
        if section_index >= len(sections):
            window.sprite_strip.set_current_section(set(), set())
            if settings.compare_to_wr_checkbox.isChecked():
                window.sprite_strip.set_wr_names(
                    wr_names_up_to(len(sections) - 1)
                )
            return
        route_section = sections[section_index]
        window.sprite_strip.set_current_section(
            set(route_section.required),
            set(route_section.bonuses),
        )
        if settings.compare_to_wr_checkbox.isChecked():
            window.sprite_strip.set_wr_names(wr_names_up_to(section_index))

    def apply_section_up_to_current() -> None:
        """Backfill every section's marks up to the active one - not just
        the current one - so re-enabling mid-run (or starting up already
        past section 0) still flags every WR pokemon missed so far, not
        only ones from here on."""
        for section_index in range(controller.current_section() + 1):
            apply_section(section_index)

    def on_compare_to_wr_toggled(checked: bool) -> None:
        if checked:
            apply_section_up_to_current()
        else:
            window.sprite_strip.clear_wr_marks()

    controller.section_changed.connect(apply_section)
    settings.compare_to_wr_checkbox.toggled.connect(on_compare_to_wr_toggled)

    # --- bonus highlighting ---
    wire_bonus_highlight(settings, window.sprite_strip, BONUSES)

    # --- WIRING (VERY IMPORTANT) ---

    capture.frame_ready.connect(detector.process_frame_textbox, Qt.ConnectionType.DirectConnection)
    detector.detection.connect(controller.on_detection)
    wire_found_pokemon(controller, window.sprite_strip, boxes_window)
    window.sprite_strip.sprite_selected.connect(controller.on_detection)
    window.sprite_strip.sprite_selected.connect(detector.select)
    window.sprite_strip.sprite_deselected.connect(controller.forget)
    window.sprite_strip.sprite_deselected.connect(detector.forget)
    def on_ignore_toggled(name: str, ignored: bool) -> None:
        if ignored:
            controller.ignore(name)
            detector.forget(name)
        else:
            controller.unignore(name)

    window.sprite_strip.sprite_ignored.connect(on_ignore_toggled)
    global_backspace = GlobalKeybind(0x08, controller.force_detect_current_section)
    app.installNativeEventFilter(global_backspace)
    app.aboutToQuit.connect(global_backspace.close)
    settings.columns_spinbox.valueChanged.connect(window.set_sprites_per_row)
    settings.font_size_spinbox.valueChanged.connect(window.set_counter_font_size)
    settings.sprite_width_spinbox.valueChanged.connect(
        lambda width: window.set_sprite_dimensions(width, settings.sprite_height_spinbox.value())
    )
    settings.sprite_height_spinbox.valueChanged.connect(
        lambda height: window.set_sprite_dimensions(settings.sprite_width_spinbox.value(), height)
    )
    settings.sprite_padding_spinbox.valueChanged.connect(window.set_sprite_padding)

    window.set_frameless_flag(settings.frameless_checkbox.isChecked())
    settings.frameless_checkbox.toggled.connect(window.on_frameless_toggled)

    def maybe_prompt_save_pb() -> None:
        """If the current run has the full 151, ask whether to save it as
        PB.json before its progress is lost (reset or app close)."""
        if controller.count != 151:
            return

        reply = QMessageBox.question(
            window,
            "Save Personal Best?",
            "You've caught all 151 Pokémon! Save this run as your PB?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            save_pb(controller.section_catches)

    def on_reset_clicked() -> None:
        maybe_prompt_save_pb()
        controller.reset()
        detector.reset()
        window.sprite_strip.reset()
        boxes_window.reset()
        # reset() drops all WR marks and turns the feature off; re-apply the
        # fresh run's marks now, including when the run was already empty.
        apply_section_up_to_current()

    settings.reset_button.clicked.connect(on_reset_clicked)
    app.aboutToQuit.connect(maybe_prompt_save_pb)

    def on_calibrate_clicked() -> None:
        nonlocal capture
        capture.stop()
        locked = run_calibration(camera_index=camera_index)
        if locked:
            new_roi_templates = build_detection_entries(templates, locked)
            detector.update_rois(new_roi_templates)
            window.set_calibrated(bool(new_roi_templates))
        capture = CaptureService(source=camera_index)
        capture.frame_ready.connect(detector.process_frame_textbox, Qt.ConnectionType.DirectConnection)
        capture.start()

    settings.calibrate_button.clicked.connect(on_calibrate_clicked)

    # --- start ---
    window.set_sprites_per_row(settings.columns_spinbox.value())
    window.set_counter_font_size(settings.font_size_spinbox.value())
    window.set_sprite_dimensions(
        settings.sprite_width_spinbox.value(),
        settings.sprite_height_spinbox.value(),
    )
    window.set_sprite_padding(settings.sprite_padding_spinbox.value())
    boxes_window.set_sprite_dimensions(
        settings.box_sprite_width_spinbox.value(),
        settings.box_sprite_height_spinbox.value(),
    )
    boxes_window.set_sprite_padding(settings.sprite_padding_spinbox.value())
    settings.box_sprite_width_spinbox.valueChanged.connect(
        lambda width: boxes_window.set_sprite_dimensions(width, settings.box_sprite_height_spinbox.value())
    )
    settings.box_sprite_height_spinbox.valueChanged.connect(
        lambda height: boxes_window.set_sprite_dimensions(settings.box_sprite_width_spinbox.value(), height)
    )
    settings.sprite_padding_spinbox.valueChanged.connect(boxes_window.set_sprite_padding)
    apply_section(0)
    if settings.compare_to_wr_checkbox.isChecked():
        apply_section_up_to_current()
    capture.start()
    window.show()
    boxes_window.show()
    settings.move(window.x() + window.frameGeometry().width() + 10, window.y())
    settings.show()

    return app.exec()
