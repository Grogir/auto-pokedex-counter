"""Windows-wide keyboard shortcut registration."""

from __future__ import annotations

import ctypes
from collections.abc import Callable

from PySide6.QtCore import QAbstractNativeEventFilter


class GlobalKeybind(QAbstractNativeEventFilter):
    """Register one callback for a system-wide Windows virtual key."""

    _next_hotkey_id = 0x5043
    _WM_HOTKEY = 0x0312
    _MOD_NOREPEAT = 0x4000

    def __init__(self, virtual_key: int, callback: Callable[[], None]) -> None:
        super().__init__()
        self._user32 = ctypes.windll.user32
        self._hotkey_id = self._allocate_hotkey_id()
        self._callback = callback
        self._registered = self._user32.RegisterHotKey(
            None,
            self._hotkey_id,
            self._MOD_NOREPEAT,
            virtual_key,
        )
        if not self._registered:
            raise OSError(f"Unable to register global hotkey for virtual key {virtual_key}")

    @classmethod
    def _allocate_hotkey_id(cls) -> int:
        hotkey_id = cls._next_hotkey_id
        cls._next_hotkey_id += 1
        return hotkey_id

    def nativeEventFilter(self, event_type, message):
        if event_type != "windows_generic_MSG":
            return False, 0

        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", ctypes.c_void_p),
                ("message", ctypes.c_uint32),
                ("w_param", ctypes.c_size_t),
                ("l_param", ctypes.c_ssize_t),
                ("time", ctypes.c_uint32),
                ("point_x", ctypes.c_long),
                ("point_y", ctypes.c_long),
            ]

        native_message = ctypes.cast(int(message), ctypes.POINTER(MSG)).contents
        if (
            native_message.message == self._WM_HOTKEY
            and native_message.w_param == self._hotkey_id
        ):
            self._callback()
            return True, 0
        return False, 0

    def close(self) -> None:
        if self._registered:
            self._user32.UnregisterHotKey(None, self._hotkey_id)
            self._registered = False
