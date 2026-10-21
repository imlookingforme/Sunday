import re
with open("/app/sunday/daemon/insomnia.py", "r") as f:
    code = f.read()

# Make it cross-platform compatible for testing in linux environments
patch = """
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
"""
code = code.replace("""        try:
            res = ctypes.windll.kernel32.SetThreadExecutionState(flags)
            if res != 0:
                self.is_active = True
                self.paused_by_safety = False
                logger.info("Windows Insomnia Engine activated (24/7 background mode enabled).")
                return True
            else:
                logger.warning("SetThreadExecutionState returned 0.")
                return False""", patch)


patch2 = """
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
"""
code = code.replace("""        try:
            res = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            self.is_active = False
            logger.info("Windows Insomnia Engine deactivated. Default sleep restored.")
            return res != 0""", patch2)

with open("/app/sunday/daemon/insomnia.py", "w") as f:
    f.write(code)
