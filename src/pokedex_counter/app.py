from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QPoint, Qt, QSettings

from pokedex_counter.calibration_runner import run_calibration
from pokedex_counter.camera import resolve_camera_index
from pokedex_counter.config import APP_NAME, ORGANIZATION_NAME, SPRITES_BG_DIR
from pokedex_counter.controllers.game_controller import GameController
from pokedex_counter.main_window import MainWindow
from pokedex_counter.services.capture_service import CaptureService
from pokedex_counter.services.detection_service import DetectionService
from pokedex_counter.services.pb_service import save_pb
from pokedex_counter.services.template_service import TemplateService
from pokedex_counter.services.wr_service import load_wr_sections
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


def wire_found_pokemon(controller: GameController, sprite_strip) -> None:
    """Route found pokemon to the sprite strip, translating the section they
    were found in into the one thing the strip cares about: whether this was
    a catch or an evolution. Routing knowledge stays here rather than in the
    widget, which knows nothing about sections."""
    from pokedex_counter.roi_config import is_evolution

    def on_pokemon_found(name: str, section_index: int) -> None:
        sprite_strip.select_sprite(name, evolved=is_evolution(section_index, name))

    controller.pokemon_found.connect(on_pokemon_found)


def run() -> int:
    camera_index = resolve_camera_index()

    from pokedex_counter.roi_config import BONUSES, build_detection_entries

    app = QApplication([])

    # --- core ---
    controller = GameController()

    # --- vision ---
    templates = TemplateService(Path(SPRITES_BG_DIR)).templates
    roi_templates = build_detection_entries(templates)  # defaults; no boot-time calibration

    detector = DetectionService(roi_templates)

    capture = CaptureService(camera_index=camera_index)

    # --- UI ---
    window = MainWindow()
    settings = SettingsWindow()
    window.close_requested.connect(app.quit)
    window.set_calibrated(bool(roi_templates))

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
    window.move(prefs.value("window_position", QPoint(0, 0)))
    app.aboutToQuit.connect(lambda: prefs.setValue("window_position", window.pos()))
    settings.frameless_checkbox.setChecked(prefs.value("frameless", settings.frameless_checkbox.isChecked(), type=bool))
    settings.frameless_checkbox.toggled.connect(lambda checked: prefs.setValue("frameless", checked))
    settings.sprite_size_spinbox.setValue(int(prefs.value("sprite_size", settings.sprite_size_spinbox.value())))
    settings.sprite_size_spinbox.valueChanged.connect(lambda v: prefs.setValue("sprite_size", v))
    settings.sprite_padding_spinbox.setValue(int(prefs.value("sprite_padding", settings.sprite_padding_spinbox.value())))
    settings.sprite_padding_spinbox.valueChanged.connect(lambda v: prefs.setValue("sprite_padding", v))

    # --- WR (world record) comparison ---
    wr_sections = load_wr_sections()

    def apply_wr_section(section_index: int) -> None:
        if settings.compare_to_wr_checkbox.isChecked():
            window.sprite_strip.mark_wr_section(wr_sections.get(section_index, set()))

    def apply_wr_up_to_current() -> None:
        """Backfill every section's marks up to the active one - not just
        the current one - so re-enabling mid-run (or starting up already
        past section 0) still flags every WR pokemon missed so far, not
        only ones from here on."""
        for section_index in range(detector.current_section() + 1):
            apply_wr_section(section_index)

    def on_compare_to_wr_toggled(checked: bool) -> None:
        if checked:
            apply_wr_up_to_current()
        else:
            window.sprite_strip.clear_wr_marks()

    detector.section_changed.connect(apply_wr_section)
    settings.compare_to_wr_checkbox.toggled.connect(on_compare_to_wr_toggled)

    # --- bonus highlighting ---
    wire_bonus_highlight(settings, window.sprite_strip, BONUSES)

    # --- WIRING (VERY IMPORTANT) ---

    capture.frame_ready.connect(detector.process_frame, Qt.ConnectionType.DirectConnection)
    detector.detection.connect(controller.on_detection)
    detector.section_changed.connect(controller.on_section_changed)

    wire_found_pokemon(controller, window.sprite_strip)
    window.sprite_strip.sprite_deselected.connect(controller.forget)
    window.sprite_strip.sprite_deselected.connect(detector.forget)
    window.sprite_strip.count_changed.connect(window._update_counter)

    settings.columns_spinbox.valueChanged.connect(window.set_sprites_per_row)
    settings.font_size_spinbox.valueChanged.connect(window.set_counter_font_size)
    settings.sprite_size_spinbox.valueChanged.connect(window.set_sprite_size)
    settings.sprite_padding_spinbox.valueChanged.connect(window.set_sprite_padding)

    window.set_frameless_flag(settings.frameless_checkbox.isChecked())
    settings.frameless_checkbox.toggled.connect(window.on_frameless_toggled)

    def maybe_prompt_save_pb() -> None:
        """If the current run has the full 151, ask whether to save it as
        PB.json before its progress is lost (reset or app close)."""
        if window.sprite_strip.caught_count() != 151:
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
        window.sprite_strip.reset()
        # reset() drops all WR marks and turns the feature off (see
        # clear_wr_marks). Re-apply the fresh run's marks now. When the run
        # wasn't empty, deselecting the caught trigger pokemon rolls the
        # section back to 0 and section_changed would re-mark anyway - but an
        # empty reset never fires that signal, so without this the blue marks
        # would silently disappear until the checkbox is toggled. (Internally
        # guarded by the checkbox, so a no-op when comparison is off.)
        apply_wr_up_to_current()

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
        capture = CaptureService(camera_index=camera_index)
        capture.frame_ready.connect(detector.process_frame, Qt.ConnectionType.DirectConnection)
        capture.start()

    settings.calibrate_button.clicked.connect(on_calibrate_clicked)

    # --- start ---
    window.set_sprites_per_row(settings.columns_spinbox.value())
    window.set_counter_font_size(settings.font_size_spinbox.value())
    window.set_sprite_size(settings.sprite_size_spinbox.value())
    window.set_sprite_padding(settings.sprite_padding_spinbox.value())
    if settings.compare_to_wr_checkbox.isChecked():
        apply_wr_up_to_current()
    capture.start()
    window.show()
    settings.move(window.x() + window.frameGeometry().width() + 10, window.y())
    settings.show()

    return app.exec()
