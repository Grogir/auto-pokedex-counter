"""Observe a Windows-wide key without consuming it in other applications."""

import ctypes
import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("virtual_key", ctypes.c_uint32),
        ("scan_code", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("time", ctypes.c_uint32),
        ("extra_info", ctypes.c_size_t),
    ]


class GlobalHotkey:
    """Call a callback on key-down while passing the key through to Windows."""

    _WH_KEYBOARD_LL = 13
    _WM_KEYDOWN = 0x0100
    _WM_KEYUP = 0x0101
    _WM_SYSKEYDOWN = 0x0104
    _WM_SYSKEYUP = 0x0105

    def __init__(self, virtual_key: int, callback: Callable[[], None]) -> None:
        self._user32 = ctypes.windll.user32
        self._virtual_key = virtual_key
        self._callback = callback
        self._key_is_down = False

        callback_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            ctypes.c_int,
            ctypes.c_size_t,
            ctypes.c_void_p,
        )
        self._hook_proc = callback_type(self._keyboard_proc)

        self._user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int,
            callback_type,
            ctypes.c_void_p,
            ctypes.c_uint32,
        ]
        self._user32.SetWindowsHookExW.restype = ctypes.c_void_p
        self._user32.CallNextHookEx.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_size_t,
            ctypes.c_ssize_t,
        ]
        self._user32.CallNextHookEx.restype = ctypes.c_ssize_t
        self._user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
        self._user32.UnhookWindowsHookEx.restype = ctypes.c_int

        self._hook = self._user32.SetWindowsHookExW(
            self._WH_KEYBOARD_LL,
            self._hook_proc,
            None,
            0,
        )
        if not self._hook:
            raise OSError(f"Unable to install global keyboard hook for virtual key {virtual_key}")

    def _keyboard_proc(self, code: int, message: int, data: int) -> int:
        if code >= 0:
            native_message = ctypes.cast(
                data,
                ctypes.POINTER(_KBDLLHOOKSTRUCT),
            ).contents
            if native_message.virtual_key == self._virtual_key:
                if message in (self._WM_KEYDOWN, self._WM_SYSKEYDOWN):
                    if not self._key_is_down:
                        self._key_is_down = True
                        try:
                            self._callback()
                        except Exception:
                            logger.exception("Global hotkey callback failed")
                elif message in (self._WM_KEYUP, self._WM_SYSKEYUP):
                    self._key_is_down = False

        # A low-level hook must always relay the event to the next hook/app.
        return self._user32.CallNextHookEx(self._hook, code, message, data)

    def close(self) -> None:
        if self._hook:
            self._user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
