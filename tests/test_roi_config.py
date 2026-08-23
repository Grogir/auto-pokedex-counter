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
from pokedex_counter.roi_config import (
    BONUSES,
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


def test_every_dex_number_has_at_least_one_detection_path():
    covered = {name for section in CATCH_SECTIONS for name, _roi_label in section}
    all_dex_numbers = {str(i) for i in range(1, 152)}
    assert all_dex_numbers - covered == set()


def test_section_triggers_are_members_of_their_own_section():
    for section_index, required in enumerate(SECTION_TRIGGERS):
        names_in_section = {name for name, _roi_label in CATCH_SECTIONS[section_index]}
        assert set(required) <= names_in_section, (
            f"section {section_index} requires {sorted(set(required) - names_in_section)}, "
            "which it never offers - the run would stall there"
        )


def test_every_section_but_the_last_can_be_advanced_past():
    """An empty list would strand the run on that section forever (see
    DetectionService._section_cleared, which refuses to treat "nothing
    required" as cleared). Only the final section may have one."""
    for section_index, required in enumerate(SECTION_TRIGGERS[:-1]):
        assert required, f"section {section_index} has no way to advance"
    assert SECTION_TRIGGERS[-1] == []


def test_a_trigger_is_never_catchable_in_a_later_section():
    """A dex number the route offers again later may legitimately be saved
    for then, so requiring it early would stall a run that does. It's only
    required in its LAST section - by then there's no later chance left."""
    catchable_in = defaultdict(set)
    for section_index, section in enumerate(CATCH_SECTIONS):
        for name, _roi_label in section:
            catchable_in[name].add(section_index)

    for section_index, required in enumerate(SECTION_TRIGGERS):
        for name in required:
            later = {s for s in catchable_in[name] if s > section_index}
            assert not later, (
                f"section {section_index} requires {name}, but it's still catchable in "
                f"{sorted(later)} - a run saving it for then would never advance"
            )


def test_every_pokemon_is_required_by_its_last_chance():
    """The flip side: nothing may quietly stop being required. Anything
    whose last appearance is before the final section has to gate it, or
    catching it could be skipped without the run ever noticing."""
    last_chance = {}
    for section_index, section in enumerate(CATCH_SECTIONS):
        for name, _roi_label in section:
            last_chance[name] = section_index

    final = len(CATCH_SECTIONS) - 1
    for name, section_index in last_chance.items():
        if section_index == final or name in BONUSES:
            continue  # the final section gates nothing; bonuses are optional
        assert name in SECTION_TRIGGERS[section_index], (
            f"{name} is last offered in section {section_index} but doesn't gate it"
        )


def test_a_bonus_never_gates_a_section():
    """A bonus is an optional wild catch, so the section has to end whether
    or not the player took it. Every bonus is currently also an evolution,
    which keeps it out of the triggers anyway - this guards the case where
    that stops being true and one silently turns mandatory."""
    for section_index, required in enumerate(SECTION_TRIGGERS):
        assert not set(required) & BONUSES, (
            f"section {section_index} requires bonus {sorted(set(required) & BONUSES)}, "
            "which the run is free to skip - it would never advance"
        )


def test_section_triggers_covers_every_section():
    assert len(SECTION_TRIGGERS) == len(CATCH_SECTIONS)


def test_bonuses_are_dex_numbers():
    """BONUSES is hand-edited and only ever used for a lookup by sprite
    name, so a typo'd or non-dex entry would silently never highlight
    rather than fail loudly."""
    assert all(name.isdigit() and 1 <= int(name) <= 151 for name in BONUSES), (
        f"not dex numbers: {sorted(name for name in BONUSES if not name.isdigit() or not 1 <= int(name) <= 151)}"
    )


def test_a_section_evolve_override_counts_as_an_evolution():
    for section_index, names in roi_config.SECTION_EVOLVE_OVERRIDES.items():
        for name in names:
            caught_here_too = any(
                entry_name == name and roi_label != "EVOLVE"
                for entry_name, roi_label in CATCH_SECTIONS[section_index]
            )
            assert is_evolution(section_index, name) is not caught_here_too


def test_the_final_sweep_section_counts_as_evolutions():
    """build_catch_sections() rakes every unrouted evolution onto the end of
    the last section. That sweep is where most of the run's evolutions
    happen, so it's the case the bonus highlight most needs to exclude."""
    assert is_evolution(len(CATCH_SECTIONS) - 1, "20")  # Raticate, swept
    assert not is_evolution(5, "20")  # ...but a real catch back in section 6


def test_a_catch_is_never_an_evolution():
    for section_index, section in enumerate(CATCH_SECTIONS):
        for name, roi_label in section:
            if roi_label == "CATCH":
                assert not is_evolution(section_index, name)


def test_an_out_of_range_section_is_not_an_evolution():
    """Nothing should ever ask, but a section index that fell out of sync
    must degrade to "it was caught" rather than raise mid-run."""
    assert not is_evolution(-1, "20")
    assert not is_evolution(len(CATCH_SECTIONS), "20")


def test_every_entry_resolves_to_a_real_sprite_template():
    templates = TemplateService(Path(SPRITES_BG_DIR)).templates
    locked = {"CATCH": (0, 0, 10, 10), "EVOLVE": (0, 0, 10, 10), "TEXT": (0, 0, 10, 10)}

    build_detection_entries(templates, locked)  # raises KeyError on a typo'd dex number
