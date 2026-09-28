from pokedex_counter.services.route_service import RouteCommand, load_route_sections


def test_command_lines_do_not_create_empty_route_sections(tmp_path):
    route_path = tmp_path / "route.txt"
    route_path.write_text(
        "Bulbasaur\ndeposit:Bulbasaur\nCaterpie\n",
        encoding="utf-8",
    )

    sections = load_route_sections(route_path)

    assert [section.required for section in sections] == [["BULBASAUR"], ["CATERPIE"]]
    assert sections[0].commands_after == [RouteCommand("DEPOSIT", "BULBASAUR")]
    assert sections[1].commands_before == []
