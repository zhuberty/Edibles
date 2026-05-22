"""
arcade_encoders
===============
A module for interfacing with Reyann Easyget Zero Delay USB Encoders.

Each encoder exposes:
  - 1 joystick (4 directions: up, down, left, right) via axes
  - 8 buttons

This module is independent of the Edibles snake game and can be used
as a standalone interface or imported by the game.

Public API
----------
EncoderDevice   -- wraps a single pygame.joystick.Joystick
EncoderManager  -- discovers and manages all connected encoders
InputTest       -- guided input-test sequence for all encoders
EncoderSetup    -- one-time interactive player-assignment wizard
load_player_map -- load the saved player→USB-port mapping from disk
save_player_map -- persist the player→USB-port mapping to disk
"""

from .encoder_device import EncoderDevice
from .encoder_manager import EncoderManager
from .input_test import InputTest
from .encoder_setup import EncoderSetup, load_player_map, save_player_map

__all__ = [
    "EncoderDevice",
    "EncoderManager",
    "InputTest",
    "EncoderSetup",
    "load_player_map",
    "save_player_map",
]
