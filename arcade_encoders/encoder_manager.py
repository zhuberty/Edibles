"""
encoder_manager.py
------------------
Discovers and manages all Reyann Easyget Zero Delay USB Encoders
that are connected to the system.

The Zero Delay encoder identifies itself with the USB product name
"USB Gamepad" (or similar).  EncoderManager scans all pygame joysticks
and wraps the matching ones as EncoderDevice objects.

If you have other joysticks/gamepads connected, they will be ignored
unless you set strict_filter=False, in which case ALL joysticks are
treated as encoders.

Usage
-----
    manager = EncoderManager()
    manager.init()

    encoder1 = manager.get_encoder(0)   # first encoder
    encoder2 = manager.get_encoder(1)   # second encoder

    direction = encoder1.get_direction()
    buttons   = encoder1.get_all_buttons()
"""

import pygame
from .encoder_device import EncoderDevice


# Substrings found in the device name reported by the Zero Delay encoder.
# Matching is case-insensitive.
# The Reyann Easyget Zero Delay encoder identifies itself via the DragonRise
# chipset as "DragonRise Inc.   Generic   USB  Joystick" on Linux.
ENCODER_NAME_HINTS = [
    "usb gamepad",
    "zero delay",
    "easyget",
    "arcade",
    "dragonrise",
    "generic usb joystick",
]


class EncoderManager:
    """
    Discovers and holds references to all connected Zero Delay USB Encoders.

    Parameters
    ----------
    strict_filter : bool
        If True (default), only joysticks whose name matches one of the
        ENCODER_NAME_HINTS are treated as encoders.
        If False, every joystick found by pygame is treated as an encoder.
        Set to False if your encoder reports an unexpected name.
    """

    def __init__(self, strict_filter: bool = True):
        self._strict_filter = strict_filter
        self._encoders: list[EncoderDevice] = []

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def init(self) -> None:
        """
        Initialise pygame's joystick subsystem and discover all encoders.

        Call this once after pygame.init() has been called.
        """
        if not pygame.joystick.get_init():
            pygame.joystick.init()

        self._encoders.clear()
        total = pygame.joystick.get_count()

        encoder_number = 1
        for i in range(total):
            js = pygame.joystick.Joystick(i)
            js.init()
            name = js.get_name()

            if self._strict_filter and not self._is_encoder(name):
                js.quit()
                continue

            label = f"Encoder {encoder_number}"
            device = EncoderDevice(joystick_index=i, label=label)
            self._encoders.append(device)
            encoder_number += 1

        if not self._encoders:
            print(
                "[arcade_encoders] WARNING: No encoders found. "
                "Check USB connections or set strict_filter=False."
            )
        else:
            for enc in self._encoders:
                print(f"[arcade_encoders] Found: {enc}")

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def get_encoder(self, index: int) -> EncoderDevice:
        """
        Return the encoder at position *index* (0-based) in discovery order.

        Raises IndexError if index is out of range.
        """
        if index < 0 or index >= len(self._encoders):
            raise IndexError(
                f"Encoder index {index} out of range "
                f"({len(self._encoders)} encoder(s) found)"
            )
        return self._encoders[index]

    @property
    def encoders(self) -> list:
        """List of all discovered EncoderDevice objects."""
        return list(self._encoders)

    @property
    def count(self) -> int:
        """Number of encoders discovered."""
        return len(self._encoders)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_encoder(device_name: str) -> bool:
        """Return True if *device_name* looks like a Zero Delay encoder."""
        lower = device_name.lower()
        return any(hint in lower for hint in ENCODER_NAME_HINTS)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def print_all_joysticks(self) -> None:
        """
        Print information about every joystick pygame can see.
        Useful for debugging when encoders are not detected.
        """
        if not pygame.joystick.get_init():
            pygame.joystick.init()

        total = pygame.joystick.get_count()
        print(f"[arcade_encoders] Total joysticks detected by pygame: {total}")
        for i in range(total):
            js = pygame.joystick.Joystick(i)
            js.init()
            print(
                f"  [{i}] name={js.get_name()!r}  "
                f"hats={js.get_numhats()}  "
                f"axes={js.get_numaxes()}  "
                f"buttons={js.get_numbuttons()}"
            )

    def __repr__(self) -> str:
        return f"<EncoderManager encoders={self._encoders!r}>"
