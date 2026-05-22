"""
encoder_device.py
-----------------
Wraps a single pygame.joystick.Joystick that represents one
Reyann Easyget Zero Delay USB Encoder.

Hardware layout (as seen by the OS / pygame on Linux)
------------------------------------------------------
The encoder uses the DragonRise chipset and is reported as:
  "DragonRise Inc.   Generic   USB  Joystick"

  Axes (primary input method on Linux):
    Axis 0 (X): LEFT  = -1.0,  RIGHT = +1.0,  idle ≈ -0.004
    Axis 1 (Y): UP    = -1.0,  DOWN  = +1.0,  idle ≈ -0.004

  Hat switch : always reports (0, 0) on this driver — not used.

  Buttons    : indices 0-7  (8 physical buttons, indices 0-11 reported
               but only 0-7 are wired to physical buttons)

Direction detection uses a threshold of ±0.5 on axes 0 and 1.

Unique identification
---------------------
Both Zero Delay encoders report the same USB GUID (identical chipset),
so the GUID alone cannot distinguish Player 1 from Player 2.

Instead we use the **USB physical port path** read from the Linux sysfs
filesystem (e.g. "2-1.3" or "3-2").  This path is stable across reboots
as long as the encoder stays plugged into the same physical USB port.

The path is resolved by following the symlink for /sys/class/input/jsN
and extracting the USB bus/port segment from the resolved path.
"""

import os
import re
import pygame


# ---------------------------------------------------------------------------
# Module-level helper: USB port path resolution (Linux sysfs)
# ---------------------------------------------------------------------------

def _get_usb_port_path(joystick_index: int) -> str:
    """
    Return the stable USB physical-port path for joystick index N.

    On Linux, /sys/class/input/jsN is a symlink whose resolved path contains
    the USB bus and port numbers, e.g.:
      /sys/devices/pci.../usb2/2-1/2-1.3/2-1.3:1.0/.../input/inputX/jsN

    We extract the segment that looks like "2-1.3" or "3-2" — the USB port
    path — which is stable across reboots for a given physical USB socket.

    Returns an empty string if the path cannot be determined (non-Linux,
    permission error, or unexpected sysfs layout).
    """
    sysfs_path = f"/sys/class/input/js{joystick_index}"
    try:
        resolved = os.path.realpath(sysfs_path)
        # The USB port segment looks like "2-1.3" or "3-2" — a digit, a dash,
        # then one or more dot-separated numbers.
        match = re.search(r'/(\d+-[\d.]+)/\d+-[\d.]+:\d+\.\d+/', resolved)
        if match:
            return match.group(1)
    except OSError:
        pass
    return ""


# Direction constants returned by get_direction()
DIR_NONE  = "none"
DIR_UP    = "up"
DIR_DOWN  = "down"
DIR_LEFT  = "left"
DIR_RIGHT = "right"

NUM_BUTTONS = 8


class EncoderDevice:
    """
    Represents one Zero Delay USB Encoder connected to the system.

    Parameters
    ----------
    joystick_index : int
        The pygame joystick index (0-based) for this encoder.
    label : str, optional
        A human-readable name, e.g. "Encoder 1".
    """

    def __init__(self, joystick_index: int, label: str = ""):
        self._index = joystick_index
        self.label = label or f"Encoder {joystick_index + 1}"

        self._joystick = pygame.joystick.Joystick(joystick_index)
        self._joystick.init()

        self._num_hats    = self._joystick.get_numhats()
        self._num_axes    = self._joystick.get_numaxes()
        self._num_buttons = self._joystick.get_numbuttons()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def pygame_index(self) -> int:
        """The pygame joystick index for this device."""
        return self._index

    @property
    def name(self) -> str:
        """The raw device name reported by pygame / the OS."""
        return self._joystick.get_name()

    @property
    def guid(self) -> str:
        """
        The SDL/pygame GUID for this joystick.

        NOTE: Both Zero Delay encoders share the same GUID because they use
        identical DragonRise chipsets.  Use usb_port_path for a stable,
        per-device identifier instead.
        """
        try:
            return self._joystick.get_guid()
        except AttributeError:
            return ""

    @property
    def usb_port_path(self) -> str:
        """
        The stable USB physical-port path for this encoder (Linux only).

        Reads the sysfs symlink for /sys/class/input/jsN and extracts the
        USB bus/port segment, e.g. "2-1.3" or "3-2".

        This value is the same every time the encoder is plugged into the
        same physical USB port, making it suitable as a persistent unique ID.

        Returns an empty string on non-Linux systems or if the path cannot
        be determined.
        """
        return _get_usb_port_path(self._index)

    # ------------------------------------------------------------------
    # Direction reading
    # ------------------------------------------------------------------

    def get_direction(self) -> str:
        """
        Return the current joystick direction as one of the DIR_* constants.

        Reads axis 0 (X) and axis 1 (Y) with a ±0.5 threshold.
        The DragonRise chipset used by this encoder reports axes only;
        the hat switch always reads (0, 0) and is intentionally ignored.

        Axis mapping:
          Axis 0 (X): LEFT = -1.0,  RIGHT = +1.0,  idle ≈ -0.004
          Axis 1 (Y): UP   = -1.0,  DOWN  = +1.0,  idle ≈ -0.004
        """
        if self._num_axes >= 2:
            ax = self._joystick.get_axis(0)
            ay = self._joystick.get_axis(1)
            # Y-axis checked first so diagonal presses prefer up/down
            if ay < -0.5:
                return DIR_UP
            if ay > 0.5:
                return DIR_DOWN
            if ax < -0.5:
                return DIR_LEFT
            if ax > 0.5:
                return DIR_RIGHT

        return DIR_NONE

    def is_direction(self, direction: str) -> bool:
        """Return True if the joystick is currently held in *direction*."""
        return self.get_direction() == direction

    # ------------------------------------------------------------------
    # Button reading
    # ------------------------------------------------------------------

    def get_button(self, button_index: int) -> bool:
        """
        Return True if the button at *button_index* (0-7) is currently pressed.

        Raises IndexError if button_index is out of range for this device.
        """
        if button_index < 0 or button_index >= self._num_buttons:
            raise IndexError(
                f"{self.label}: button index {button_index} out of range "
                f"(device has {self._num_buttons} buttons)"
            )
        return bool(self._joystick.get_button(button_index))

    def get_all_buttons(self) -> list:
        """
        Return a list of bool values for all buttons (indices 0 to N-1).
        """
        return [bool(self._joystick.get_button(i)) for i in range(self._num_buttons)]

    def any_button_pressed(self) -> bool:
        """Return True if any button is currently pressed."""
        return any(self.get_all_buttons())

    def first_pressed_button(self):
        """
        Return the index of the first button that is currently pressed,
        or None if no button is pressed.
        """
        for i in range(self._num_buttons):
            if self._joystick.get_button(i):
                return i
        return None

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def info(self) -> dict:
        """Return a dict with device diagnostics (useful for debugging)."""
        return {
            "label":         self.label,
            "name":          self.name,
            "index":         self._index,
            "guid":          self.guid,
            "usb_port_path": self.usb_port_path,
            "num_hats":      self._num_hats,
            "num_axes":      self._num_axes,
            "num_buttons":   self._num_buttons,
        }

    def __repr__(self) -> str:
        return (
            f"<EncoderDevice label={self.label!r} "
            f"name={self.name!r} index={self._index}>"
        )
