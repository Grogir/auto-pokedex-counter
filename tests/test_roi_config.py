"""Locks in build_detection_entries()'s contract: run_calibration()'s
locked ROIs must apply in-memory for this session regardless of whether
they got persisted to disk (see test_calibration_runner.py and
test_roi_writer.py for the persistence side of that).

ROI_CATCH/ROI_EVOLVE/ROI_TEXT reflect this machine's actual calibration
state (None until calibrated at least once - see roi_config.py), so tests
that care about a specific calibrated/uncalibrated state monkeypatch them
explicitly rather than relying on whatever's true locally.

Also guards CATCH_SECTIONS_RAW - the hand-authored catch route - against
transcription mistakes: every entry must resolve to a real sprite
template, and every dex number needs to be detectable somewhere.
"""

from collections import defaultdict
from pathlib import Path

import pokedex_counter.roi_config as roi_config
from pokedex_counter.config import SPRITES_BG_DIR
from pokedex_counter.game_config import BONUSES, POKEMON_NAME_TO_DEX
from pokedex_counter.roi_config import (
    CATCH_SECTIONS,
    SECTION_TRIGGERS,
    build_detection_entries,
    is_evolution,
)
from pokedex_counter.services.template_service import TemplateService


def _fake_templates():
    return defaultdict(lambda: "template-stub")


def test_returns_nothing_when_no_roi_is_calibrated(monkeypatch):
    monkeypatch.setattr(roi_config, "ROI_CATCH", None)
    monkeypatch.setattr(roi_config, "ROI_EVOLVE", None)
    monkeypatch.setattr(roi_config, "ROI_TEXT", None)

    assert build_detection_entries(_fake_templates(), locked=None) == []


def test_uses_persisted_rois_when_nothing_freshly_locked(monkeypatch):
    monkeypatch.setattr(roi_config, "ROI_CATCH", (10, 10, 10, 10))
    monkeypatch.setattr(roi_config, "ROI_EVOLVE", (20, 20, 20, 20))
    monkeypatch.setattr(roi_config, "ROI_TEXT", (30, 30, 30, 30))

    result = build_detection_entries(_fake_templates(), locked=None)

    assert len(result) == sum(len(section) for section in CATCH_SECTIONS)
    rois_used = {roi for _, roi, _, _ in result}
    assert rois_used == {(10, 10, 10, 10), (20, 20, 20, 20), (30, 30, 30, 30)}


def test_locked_overrides_persisted_rois(monkeypatch):
    monkeypatch.setattr(roi_config, "ROI_CATCH", (10, 10, 10, 10))
    monkeypatch.setattr(roi_config, "ROI_EVOLVE", (20, 20, 20, 20))
    monkeypatch.setattr(roi_config, "ROI_TEXT", (30, 30, 30, 30))

    result = build_detection_entries(_fake_templates(), {"CATCH": (1, 1, 1, 1)})

    rois_used = {roi for _, roi, _, _ in result}
    assert rois_used == {(1, 1, 1, 1), (20, 20, 20, 20), (30, 30, 30, 30)}


def test_partial_lock_only_includes_calibrated_labels(monkeypatch):
    monkeypatch.setattr(roi_config, "ROI_CATCH", None)
    monkeypatch.setattr(roi_config, "ROI_EVOLVE", None)
    monkeypatch.setattr(roi_config, "ROI_TEXT", None)

    result = build_detection_entries(_fake_templates(), {"EVOLVE": (9, 9, 9, 9)})

    # only EVOLVE-labeled entries have a real position; CATCH/TEXT are still
    # unlocked (None) and must be skipped entirely, not included with a
    # None roi.
    assert result
    rois_used = {roi for _, roi, _, _ in result}
    assert rois_used == {(9, 9, 9, 9)}


def test_preserves_section_order_and_tags_each_entry_with_its_section():
    locked = {"CATCH": (1, 1, 1, 1), "EVOLVE": (2, 2, 2, 2), "TEXT": (3, 3, 3, 3)}
    result = build_detection_entries(_fake_templates(), locked)

    expected = [
        (name, section_index)
        for section_index, section in enumerate(CATCH_SECTIONS)
        for name, _roi_label in section
    ]
    assert [(name, section_index) for name, _roi, _template, section_index in result] == expected


def test_every_pokemon_has_at_least_one_detection_path():
    covered = {name for section in CATCH_SECTIONS for name, _roi_label in section}
    assert set(POKEMON_NAME_TO_DEX) - covered == set()


def test_section_triggers_are_members_of_their_own_section():
    for section_index, trigger in enumerate(SECTION_TRIGGERS):
        if trigger is None:
            continue
        names_in_section = {name for name, _roi_label in CATCH_SECTIONS[section_index]}
        assert trigger in names_in_section


def test_bonuses_are_pokemon_names():
    """BONUSES is hand-edited and only ever used for a lookup by sprite
    name, so a typo'd or non-dex entry would silently never highlight
    rather than fail loudly."""
    assert all(name in POKEMON_NAME_TO_DEX for name in BONUSES), (
        f"unknown Pokémon names: {sorted(set(BONUSES) - set(POKEMON_NAME_TO_DEX))}"
    )


# def test_a_section_evolve_override_counts_as_an_evolution():
#     for section_index, names in roi_config.SECTION_EVOLVE_OVERRIDES.items():
#         for name in names:
#             caught_here_too = any(
#                 entry_name == name and roi_label != "EVOLVE"
#                 for entry_name, roi_label in CATCH_SECTIONS[section_index]
#             )
#             assert is_evolution(section_index, name) is not caught_here_too


def test_the_final_sweep_section_counts_as_evolutions():
    """build_catch_sections() rakes every unrouted evolution onto the end of
    the last section. That sweep is where most of the run's evolutions
    happen, so it's the case the bonus highlight most needs to exclude."""
    assert is_evolution(len(CATCH_SECTIONS) - 1, "RATICATE")  # Raticate, swept
    assert not is_evolution(5, "RATICATE")  # ...but a real catch back in section 6


def test_a_catch_is_never_an_evolution():
    for section_index, section in enumerate(CATCH_SECTIONS):
        for name, roi_label in section:
            if roi_label == "CATCH":
                assert not is_evolution(section_index, name)


def test_an_out_of_range_section_is_not_an_evolution():
    """Nothing should ever ask, but a section index that fell out of sync
    must degrade to "it was caught" rather than raise mid-run."""
    assert not is_evolution(-1, "RATICATE")
    assert not is_evolution(len(CATCH_SECTIONS), "RATICATE")


def test_every_entry_resolves_to_a_real_sprite_template():
    templates = TemplateService(Path(SPRITES_BG_DIR)).templates
    locked = {"CATCH": (0, 0, 10, 10), "EVOLVE": (0, 0, 10, 10), "TEXT": (0, 0, 10, 10)}

    build_detection_entries(templates, locked)  # raises KeyError on a typo'd dex number
