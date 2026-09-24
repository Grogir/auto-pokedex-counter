import json

from pokedex_counter.game_config import ROUTE_SECTIONS
from pokedex_counter.services import wr_service


def test_load_wr_sections_reconstructs_sections_from_current_route(tmp_path, monkeypatch):
    first_section = ROUTE_SECTIONS[0].required
    second_section = ROUTE_SECTIONS[1].required
    wr_path = tmp_path / "WR.json"
    wr_path.write_text(
        json.dumps({"999": first_section + second_section}),
        encoding="utf-8",
    )
    monkeypatch.setattr(wr_service, "WR_JSON_PATH", wr_path)

    result = wr_service.load_wr_sections()

    assert result[0] == set(first_section)
    assert result[1] == set(second_section)
    assert 999 not in result
