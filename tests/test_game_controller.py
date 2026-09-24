from pokedex_counter.controllers.game_controller import GameController


def test_duplicate_catches_are_logged_and_counted_once():
    controller = GameController()
    findings = []
    controller.pokemon_found.connect(lambda *finding: findings.append(finding))

    controller.on_detection("CHARMANDER")
    controller.on_detection("CHARMANDER")

    assert controller.count == 1
    assert controller.found == {"CHARMANDER"}
    assert controller.section_catches == {0: ["CHARMANDER", "CHARMANDER"]}
    assert [finding[0] for finding in findings] == ["CHARMANDER", "CHARMANDER"]


def test_section_is_derived_from_found_triggers():
    controller = GameController()

    controller.on_detection("BULBASAUR")
    controller.on_detection("PIDGEY")

    assert controller.current_section() == 2
    assert [names for names in controller.section_catches.values()] == [["BULBASAUR"], ["PIDGEY"]]


def test_forgetting_a_pokemon_removes_all_duplicates():
    controller = GameController()
    controller.on_detection("BULBASAUR")
    controller.on_detection("BULBASAUR")

    controller.forget("BULBASAUR")

    assert controller.count == 0
    assert controller.found == set()
    assert controller.section_catches == {}


def test_reset_clears_the_run_state():
    controller = GameController()
    controller.on_detection("MR.MIME")
    controller.on_detection("BULBASAUR")

    controller.reset()

    assert controller.count == 0
    assert controller.found == set()
    assert controller.section_catches == {}
    assert controller.current_section() == 0
