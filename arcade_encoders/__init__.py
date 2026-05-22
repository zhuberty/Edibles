"""
arcade_encoders
===============
A module for interfacing with Reyann Easyget Zero Delay USB Encoders.

Each encoder exposes:
  - 1 joystick (4 directions: up, down, left, right) via a hat switch
  - 8 buttons

This module is independent of the Edibles snake game and can be used
as a standalone interface or imported by the game.

Public API
----------
EncoderDevice   -- wraps a single pygame.joystick.Joystick
EncoderManager  -- discovers and manages all connected encoders
InputTest       -- guided input-test sequence for all encoders
"""

from .encoder_device import EncoderDevice
from .encoder_manager import EncoderManager
from .input_test import InputTest

__all__ = ["EncoderDevice", "EncoderManager", "InputTest"]
