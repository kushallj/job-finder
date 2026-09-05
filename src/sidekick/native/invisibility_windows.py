"""
invisibility_windows.py — Native Windows DWM Invisibility Bridge.

Uses Win32 API via ctypes to invoke `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` (0x00000011).
Completely excludes target windows from DirectX Desktop Duplication, BitBlt, Zoom, and Teams screen capture.
"""
import ctypes
import logging
import sys

logger = logging.getLogger("sidekick.native.windows")

WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011

WS_EX_LAYERED = 0x00080000
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
GWL_EXSTYLE = -20


def make_windows_window_invisible(hwnd_or_title: str = None) -> bool:
    """
    Sets WDA_EXCLUDEFROMCAPTURE on the target HWND or active process window.
    """
    if sys.platform != "win32":
        logger.warning("make_windows_window_invisible called on non-Windows platform")
        return False

    try:
        user32 = ctypes.windll.user32
        
        target_hwnd = None
        if isinstance(hwnd_or_title, int):
            target_hwnd = hwnd_or_title
        elif isinstance(hwnd_or_title, str) and hwnd_or_title.isdigit():
            target_hwnd = int(hwnd_or_title)
        elif isinstance(hwnd_or_title, str):
            target_hwnd = user32.FindWindowW(None, hwnd_or_title)
        else:
            target_hwnd = user32.GetForegroundWindow()

        if not target_hwnd:
            logger.warning("Could not locate target HWND for Windows invisibility.")
            return False

        # Set Display Affinity to EXCLUDE FROM CAPTURE
        result = user32.SetWindowDisplayAffinity(target_hwnd, WDA_EXCLUDEFROMCAPTURE)
        if not result:
            # Fallback for older Windows 10 versions
            result = user32.SetWindowDisplayAffinity(target_hwnd, WDA_MONITOR)

        # Apply Layered & TopMost Styles
        current_style = user32.GetWindowLongW(target_hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(target_hwnd, GWL_EXSTYLE, current_style | WS_EX_LAYERED | WS_EX_TOPMOST)

        logger.info(f"✅ Successfully set WDA_EXCLUDEFROMCAPTURE on HWND {target_hwnd} (Result: {result}).")
        return bool(result)

    except Exception as exc:
        logger.error(f"Failed to set Windows window display affinity: {exc}")
        return False
