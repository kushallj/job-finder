"""
Native OS Invisibility & Compositor Bypass Module.
"""
import sys
import logging
from typing import Dict, Any

from .invisibility_macos import make_macos_window_invisible
from .invisibility_windows import make_windows_window_invisible

logger = logging.getLogger("sidekick.native")


def set_window_invisible(window_identifier: str = None) -> Dict[str, Any]:
    """
    Platform-agnostic entry point to make HUD overlays invisible to screen capture.
    """
    platform = sys.platform
    success = False
    mechanism = "unknown"

    if platform == "darwin":
        success = make_macos_window_invisible(window_identifier)
        mechanism = "macOS NSWindow.sharingType = NSWindowSharingNone (0)"
    elif platform == "win32":
        success = make_windows_window_invisible(window_identifier)
        mechanism = "Windows SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE: 0x11)"
    else:
        mechanism = f"Unsupported platform: {platform} (Linux Wayland/X11 requires compositor override)"
        logger.warning(mechanism)

    return {
        "status": "success" if success else "failed",
        "platform": platform,
        "mechanism": mechanism,
        "is_invisible": success,
    }


def is_invisibility_supported() -> bool:
    """Check if the current operating system supports native screen capture exclusion."""
    return sys.platform in ["darwin", "win32"]
