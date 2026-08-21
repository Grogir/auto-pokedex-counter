def test_set_sprites_per_row_window_fits_the_last_column(main_window, qtbot):
    """Regression test: the fixed window width must include the outer
    QVBoxLayout's own margins (main_window.py's _build_ui), not just
    SpriteStrip's natural_width() - otherwise the last column gets clipped."""
    main_window.set_sprites_per_row(5)
    main_window.show()
    qtbot.waitExposed(main_window)

    layout = main_window.sprite_strip._layout
    last_item = layout.itemAt(4).geometry()

    assert last_item.x() + last_item.width() <= main_window.sprite_strip.width()


def test_closing_main_window_requests_application_quit(main_window, qtbot):
    close_requested = qtbot.waitSignal(main_window.close_requested, timeout=1000)

    main_window.close()

    assert close_requested.signal_triggered


def test_set_calibrated_false_shows_the_calibration_message(main_window):
    from pokedex_counter.main_window import CALIBRATION_NEEDED_MESSAGE

    main_window.set_calibrated(False)

    assert main_window.counter_label.text() == CALIBRATION_NEEDED_MESSAGE
    assert main_window.counter_label.wordWrap()


def test_update_counter_is_ignored_while_uncalibrated(main_window):
    from pokedex_counter.main_window import CALIBRATION_NEEDED_MESSAGE

    main_window.set_calibrated(False)
    main_window._update_counter(5)

    assert main_window.counter_label.text() == CALIBRATION_NEEDED_MESSAGE


def test_set_calibrated_true_restores_the_current_count(main_window):
    main_window.set_calibrated(False)
    main_window.sprite_strip._count = 3  # simulate catches made before calibrating

    main_window.set_calibrated(True)

    assert "3" in main_window.counter_label.text()
