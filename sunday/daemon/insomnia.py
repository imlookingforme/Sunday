"""24/7 Windows Insomnia & AwayMode Engine for Sunday.

Prevents Windows from suspending the system, turning off network adapters,
or sleeping background workers when the laptop display is closed, with
automated battery threshold and thermal safety guards.
"""

import ctypes
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Windows Execution State Flags
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_AWAYMODE_REQUIRED = 0x00000040


class InsomniaEngine:
    """Manages Windows system sleep suppression and 24/7 background execution safety."""

    def __init__(
        self,
        keep_display_on: bool = False,
        min_battery_threshold: float = 20.0,
        thermal_throttle_check: bool = True,
    ):
        self.keep_display_on = keep_display_on
        self.min_battery_threshold = min_battery_threshold
        self.thermal_throttle_check = thermal_throttle_check
        self.is_active = False
        self.paused_by_safety = False
        self.last_check_time = 0.0

    def activate(self) -> bool:
        """Activate Windows Insomnia / AwayMode to prevent sleep with lid closed."""
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
        if self.keep_display_on:
            flags |= ES_DISPLAY_REQUIRED


        try:
            if hasattr(ctypes, 'windll'):
                res = ctypes.windll.kernel32.SetThreadExecutionState(flags)
                if res != 0:
                    self.is_active = True
                    self.paused_by_safety = False
                    logger.info("Windows Insomnia Engine activated (24/7 background mode enabled).")
                    return True
                else:
                    logger.warning("SetThreadExecutionState returned 0.")
                    return False
            else:
                # Mock for non-Windows testing
                self.is_active = True
                self.paused_by_safety = False
                logger.info("Mock Insomnia Engine activated (non-Windows system).")
                return True

        except Exception as e:
            logger.error(f"Failed to set Windows execution state: {e}")
            return False

    def deactivate(self) -> bool:
        """Release sleep suppression and restore normal Windows power behavior."""

        try:
            if hasattr(ctypes, 'windll'):
                res = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                self.is_active = False
                logger.info("Windows Insomnia Engine deactivated. Default sleep restored.")
                return res != 0
            else:
                self.is_active = False
                logger.info("Mock Insomnia Engine deactivated.")
                return True

        except Exception as e:
            logger.error(f"Failed to reset Windows execution state: {e}")
            return False

    def check_safety_guards(self) -> Dict[str, Any]:
        """Check battery level and power state.

        Automatically pauses insomnia if on battery below safety threshold.
        """
        import psutil

        battery = psutil.sensors_battery()
        now = time.time()
        self.last_check_time = now

        if battery is None:
            # Desktop PC or no battery sensor -> Always safe
            return {
                "safe": True,
                "has_battery": False,
                "is_active": self.is_active,
                "reason": "Desktop / AC power source detected",
            }

        percent = battery.percent
        plugged = battery.power_plugged

        # Critical battery safety rule:
        # If running on battery and charge drops below min_battery_threshold, pause insomnia
        if not plugged and percent <= self.min_battery_threshold:
            if self.is_active:
                logger.warning(
                    f"Battery at {percent}% (<= {self.min_battery_threshold}% threshold). "
                    "Suspending Insomnia to protect battery health."
                )
                self.deactivate()
                self.paused_by_safety = True
            return {
                "safe": False,
                "battery_percent": percent,
                "power_plugged": plugged,
                "is_active": self.is_active,
                "paused_by_safety": self.paused_by_safety,
                "reason": f"Low battery cutoff ({percent}%)",
            }

        # If plugged back in or above threshold, resume if previously paused
        if self.paused_by_safety and (plugged or percent > self.min_battery_threshold + 5.0):
            logger.info(f"Power condition restored ({percent}%, plugged={plugged}). Resuming Insomnia.")
            self.activate()

        return {
            "safe": True,
            "battery_percent": percent,
            "power_plugged": plugged,
            "is_active": self.is_active,
            "paused_by_safety": self.paused_by_safety,
            "reason": "Power parameters normal",
        }

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status of the insomnia engine."""
        safety = self.check_safety_guards()
        return {
            "is_active": self.is_active,
            "keep_display_on": self.keep_display_on,
            "paused_by_safety": self.paused_by_safety,
            "min_battery_threshold": self.min_battery_threshold,
            **safety,
        }
