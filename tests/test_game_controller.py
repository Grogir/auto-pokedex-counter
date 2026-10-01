import pokedex_counter.game_controller as game_controller_module
from pokedex_counter.game_controller import GameController
from pokedex_counter.services.route_service import (
    RouteCommand,
    RouteSection,
    load_route_sections,
)


def test_duplicate_catches_are_logged_and_counted_once():
    controller = GameController()
    findings = []
    controller.pokemon_found.connect(lambda *finding: findings.append(finding))

    controller.on_caught("CHARMANDER")
    controller.on_caught("CHARMANDER")

    assert controller.count == 1
    assert controller.found == {"CHARMANDER"}
    assert controller.section_catches == {0: ["CHARMANDER", "CHARMANDER"]}
    assert [finding[0] for finding in findings] == ["CHARMANDER", "CHARMANDER"]


def test_section_is_derived_from_found_triggers():
    controller = GameController()

    controller.on_caught("BULBASAUR")
    controller.on_caught("PIDGEY")

    assert controller.current_section() == 2
    assert [names for names in controller.section_catches.values()] == [["BULBASAUR"], ["PIDGEY"]]


def test_forgetting_a_pokemon_removes_all_duplicates():
    controller = GameController()
    controller.on_caught("BULBASAUR")
    controller.on_caught("BULBASAUR")

    controller.on_manual_uncaught("BULBASAUR")

    assert controller.count == 0
    assert controller.found == set()
    assert controller.section_catches == {}


def test_reset_clears_the_run_state():
    controller = GameController()
    controller.on_caught("MR.MIME")
    controller.on_caught("BULBASAUR")

    controller.reset()

    assert controller.count == 0
    assert controller.found == set()
    assert controller.section_catches == {}
    assert controller.current_section() == 0


def test_route_commands_run_when_the_previous_section_is_completed(monkeypatch):
    sections = [
        RouteSection(
            required=["BULBASAUR"], bonuses=[], minimum=1, evolutions=set(),
            commands_after=[RouteCommand("MARK", "NEXT")],
        ),
        RouteSection(required=["PIDGEY"], bonuses=[], minimum=1, evolutions=set()),
    ]
    monkeypatch.setattr(game_controller_module, "ROUTE_SECTIONS", sections)
    controller = GameController()
    calls = []
    controller.register_command("mark", calls.append)

    controller.on_caught("BULBASAUR")

    assert calls == ["NEXT"]
    assert controller.current_section() == 1


def test_force_and_if_commands_dispatch_at_a_section_boundary(monkeypatch):
    sections = [
        RouteSection(
            required=["BULBASAUR"], bonuses=[], minimum=1, evolutions=set(),
            commands_after=[
                RouteCommand("IF", "CHARMANDER MARK:unexpected"),
                RouteCommand("IF", "BULBASAUR MARK:matched"),
                RouteCommand("FORCE", "PIDGEY"),
            ],
        ),
        RouteSection(required=["PIDGEY"], bonuses=[], minimum=1, evolutions=set()),
    ]
    monkeypatch.setattr(game_controller_module, "ROUTE_SECTIONS", sections)
    controller = GameController()
    calls = []
    controller.register_command("MARK", calls.append)

    controller.on_caught("BULBASAUR")

    assert calls == ["MATCHED"]
    assert "PIDGEY" in controller.found
    assert controller.section_catches == {0: ["BULBASAUR"], 1: ["PIDGEY"]}

def test_commands_at_the_beginning_and_the_end(monkeypatch, tmp_path, qtbot):
    route_path = tmp_path / "route.txt"
    route_path.write_text(
        "force:Bulbasaur\nIvysaur\nforce:Venusaur",
        encoding="utf-8",
    )
    sections = load_route_sections(route_path)
    monkeypatch.setattr(game_controller_module, "ROUTE_SECTIONS", sections)
    controller = GameController()

    qtbot.waitUntil(lambda: "BULBASAUR" in controller.found)
    assert "BULBASAUR" in controller.found
    controller.on_caught("IVYSAUR")
    assert "IVYSAUR" in controller.found
    assert "VENUSAUR" in controller.found
