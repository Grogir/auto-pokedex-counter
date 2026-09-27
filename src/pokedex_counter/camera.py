"""Locates the camera/capture device index for a named DirectShow device
(the OBS Virtual Camera, by default), since device indices aren't stable
across machines or reboots but device names are.
"""
from __future__ import annotations

from pygrabber.dshow_graph import FilterGraph

DEFAULT_CAMERA_NAME = "OBS Virtual Camera"
FALLBACK_CAMERA_INDEX = 0


def find_camera_index(name: str = DEFAULT_CAMERA_NAME) -> int | None:
    """Returns the DirectShow device index whose name contains `name`
    (case-insensitive), or None if no such device is currently listed.
    """
    try:
        devices = FilterGraph().get_input_devices()
    except Exception as exc:
        # DirectShow/COM enumeration failing (no devices, driver issues,
        # running somewhere without a working DirectShow subsystem) must
        # never be fatal — just means we couldn't auto-detect.
        print(f"[Camera] Could not enumerate capture devices ({exc}).")
        return None

    name_lower = name.lower()
    for index, device_name in enumerate(devices):
        if name_lower in device_name.lower():
            return index

    return None


def resolve_camera_index(name: str = DEFAULT_CAMERA_NAME, fallback: int = FALLBACK_CAMERA_INDEX) -> int:
    index = find_camera_index(name)
    if index is not None:
        print(f"[Camera] Found '{name}' at index {index}.")
        return index

    print(f"[Camera] Could not find a device named '{name}'; falling back to index {fallback}.")
    return fallback
