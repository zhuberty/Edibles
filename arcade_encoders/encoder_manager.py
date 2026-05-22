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

Player assignment
-----------------
Because both encoders share the same USB GUID (identical DragonRise
chipset), EncoderManager uses the saved player map from
encoder_player_map.json (written by encoder_setup.py) to label each
device "Player 1" or "Player 2" based on its physical USB port path.

If no config file exists the encoders are labelled in discovery order
("Encoder 1", "Encoder 2") and a warning is printed.

Usage
-----
    manager = EncoderManager()
    manager.init()

    player1 = manager.get_player(1)   # encoder assigned to Player 1
    player2 = manager.get_player(2)   # encoder assigned to Player 2

    direction = player1.get_direction()
    buttons   = player1.get_all_buttons()
"""

import pygame
from .encoder_device import EncoderDevice
from .encoder_setup import load_player_map


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

        # player_number (1 or 2) → EncoderDevice
        self._player_map: dict[int, EncoderDevice] = {}

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def init(self) -> None:
        """
        Initialise pygame's joystick subsystem, discover all encoders, and
        apply the saved player assignment (if available).

        Call this once after pygame.init() has been called.
        """
        if not pygame.joystick.get_init():
            pygame.joystick.init()

        self._encoders.clear()
        self._player_map.clear()
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

        # Apply player assignment from saved config
        self._apply_player_map()

    def _apply_player_map(self) -> None:
        """
        Load encoder_player_map.json and assign player labels to encoders.

        Matches each encoder's USB port path against the saved mapping.
        If the config is missing or a port path is not found, falls back to
        discovery order and prints a warning.
        """
        saved = load_player_map()

        if not saved:
            print(
                "[arcade_encoders] No player map found. "
                "Run 'python -m arcade_encoders.encoder_setup' to assign "
                "Player 1 and Player 2 to specific controllers."
            )
            # Fall back: assign in discovery order
            for i, enc in enumerate(self._encoders):
                player_num = i + 1
                enc.label = f"Player {player_num}"
                self._player_map[player_num] = enc
            return

        p1_port = saved.get("player1", "")
        p2_port = saved.get("player2", "")

        assigned = {}  # port_path → player_number
        if p1_port:
            assigned[p1_port] = 1
        if p2_port:
            assigned[p2_port] = 2

        unmatched = []
        for enc in self._encoders:
            port = enc.usb_port_path
            if port in assigned:
                player_num = assigned[port]
                enc.label = f"Player {player_num}"
                self._player_map[player_num] = enc
                print(
                    f"[arcade_encoders] {enc.label} ← USB port {port}"
                )
            else:
                unmatched.append(enc)

        if unmatched:
            print(
                "[arcade_encoders] WARNING: Some encoders could not be matched "
                "to the saved player map (USB port changed?):\n"
                + "\n".join(
                    f"  {enc.name!r} at USB port {enc.usb_port_path or 'unknown'}"
                    for enc in unmatched
                )
                + "\n  Re-run 'python -m arcade_encoders.encoder_setup' to fix."
            )

    # ------------------------------------------------------------------
    # Access by discovery order
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

    # ------------------------------------------------------------------
    # Access by player number
    # ------------------------------------------------------------------

    def get_player(self, player_number: int) -> EncoderDevice:
        """
        Return the encoder assigned to *player_number* (1 or 2).

        Uses the saved player map from encoder_player_map.json.
        Falls back to discovery order if no map is available.

        Raises KeyError if the player number has no assigned encoder.
        """
        if player_number not in self._player_map:
            raise KeyError(
                f"No encoder assigned to Player {player_number}. "
                f"Run 'python -m arcade_encoders.encoder_setup' to set up "
                f"player assignments."
            )
        return self._player_map[player_number]

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
