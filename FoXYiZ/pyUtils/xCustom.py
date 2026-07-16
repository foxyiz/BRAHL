"""
Custom Actions Handler - For End Users

This file allows end users to add their own custom functions that can be used
in test plans. Simply add methods to the CustomActionHandler class below.

Usage in y2Actions.csv:
- ActionType: xCustom
- ActionName: your_method_name (without the 'x' prefix)
- Input: your input parameters (semicolon-separated if multiple)

Example:
    ActionType: xCustom
    ActionName: xMyCustomFunction
    Input: param1;param2;param3

The method should be named with 'x' prefix in this file:
    def xMyCustomFunction(self, aIn):
        # Your code here
        return "result"
"""

import logging
import os
import sys

# Import the base ActionHandler class from x/xActions.py (engine)
try:
    _x_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "x"))
    if _x_dir not in sys.path:
        sys.path.insert(0, _x_dir)
    from xActions import ActionHandler
except ImportError:
    try:
        x_dir = os.path.abspath(os.path.join(sys._MEIPASS, "x"))  # type: ignore[attr-defined]
        if x_dir not in sys.path:
            sys.path.insert(0, x_dir)
        from xActions import ActionHandler  # type: ignore[import-not-found]
    except Exception:
        raise ImportError("xActions.ActionHandler not found — ensure FoXYiZ/x/xActions.py exists")

logger = logging.getLogger(__name__)


class CustomActionHandler(ActionHandler):
    """
    Custom Actions Handler - Add your own functions here.

    All methods should:
    1. Start with 'x' prefix (e.g., xMyFunction)
    2. Accept 'aIn' as the first parameter (input string, semicolon-separated)
    3. Return a string result
    4. Use self.validate_input(aIn) to get and validate input
    """

    def __init__(self, timeout=6):
        super().__init__(timeout)

    # ============================================
    # ADD YOUR CUSTOM FUNCTIONS BELOW THIS LINE
    # ============================================

    def xExampleFunction(self, aIn):
        """
        Example custom function.

        Input format: "param1;param2"
        Returns: A string result
        """
        parts = self.validate_input(aIn).split(";")
        if len(parts) < 2:
            raise ValueError(f"Invalid input for xExampleFunction: {aIn}. Expected 'param1;param2'")

        param1 = parts[0].strip()
        param2 = parts[1].strip()

        logger.info(f"Example function called with: {param1}, {param2}")
        result = f"Processed: {param1} and {param2}"
        return result
