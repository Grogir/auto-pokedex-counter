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


def test_bottom_margin_is_added_to_the_window_height(main_window):
    main_window.set_calibrated(True)
    main_window.set_bottom_margin(17)
    content_width = main_window.centralWidget().width()
    expected_height = (
        main_window.centralWidget().layout().totalHeightForWidth(content_width) + 17
    )

    main_window._sync_height_to_width()

    assert main_window.height() == expected_height


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
    from pokedex_counter.controllers.game_controller import GameController

    controller = GameController()
    controller.count_changed.connect(main_window._update_counter)
    main_window.set_count_provider(controller.current_count)
    main_window.set_calibrated(False)
    for name in ("BULBASAUR", "IVYSAUR", "VENUSAUR"):
        controller.on_detection(name)

    main_window.set_calibrated(True)

    assert "3" in main_window.counter_label.text()
