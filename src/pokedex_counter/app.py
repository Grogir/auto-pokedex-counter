from PySide6.QtCore import (
    QPoint,
    QSettings,
    Qt,
    QTime,
)
from PySide6.QtWidgets import QApplication, QMessageBox

from pokedex_counter.config import (
    APP_NAME,
    DETECTION_IMAGE_DIR,
    ORGANIZATION_NAME,
    SPRITES_DIRS,
)
from pokedex_counter.detection_config import DETECTION_TYPE
from pokedex_counter.game_config import BONUSES, ROUTE_SECTIONS
from pokedex_counter.game_controller import GameController
from pokedex_counter.services.calibration_runner import (
    run_calibration,
    save_calibration_results,
)
from pokedex_counter.services.calibration_service import CalibrationService
from pokedex_counter.services.camera_finder import resolve_camera_index
from pokedex_counter.services.capture_service import CaptureService
from pokedex_counter.services.comparison_service import load_comparisons
from pokedex_counter.services.detection_service import DetectionService
from pokedex_counter.services.global_hotkey import GlobalHotkey
from pokedex_counter.services.pb_service import save_pb
from pokedex_counter.services.template_service import TemplateService
from pokedex_counter.ui.afo_window import AfoWindow
from pokedex_counter.ui.boxes_window import BoxesWindow
from pokedex_counter.ui.main_window import MainWindow
from pokedex_counter.ui.settings_window import SettingsWindow
from pokedex_counter.ui.widgets.sprite_strip import SpriteStrip


def run() -> int:
    app = QApplication([])

    # --- core ---
    controller = GameController()

    # --- vision ---
    camera_index = resolve_camera_index()
    capture = CaptureService(source=camera_index)
    calibration = CalibrationService(capture)

    detector = DetectionService()
    detector.build_roi_groups(TemplateService(DETECTION_IMAGE_DIR).templates)
    detector.set_section_provider(controller.current_section)

    # --- UI ---
    window = MainWindow()
    boxes_window = BoxesWindow()
    afo_window = AfoWindow(controller.current_section)
    settings = SettingsWindow()
    controller.count_changed.connect(window.update_counter)
    window.set_count_provider(controller.current_count)
    window.close_requested.connect(app.quit)
    wire_ui_settings(settings, window, boxes_window, afo_window)
    apply_section, refresh_comparisons = wire_comparison(controller, settings, window.sprite_strip)

    # --- persisted settings ---
    prefs = QSettings(ORGANIZATION_NAME, APP_NAME)
    wire_preferences(settings, window, boxes_window, afo_window, prefs, app)

    # --- event wiring ---
    apply_detection_type = wire_detection(
        controller, detector, capture, calibration, window, boxes_window, settings, afo_window
    )
    app.aboutToQuit.connect(capture.shutdown)
    app.aboutToQuit.connect(
        lambda: maybe_prompt_save_pb(controller, window, refresh_comparisons)
    )
    settings.reset_button.clicked.connect(
        lambda: reset_run(controller, detector, window, boxes_window, apply_section, refresh_comparisons, afo_window)
    )

    # --- calibration ---
    wire_calibration(capture, calibration, detector, settings, apply_detection_type)

    # --- keybinds ---
    global_backspace = GlobalHotkey(0x08, controller.force_detect_current_section)
    app.aboutToQuit.connect(global_backspace.close)

    # --- start ---
    window.show()
    boxes_window.show()
    afo_window.show()
    settings.move(window.x() + window.frameGeometry().width() + 10, window.y())
    settings.show()

    return app.exec()


def wire_preferences(settings: SettingsWindow,
                     window: MainWindow,
                     boxes_window: BoxesWindow,
                     afo_window: AfoWindow,
                     prefs: QSettings,
                     app: QApplication) -> None:
    for key, spinbox in (
        ("sprites_per_row", settings.columns_spinbox),
        ("counter_font_size", settings.font_size_spinbox),
        ("sprite_width", settings.sprite_width_spinbox),
        ("sprite_height", settings.sprite_height_spinbox),
        ("sprite_padding", settings.sprite_padding_spinbox),
        ("bottom_margin", settings.bottom_margin_spinbox),
        ("box_sprite_width", settings.box_sprite_width_spinbox),
        ("box_sprite_height", settings.box_sprite_height_spinbox),
    ):
        spinbox.setValue(int(prefs.value(key, spinbox.value())))
        spinbox.valueChanged.connect(
            lambda value, setting_key=key: prefs.setValue(setting_key, value)
        )

    for key, checkbox in (
        ("highlight_bonuses", settings.highlight_bonuses_checkbox),
        ("frameless", settings.frameless_checkbox),
    ):
        checkbox.setChecked(prefs.value(key, checkbox.isChecked(), type=bool))
        checkbox.toggled.connect(
            lambda checked, setting_key=key: prefs.setValue(setting_key, checked)
        )

    comparison_seconds = max(
        0, min(int(prefs.value("afo_comparison_seconds", 0)), 59 * 60 + 59)
    )
    settings.afo_comparison_time_edit.setTime(
        QTime(0, comparison_seconds // 60, comparison_seconds % 60)
    )
    settings.afo_comparison_time_edit.timeChanged.connect(
        lambda time: prefs.setValue(
            "afo_comparison_seconds", time.minute() * 60 + time.second()
        )
    )

    multiplier = float(prefs.value("afo_multiplier", 0.0))
    settings.afo_multiplier_spinbox.setValue(multiplier)
    settings.afo_multiplier_spinbox.valueChanged.connect(
        lambda value: prefs.setValue("afo_multiplier", value)
    )

    comparison = prefs.value("comparison", settings.comparison_combo.currentData())
    comparison_index = settings.comparison_combo.findData(comparison)
    if comparison_index >= 0:
        settings.comparison_combo.setCurrentIndex(comparison_index)
    settings.comparison_combo.currentIndexChanged.connect(
        lambda _: prefs.setValue("comparison", settings.comparison_combo.currentData())
    )

    detection_type = prefs.value(
        "detection_type", settings.detection_type_combo.currentData(), type=int
    )
    settings.detection_type_combo.setCurrentIndex(detection_type)
    settings.detection_type_combo.currentIndexChanged.connect(
        lambda type: prefs.setValue("detection_type", type)
    )

    sprite_set = prefs.value(
        "sprite_set", settings.sprite_set_combo.currentData(), type=int
    )
    sprite_set_index = settings.sprite_set_combo.findData(sprite_set)
    if sprite_set_index >= 0:
        settings.sprite_set_combo.setCurrentIndex(sprite_set_index)
    settings.sprite_set_combo.currentIndexChanged.connect(
        lambda _: prefs.setValue("sprite_set", settings.sprite_set_combo.currentData())
    )

    window.move(prefs.value("window_position", QPoint(10, 10)))
    app.aboutToQuit.connect(lambda: prefs.setValue("window_position", window.pos()))
    boxes_window.move(prefs.value("boxes_window_position", QPoint(10, 530)))
    app.aboutToQuit.connect(lambda: prefs.setValue("boxes_window_position", boxes_window.pos()))
    afo_window.move(prefs.value("afo_window_position", QPoint(220, 530)))
    app.aboutToQuit.connect(lambda: prefs.setValue("afo_window_position", afo_window.pos()))


def wire_comparison(controller: GameController,
                    settings: SettingsWindow,
                    sprite_strip: SpriteStrip):
    comparisons = {}

    def apply_section(section_index: int) -> None:
        if section_index < len(ROUTE_SECTIONS):
            route_section = ROUTE_SECTIONS[section_index]
            sprite_strip.set_current_section(set(route_section.required), set(route_section.bonuses))
            comparison_index = section_index
        else:
            sprite_strip.set_current_section(set(), set())
            comparison_index = len(ROUTE_SECTIONS) - 1

        comparison = comparisons.get(settings.comparison_combo.currentData())
        names = comparison.cumulative_bonuses.get(comparison_index, set()) if comparison else set()
        sprite_strip.set_comparison_names(names)

    def reapply_section() -> None:
        apply_section(controller.current_section())

    def refresh_comparisons() -> None:
        selected = settings.comparison_combo.currentData()
        comparisons.clear()
        comparisons.update({comparison.key: comparison for comparison in load_comparisons()})

        combo = settings.comparison_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("None", None)
        for comparison in comparisons.values():
            combo.addItem(comparison.name, comparison.key)
        selected_index = combo.findData(selected)
        combo.setCurrentIndex(max(selected_index, 0))
        combo.blockSignals(False)
        reapply_section()

    refresh_comparisons()
    controller.section_changed.connect(apply_section)
    settings.comparison_combo.currentIndexChanged.connect(reapply_section)
    apply_section(0)
    return apply_section, refresh_comparisons


def wire_detection(controller: GameController,
                   detector: DetectionService,
                   capture: CaptureService,
                   calibration: CalibrationService,
                   window: MainWindow,
                   boxes_window: BoxesWindow,
                   settings: SettingsWindow,
                   afo_window: AfoWindow):
    capture.frame_ready.connect(detector.process_frame, Qt.ConnectionType.DirectConnection)

    sprite_strip = window.sprite_strip
    detector.detected.connect(controller.on_caught)
    controller.pokemon_found.connect(sprite_strip.on_pokemon_found)
    controller.pokemon_found.connect(boxes_window.on_pokemon_found)
    controller.pokemon_found.connect(afo_window.on_pokemon_found)

    sprite_strip.manual_caught.connect(controller.on_caught)
    sprite_strip.manual_caught.connect(detector.on_manual_caught)
    boxes_window.manual_caught.connect(controller.on_caught)
    boxes_window.manual_caught.connect(detector.on_manual_caught)
    sprite_strip.manual_uncaught.connect(controller.on_manual_uncaught)
    sprite_strip.manual_uncaught.connect(detector.on_manual_uncaught)
    sprite_strip.manual_uncaught.connect(boxes_window.on_manual_uncaught)
    sprite_strip.manual_uncaught.connect(afo_window.on_manual_uncaught)

    sprite_strip.manual_ignored.connect(controller.on_ignored)
    sprite_strip.manual_ignored.connect(detector.on_manual_uncaught)
    sprite_strip.manual_ignored.connect(boxes_window.on_manual_uncaught)
    sprite_strip.manual_unignored.connect(controller.on_unignored)

    controller.register_command("box", boxes_window.change_box)
    controller.register_command("deposit", boxes_window.deposit)
    controller.register_command("swap", boxes_window.swap)

    def apply_detection_type() -> None:
        type = settings.detection_type_combo.currentData()
        detector.set_detection_type(type)
        window.set_calibrated(type == DETECTION_TYPE["NONE"] or detector.is_calibrated)
        if not calibration.active:
            if type == DETECTION_TYPE["NONE"]:
                if capture.running:
                    capture.stop()
            elif not capture.running:
                capture.start()
    settings.detection_type_combo.currentIndexChanged.connect(apply_detection_type)
    apply_detection_type()
    return apply_detection_type


def wire_ui_settings(settings: SettingsWindow,
                     window: MainWindow,
                     boxes_window: BoxesWindow,
                     afo_window: AfoWindow) -> None:
    def apply_sprite_set(sprite_set: int) -> None:
        sprites_dir = SPRITES_DIRS[sprite_set - 1]
        window.sprite_strip.set_folder(sprites_dir)
        boxes_window.set_sprites_dir(sprites_dir)

    settings.sprite_set_combo.currentIndexChanged.connect(
        lambda _: apply_sprite_set(settings.sprite_set_combo.currentData())
    )
    apply_sprite_set(settings.sprite_set_combo.currentData())

    settings.columns_spinbox.valueChanged.connect(window.set_sprites_per_row)
    window.set_sprites_per_row(settings.columns_spinbox.value())

    settings.font_size_spinbox.valueChanged.connect(window.set_counter_font_size)
    window.set_counter_font_size(settings.font_size_spinbox.value())

    settings.bottom_margin_spinbox.valueChanged.connect(window.set_bottom_margin)
    window.set_bottom_margin(settings.bottom_margin_spinbox.value())

    settings.sprite_width_spinbox.valueChanged.connect(
        lambda width: window.set_sprite_dimensions(width, settings.sprite_height_spinbox.value())
    )
    settings.sprite_height_spinbox.valueChanged.connect(
        lambda height: window.set_sprite_dimensions(settings.sprite_width_spinbox.value(), height)
    )
    window.set_sprite_dimensions(
        settings.sprite_width_spinbox.value(),
        settings.sprite_height_spinbox.value(),
    )

    settings.box_sprite_width_spinbox.valueChanged.connect(
        lambda width: boxes_window.set_sprite_dimensions(width, settings.box_sprite_height_spinbox.value())
    )
    settings.box_sprite_height_spinbox.valueChanged.connect(
        lambda height: boxes_window.set_sprite_dimensions(settings.box_sprite_width_spinbox.value(), height)
    )
    boxes_window.set_sprite_dimensions(
        settings.box_sprite_width_spinbox.value(),
        settings.box_sprite_height_spinbox.value(),
    )

    settings.sprite_padding_spinbox.valueChanged.connect(window.set_sprite_padding)
    window.set_sprite_padding(settings.sprite_padding_spinbox.value())

    settings.sprite_padding_spinbox.valueChanged.connect(boxes_window.set_sprite_padding)
    boxes_window.set_sprite_padding(settings.sprite_padding_spinbox.value())

    settings.frameless_checkbox.toggled.connect(window.on_frameless_toggled)
    window.set_frameless_flag(settings.frameless_checkbox.isChecked())

    def apply_bonuses(checked: bool) -> None:
        window.sprite_strip.set_bonus_names(BONUSES if checked else set())
    settings.highlight_bonuses_checkbox.toggled.connect(apply_bonuses)
    apply_bonuses(settings.highlight_bonuses_checkbox.isChecked())

    settings.afo_comparison_time_edit.timeChanged.connect(
        lambda time: afo_window.set_afo_comparison(
            time.minute() * 60 + time.second()
        )
    )
    settings.afo_multiplier_spinbox.valueChanged.connect(
        afo_window.set_afo_multiplier
    )
    comparison_time = settings.afo_comparison_time_edit.time()
    afo_window.set_afo_comparison(
        comparison_time.minute() * 60 + comparison_time.second()
    )
    afo_window.set_afo_multiplier(settings.afo_multiplier_spinbox.value())


def wire_calibration(capture: CaptureService,
                     calibration: CalibrationService,
                     detector: DetectionService,
                     settings: SettingsWindow,
                     apply_detection_type: callable):
    """Wire up the calibration process to the UI and detection service."""
    def on_calibrate_clicked() -> None:
        if not calibration.active:
            capture.frame_ready.disconnect(detector.process_frame)
            if not capture.running:
                capture.start()
            run_calibration(calibration)

    def on_calibration_finished(results) -> None:
        save_calibration_results(results)
        if results.get("GAME_AREA") is not None:
            detector.update_game_area(results["GAME_AREA"])
        apply_detection_type()
        capture.frame_ready.connect(detector.process_frame, Qt.ConnectionType.DirectConnection)

    settings.calibrate_button.clicked.connect(on_calibrate_clicked)
    calibration.finished.connect(on_calibration_finished, Qt.ConnectionType.QueuedConnection)


def reset_run(controller: GameController,
              detector: DetectionService,
              window: MainWindow,
              boxes_window: BoxesWindow,
              apply_section,
              refresh_comparisons,
              afo_window: AfoWindow):
    maybe_prompt_save_pb(controller, window, refresh_comparisons)
    controller.reset()
    detector.reset()
    window.sprite_strip.reset()
    boxes_window.reset()
    afo_window.reset()
    apply_section(0)


def maybe_prompt_save_pb(controller, window, refresh_comparisons) -> None:
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
        refresh_comparisons()
