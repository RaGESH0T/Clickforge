from clickforge.core.models import ClickType, MouseButton, RepeatMode
from clickforge.services.presets import BUILTIN_PRESETS, preset_by_key


def test_builtin_presets_are_complete_and_distinct():
    assert [preset.key for preset in BUILTIN_PRESETS] == ["balanced", "rapid", "steady"]
    assert len({preset.name for preset in BUILTIN_PRESETS}) == 3


def test_preset_summaries_are_human_readable():
    assert BUILTIN_PRESETS[0].summary == "100 ms · Left · Single · Continuous"
    assert BUILTIN_PRESETS[1].summary == "50 ms · Left · Double · 250 repeats"
    assert BUILTIN_PRESETS[2].summary == "1 s · Right · Single · Continuous"


def test_rapid_preset_uses_double_click_fixed_mode():
    rapid = preset_by_key("rapid")
    assert rapid is not None
    assert rapid.profile.click_type is ClickType.DOUBLE
    assert rapid.profile.mouse_button is MouseButton.LEFT
    assert rapid.profile.repeat_mode is RepeatMode.FIXED
    assert rapid.profile.repeat_count == 250
    assert preset_by_key("missing") is None
