"""
encoder_setup.py
----------------
One-time interactive setup that assigns Player 1 and Player 2 to specific
physical USB encoder boards and saves the mapping to a config file.

WHY THIS IS NEEDED
------------------
Both Zero Delay USB Encoders use the same DragonRise chipset and therefore
report an identical USB GUID.  The only reliable way to tell them apart is
by the physical USB port they are plugged into (read from the Linux sysfs
path, e.g. "2-1.3" vs "3-2").

This script records which USB port path belongs to Player 1 and which
belongs to Player 2, saving the result to:

    arcade_encoders/encoder_player_map.json

EncoderManager reads that file on startup and labels each encoder
"Player 1" or "Player 2" accordingly.

USAGE
-----
Run once from the project root whenever you want to (re-)assign players:

    python -m arcade_encoders.encoder_setup

  or directly:

    python arcade_encoders/encoder_setup.py

WHAT IT DOES
------------
  1. Discovers all connected encoders.
  2. Displays a pygame window prompting the Player 1 person to press ANY
     button on their controller.
  3. Whichever encoder fires first is saved as Player 1.
  4. Repeats for Player 2.
  5. Writes arcade_encoders/encoder_player_map.json with the USB port paths.
"""

import sys
import os
import json
import time

# Allow running as a plain script from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

# NOTE: EncoderManager and EncoderDevice are imported lazily (inside functions
# and classes) to avoid a circular import.  The import chain is:
#   __init__ → encoder_manager → encoder_setup (load_player_map)
# Importing EncoderManager at module level here would close the circle.

# ---------------------------------------------------------------------------
# Config file location — sits next to this module so it travels with the code
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_HERE, "encoder_player_map.json")

# ---------------------------------------------------------------------------
# Colour palette (matches input_test.py for visual consistency)
# ---------------------------------------------------------------------------
BLACK      = (  0,   0,   0)
DARK_GREY  = ( 30,  30,  30)
MID_GREY   = ( 80,  80,  80)
LIGHT_GREY = (180, 180, 180)
WHITE      = (255, 255, 255)
GREEN      = ( 50, 220,  80)
YELLOW     = (255, 220,  40)
CYAN       = ( 40, 220, 220)
ORANGE     = (255, 150,  44)
RED        = (220,  50,  50)

WINDOW_W = 700
WINDOW_H = 400
FPS      = 60


# ---------------------------------------------------------------------------
# Public helpers — used by EncoderManager
# ---------------------------------------------------------------------------

def load_player_map() -> dict:
    """
    Load the saved player→USB-port-path mapping from disk.

    Returns a dict like::

        {
            "player1": "2-1.3",
            "player2": "3-2"
        }

    Returns an empty dict if the config file does not exist or is invalid.
    """
    if not os.path.isfile(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
        # Basic validation
        if isinstance(data, dict) and "player1" in data and "player2" in data:
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_player_map(player1_usb_path: str, player2_usb_path: str) -> None:
    """
    Persist the player→USB-port-path mapping to disk.

    Parameters
    ----------
    player1_usb_path : str
        The USB port path (e.g. "2-1.3") for the Player 1 encoder.
    player2_usb_path : str
        The USB port path (e.g. "3-2") for the Player 2 encoder.
    """
    data = {
        "player1": player1_usb_path,
        "player2": player2_usb_path,
        "_note": (
            "Maps player numbers to USB physical port paths. "
            "Keep each encoder in the same USB port to preserve this mapping. "
            "Re-run encoder_setup.py if you swap ports."
        ),
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[encoder_setup] Config saved to: {CONFIG_PATH}")


# ---------------------------------------------------------------------------
# Interactive setup — pygame window
# ---------------------------------------------------------------------------

class EncoderSetup:
    """
    Interactive pygame-based setup wizard.

    Prompts each player to press any button on their encoder, records which
    physical USB port responded, and saves the mapping.

    Parameters
    ----------
    manager : EncoderManager
        An already-initialised EncoderManager with at least 2 encoders.
    """

    def __init__(self, manager):
        self._manager = manager

        self._screen = None
        self._clock  = None
        self._font_large  = None
        self._font_medium = None
        self._font_small  = None

        # Results (EncoderDevice instances, or None)
        self._player1_enc = None
        self._player2_enc = None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> bool:
        """
        Open a pygame window and run the interactive setup.

        Returns True if both players were successfully assigned and the
        config was saved.  Returns False if the user quit early.
        """
        if self._manager.count < 2:
            print(
                f"[encoder_setup] ERROR: Need at least 2 encoders, "
                f"found {self._manager.count}."
            )
            return False

        # Set up display
        self._screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("Arcade Encoder Setup — Player Assignment")

        self._clock = pygame.time.Clock()

        try:
            self._font_large  = pygame.font.Font("fonts/Condition.ttf", 36)
            self._font_medium = pygame.font.Font("fonts/Condition.ttf", 24)
            self._font_small  = pygame.font.Font("fonts/Condition.ttf", 18)
        except FileNotFoundError:
            self._font_large  = pygame.font.SysFont(None, 42)
            self._font_medium = pygame.font.SysFont(None, 28)
            self._font_small  = pygame.font.SysFont(None, 22)

        # --- Step 1: assign Player 1 ---
        result = self._wait_for_press(
            player_number=1,
            exclude=None,
        )
        if result is None:
            return False
        self._player1_enc = result

        # Brief pause so the button-release doesn't bleed into step 2
        self._wait_for_release(self._player1_enc)

        # --- Step 2: assign Player 2 ---
        result = self._wait_for_press(
            player_number=2,
            exclude=self._player1_enc,
        )
        if result is None:
            return False
        self._player2_enc = result

        # --- Show confirmation and save ---
        self._draw_confirmation()
        pygame.display.flip()
        pygame.time.wait(2500)

        save_player_map(
            player1_usb_path=self._player1_enc.usb_port_path,
            player2_usb_path=self._player2_enc.usb_port_path,
        )
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _wait_for_press(self, player_number: int, exclude):
        """
        Poll all encoders until one (other than *exclude*) has a button pressed.

        Returns the EncoderDevice that fired, or None if the user quit.
        """
        while True:
            self._clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return None

            pygame.event.pump()

            # Draw the prompt
            self._draw_prompt(player_number, exclude)
            pygame.display.flip()

            # Check each encoder for a button press
            for enc in self._manager.encoders:
                if exclude is not None and enc.pygame_index == exclude.pygame_index:
                    continue
                if enc.any_button_pressed():
                    return enc

    def _wait_for_release(self, enc) -> None:
        """Wait until all buttons on *enc* are released (debounce)."""
        deadline = time.monotonic() + 2.0  # safety timeout
        while time.monotonic() < deadline:
            pygame.event.pump()
            if not enc.any_button_pressed():
                break
            self._clock.tick(FPS)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw_prompt(self, player_number: int, exclude) -> None:
        self._screen.fill(DARK_GREY)

        # Title
        title = self._font_large.render(
            "Arcade Encoder Setup", True, CYAN
        )
        self._screen.blit(title, title.get_rect(centerx=WINDOW_W // 2, centery=50))

        # Sub-title
        sub = self._font_small.render(
            "Press ESC or close the window to cancel",
            True, LIGHT_GREY,
        )
        self._screen.blit(sub, sub.get_rect(centerx=WINDOW_W // 2, centery=90))

        # Divider
        pygame.draw.line(self._screen, MID_GREY, (40, 110), (WINDOW_W - 40, 110), 1)

        # Main instruction
        colour = YELLOW if player_number == 1 else GREEN
        player_label = f"PLAYER {player_number}"
        msg = self._font_large.render(
            f"Press any button on the  {player_label}  controller",
            True, colour,
        )
        self._screen.blit(msg, msg.get_rect(centerx=WINDOW_W // 2, centery=180))

        # Show already-assigned encoder (if any)
        if exclude is not None:
            done_colour = YELLOW
            done_text = (
                f"✓  Player 1 assigned  "
                f"(USB port: {exclude.usb_port_path or 'unknown'})"
            )
            done_surf = self._font_small.render(done_text, True, done_colour)
            self._screen.blit(
                done_surf,
                done_surf.get_rect(centerx=WINDOW_W // 2, centery=260),
            )

        # List all detected encoders at the bottom
        hint = self._font_small.render(
            f"{self._manager.count} encoder(s) detected", True, LIGHT_GREY
        )
        self._screen.blit(hint, hint.get_rect(centerx=WINDOW_W // 2, centery=320))

        for i, enc in enumerate(self._manager.encoders):
            port = enc.usb_port_path or "unknown"
            is_excluded = (exclude is not None and enc.pygame_index == exclude.pygame_index)
            colour = MID_GREY if is_excluded else LIGHT_GREY
            line = self._font_small.render(
                f"  Encoder {i + 1}: USB port {port}  ({enc.name})",
                True, colour,
            )
            self._screen.blit(
                line,
                line.get_rect(centerx=WINDOW_W // 2, centery=345 + i * 24),
            )

    def _draw_confirmation(self) -> None:
        self._screen.fill(DARK_GREY)

        title = self._font_large.render("Setup Complete!", True, GREEN)
        self._screen.blit(title, title.get_rect(centerx=WINDOW_W // 2, centery=100))

        p1_port = self._player1_enc.usb_port_path if self._player1_enc else "?"
        p2_port = self._player2_enc.usb_port_path if self._player2_enc else "?"

        p1_surf = self._font_medium.render(
            f"Player 1  →  USB port {p1_port}", True, YELLOW
        )
        p2_surf = self._font_medium.render(
            f"Player 2  →  USB port {p2_port}", True, GREEN
        )
        note_surf = self._font_small.render(
            "Keep each encoder in the same USB port to preserve this mapping.",
            True, LIGHT_GREY,
        )
        saved_surf = self._font_small.render(
            f"Saved to: {CONFIG_PATH}", True, LIGHT_GREY
        )

        self._screen.blit(p1_surf, p1_surf.get_rect(centerx=WINDOW_W // 2, centery=190))
        self._screen.blit(p2_surf, p2_surf.get_rect(centerx=WINDOW_W // 2, centery=230))
        self._screen.blit(note_surf, note_surf.get_rect(centerx=WINDOW_W // 2, centery=300))
        self._screen.blit(saved_surf, saved_surf.get_rect(centerx=WINDOW_W // 2, centery=330))


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    strict_filter = "--no-filter" not in args

    print("\n=== Arcade Encoder Setup — Player Assignment ===\n")

    pygame.init()
    pygame.joystick.init()

    # Lazy import here to avoid the circular dependency at module load time.
    # By the time main() is called, all modules are fully initialised.
    from arcade_encoders.encoder_manager import EncoderManager  # noqa: PLC0415

    manager = EncoderManager(strict_filter=strict_filter)

    print("Scanning for joystick devices…\n")
    manager.print_all_joysticks()
    print()
    manager.init()

    # Fallback: retry without strict filter if nothing found
    if manager.count == 0 and strict_filter:
        print(
            "[encoder_setup] No encoders matched the name filter.\n"
            "Retrying with --no-filter (all joysticks treated as encoders)…\n"
        )
        manager = EncoderManager(strict_filter=False)
        manager.init()

    if manager.count == 0:
        print(
            "[encoder_setup] ERROR: No joystick devices found.\n"
            "Please connect your USB encoders and try again."
        )
        pygame.quit()
        sys.exit(1)

    if manager.count < 2:
        print(
            f"[encoder_setup] WARNING: Only {manager.count} encoder found.\n"
            "Two encoders are required for player assignment.\n"
            "Connect both encoders and try again."
        )
        pygame.quit()
        sys.exit(1)

    print(f"{manager.count} encoder(s) ready.\n")
    for enc in manager.encoders:
        info = enc.info()
        print(
            f"  Encoder {enc.pygame_index + 1}: "
            f"name={enc.name!r}  "
            f"usb_port={info['usb_port_path'] or 'unknown'}  "
            f"guid={info['guid']}"
        )

    print(
        "\nStarting player-assignment wizard…\n"
        "  • When prompted, press ANY button on the correct controller.\n"
        "  • Press ESC or close the window to cancel.\n"
    )

    setup = EncoderSetup(manager)
    success = setup.run()

    pygame.quit()

    if success:
        print("\n✓  Player assignment saved successfully!")
        print(f"   Config file: {CONFIG_PATH}")
        sys.exit(0)
    else:
        print("\n✗  Setup was cancelled — no changes saved.")
        sys.exit(1)


if __name__ == "__main__":
    main()
