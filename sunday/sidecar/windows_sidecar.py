"""Windows sidecar for screen awareness and control."""

import win32gui
import win32con
import win32api
import win32process
from typing import Optional, Dict, Any, List
from PIL import ImageGrab
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None
    PYTESSERACT_AVAILABLE = False
import time


class WindowsSidecar:
    """Windows sidecar for screen awareness and control.

    Provides:
    - Screen capture
    - OCR
    - Window control
    - Proactive nudges based on screen context
    """

    def __init__(self):
        """Initialize Windows sidecar."""
        self.current_window = None
        self.window_history: List[Dict[str, Any]] = []
        self.max_history = 100

    def get_active_window(self) -> Optional[Dict[str, Any]]:
        """Get information about the active window.

        Returns:
            Dictionary with window info or None
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            rect = win32gui.GetWindowRect(hwnd)

            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            window_info = {
                "hwnd": hwnd,
                "title": title,
                "class_name": class_name,
                "rect": rect,
                "pid": pid,
                "timestamp": time.time()
            }

            self.current_window = window_info
            self._add_to_history(window_info)

            return window_info
        except Exception as e:
            print(f"Error getting active window: {e}")
            return None

    def _add_to_history(self, window_info: Dict[str, Any]) -> None:
        """Add window to history."""
        self.window_history.append(window_info)
        if len(self.window_history) > self.max_history:
            self.window_history.pop(0)

    def screenshot_window(self, hwnd: Optional[int] = None) -> Optional[bytes]:
        """Capture screenshot of a window.

        Args:
            hwnd: Window handle, or None for active window

        Returns:
            Screenshot as bytes or None
        """
        try:
            if hwnd is None:
                window_info = self.get_active_window()
                if not window_info:
                    return None
                hwnd = window_info["hwnd"]

            rect = win32gui.GetWindowRect(hwnd)
            screenshot = ImageGrab.grab(rect)

            # Convert to bytes
            from io import BytesIO
            buffer = BytesIO()
            screenshot.save(buffer, format="PNG")
            return buffer.getvalue()
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return None

    def screenshot_desktop(self) -> Optional[bytes]:
        """Capture screenshot of entire desktop.

        Returns:
            Screenshot as bytes or None
        """
        try:
            screenshot = ImageGrab.grab()

            from io import BytesIO
            buffer = BytesIO()
            screenshot.save(buffer, format="PNG")
            return buffer.getvalue()
        except Exception as e:
            print(f"Error capturing desktop screenshot: {e}")
            return None

    def ocr_screen(self, image_bytes: Optional[bytes] = None) -> str:
        """Extract text from screen using OCR.

        Args:
            image_bytes: Image bytes, or None for current screen

        Returns:
            Extracted text
        """
        try:
            if not PYTESSERACT_AVAILABLE or pytesseract is None:
                return ""
            from PIL import Image
            from io import BytesIO

            if image_bytes is None:
                image_bytes = self.screenshot_desktop()
                if not image_bytes:
                    return ""

            image = Image.open(BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            print(f"Error performing OCR: {e}")
            return ""

    def switch_window(self, hwnd: int) -> bool:
        """Switch to a window.

        Args:
            hwnd: Window handle

        Returns:
            True if successful
        """
        try:
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception as e:
            print(f"Error switching window: {e}")
            return False

    def close_window(self, hwnd: int) -> bool:
        """Close a window.

        Args:
            hwnd: Window handle

        Returns:
            True if successful
        """
        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return True
        except Exception as e:
            print(f"Error closing window: {e}")
            return False

    def minimize_window(self, hwnd: int) -> bool:
        """Minimize a window.

        Args:
            hwnd: Window handle

        Returns:
            True if successful
        """
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return True
        except Exception as e:
            print(f"Error minimizing window: {e}")
            return False

    def maximize_window(self, hwnd: int) -> bool:
        """Maximize a window.

        Args:
            hwnd: Window handle

        Returns:
            True if successful
        """
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return True
        except Exception as e:
            print(f"Error maximizing window: {e}")
            return False

    def list_windows(self) -> List[Dict[str, Any]]:
        """List all visible windows.

        Returns:
            List of window info dictionaries
        """
        windows = []

        def callback(hwnd, windows_list):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:  # Only include windows with titles
                    windows_list.append({
                        "hwnd": hwnd,
                        "title": title,
                        "class_name": win32gui.GetClassName(hwnd)
                    })
            return True

        win32gui.EnumWindows(callback, windows)
        return windows

    def get_screen_context(self) -> Dict[str, Any]:
        """Get current screen context for proactive nudges.

        Returns:
            Dictionary with screen context
        """
        active_window = self.get_active_window()
        ocr_text = self.ocr_screen()

        context = {
            "active_window": active_window,
            "screen_text": ocr_text[:500] if ocr_text else "",  # First 500 chars
            "timestamp": time.time()
        }

        return context

    def analyze_screen_for_context(self) -> Dict[str, Any]:
        """Analyze screen for proactive suggestions.

        Returns:
            Dictionary with analysis results
        """
        context = self.get_screen_context()
        suggestions = []

        # Analyze active window
        if context["active_window"]:
            title = context["active_window"]["title"].lower()

            # Check for specific applications
            if "outlook" in title or "mail" in title:
                suggestions.append("You're in your email. Need help drafting a reply?")
            elif "word" in title or "document" in title:
                suggestions.append("Working on a document? I can help with writing or editing.")
            elif "excel" in title or "spreadsheet" in title:
                suggestions.append("In Excel? I can help with formulas or data analysis.")
            elif "browser" in title or "chrome" in title or "edge" in title:
                suggestions.append("Browsing the web? I can help with research or information.")
            elif "code" in title or "visual studio" in title or "pycharm" in title:
                suggestions.append("Coding? I can help with debugging or code review.")

        # Analyze screen text
        if context["screen_text"]:
            text_lower = context["screen_text"].lower()

            if "error" in text_lower or "failed" in text_lower:
                suggestions.append("I see an error message. Would you like help troubleshooting?")
            elif "deadline" in text_lower or "due" in text_lower:
                suggestions.append("I see a deadline mentioned. Should I add a reminder?")
            elif "meeting" in text_lower:
                suggestions.append("Meeting detected. Would you like me to take notes?")

        return {
            "context": context,
            "suggestions": suggestions
        }
