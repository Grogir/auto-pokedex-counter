import json

from pokedex_counter.game_config import BONUSES, ROUTE_SECTIONS
from pokedex_counter.services import comparison_service


def test_loads_valid_comparisons_from_both_folders_and_skips_invalid_json(
    monkeypatch, tmp_path
):
    bundled = tmp_path / "bundled"
    external = tmp_path / "external"
    bundled.mkdir()
    external.mkdir()
    bonus = next(iter(BONUSES))

    (bundled / "PB.json").write_text(json.dumps({"0": [bonus]}), encoding="utf-8")
    (external / "PB.json").write_text(json.dumps({"0": [bonus]}), encoding="utf-8")
    (external / "broken.json").write_text("{", encoding="utf-8")
    (external / "wrong-shape.json").write_text(json.dumps([bonus]), encoding="utf-8")
    monkeypatch.setattr(comparison_service, "COMPARISON_DIRS", (bundled, external))

    comparisons = comparison_service.load_comparisons()

    assert [item.name for item in comparisons] == ["PB (bundled)", "PB (external)"]
    assert len({item.key for item in comparisons}) == 2
    last_section = len(ROUTE_SECTIONS) - 1
    assert all(bonus in item.cumulative_bonuses[last_section] for item in comparisons)
