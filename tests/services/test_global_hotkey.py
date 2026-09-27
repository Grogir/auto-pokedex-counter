import ctypes
from unittest.mock import Mock

from pokedex_counter.services.global_hotkey import _KBDLLHOOKSTRUCT, GlobalHotkey


class FakeUser32:
    def __init__(self):
        self.forwarded = []

    def CallNextHookEx(self, hook, code, message, data):
        self.forwarded.append((hook, code, message, data))
        return 1


def test_key_events_trigger_once_per_press_and_are_always_forwarded():
    binding = GlobalHotkey.__new__(GlobalHotkey)
    binding._user32 = FakeUser32()
    binding._hook = 42
    binding._virtual_key = 0x08
    binding._callback = Mock()
    binding._key_is_down = False

    key_data = _KBDLLHOOKSTRUCT(virtual_key=0x08)
    data_address = ctypes.addressof(key_data)

    for message in (
        GlobalHotkey._WM_KEYDOWN,
        GlobalHotkey._WM_KEYDOWN,
        GlobalHotkey._WM_KEYUP,
        GlobalHotkey._WM_KEYDOWN,
    ):
        assert binding._keyboard_proc(0, message, data_address) == 1

    assert binding._callback.call_count == 2
    assert len(binding._user32.forwarded) == 4
