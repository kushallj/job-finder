"""
invisibility_macos.py — Native macOS WindowServer Invisibility Bridge.

Uses Cocoa / Objective-C runtime via PyObjC or ctypes to set:
1. `NSWindow.sharingType = .none` (0) -> Excludes window from ScreenCaptureKit, Zoom, Meet, Teams.
2. `NSWindow.level = .floating` (3) -> Always floats on top of full-screen IDEs/browsers.
3. `NSWindowCollectionBehavior` -> [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary].
4. Transparent glassmorphism and click-through toggling.
"""
import ctypes
import logging
import sys

logger = logging.getLogger("sidekick.native.macos")

# Cocoa Constants
NSWindowSharingNone = 0
NSWindowSharingReadOnly = 1
NSFloatingWindowLevel = 3
NSWindowCollectionBehaviorCanJoinAllSpaces = 1 << 0
NSWindowCollectionBehaviorStationary = 1 << 4
NSWindowCollectionBehaviorFullScreenAuxiliary = 1 << 8


def make_macos_window_invisible(window_title_or_id: str = None) -> bool:
    """
    Applies NSWindowSharingNone to the target window or all windows owned by the current process.
    Returns True if successfully applied.
    """
    if sys.platform != "darwin":
        logger.warning("make_macos_window_invisible called on non-macOS platform")
        return False

    try:
        # Attempt via PyObjC AppKit if available
        from AppKit import NSApplication, NSWindowSharingNone as NS_NONE, NSFloatingWindowLevel as NS_FLOAT
        app = NSApplication.sharedApplication()
        windows = app.windows()
        
        applied_count = 0
        for win in windows:
            title = win.title()
            if not window_title_or_id or window_title_or_id.lower() in str(title).lower():
                # 1. Set Invisibility on Screen Capture
                win.setSharingType_(NS_NONE)
                
                # 2. Float above all apps
                win.setLevel_(NS_FLOAT)
                
                # 3. Join all virtual spaces/desktops
                behavior = (
                    NSWindowCollectionBehaviorCanJoinAllSpaces
                    | NSWindowCollectionBehaviorStationary
                    | NSWindowCollectionBehaviorFullScreenAuxiliary
                )
                win.setCollectionBehavior_(behavior)
                
                # 4. Enable transparent backing
                win.setOpaque_(False)
                applied_count += 1
                logger.info(f"✅ Successfully made macOS NSWindow '{title}' invisible to screen share (sharingType=NONE).")

        return applied_count > 0

    except ImportError:
        logger.info("PyObjC AppKit not installed. Attempting ctypes / objc runtime fallback...")
        return _apply_via_objc_runtime(window_title_or_id)
    except Exception as exc:
        logger.error(f"Error making macOS window invisible: {exc}")
        return False


def _apply_via_objc_runtime(window_title_or_id: str = None) -> bool:
    """Fallback using libobjc.dylib directly."""
    try:
        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        objc.objc_msgSend.restype = ctypes.c_void_p
        
        ns_app_cls = objc.objc_getClass(b"NSApplication")
        sel_shared_app = objc.sel_registerName(b"sharedApplication")
        sel_windows = objc.sel_registerName(b"windows")
        sel_count = objc.sel_registerName(b"count")
        sel_object_at_index = objc.sel_registerName(b"objectAtIndex:")
        sel_set_sharing_type = objc.sel_registerName(b"setSharingType:")
        
        app = objc.objc_msgSend(ns_app_cls, sel_shared_app)
        if not app:
            logger.warning("Could not acquire NSApplication sharedApplication via objc runtime.")
            return False
            
        windows = objc.objc_msgSend(app, sel_windows)
        if not windows:
            return False
            
        count = objc.objc_msgSend(windows, sel_count)
        for i in range(count):
            win = objc.objc_msgSend(windows, sel_object_at_index, ctypes.c_ulong(i))
            # Set sharingType = NSWindowSharingNone (0)
            objc.objc_msgSend(win, sel_set_sharing_type, ctypes.c_ulong(0))
            
        logger.info(f"✅ Applied NSWindowSharingNone to {count} windows via ObjC runtime.")
        return True
    except Exception as exc:
        logger.error(f"ObjC runtime fallback failed: {exc}")
        return False
