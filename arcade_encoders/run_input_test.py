"""
run_input_test.py
-----------------
Standalone entry point for the Arcade Encoder Input Test.

Run from the project root:

    python -m arcade_encoders.run_input_test

  or directly:

    python arcade_encoders/run_input_test.py

The script will:
  1. Initialise pygame.
  2. List every joystick pygame can see (for diagnostics).
  3. Discover all connected Zero Delay USB Encoders.
  4. Launch the guided input-test window.

If your encoders are not detected automatically (strict_filter=True),
the script will fall back to treating ALL joysticks as encoders so the
test can still run.  You can also pass --no-filter on the command line
to force this behaviour.

Command-line flags
------------------
  --no-filter     Treat every joystick as an encoder (skip name matching).
  --help / -h     Show this help text and exit.
"""

import sys
import os

# Allow running as a plain script from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
from arcade_encoders import EncoderManager, InputTest


def main():
    # --- Parse minimal CLI flags ---
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    strict_filter = "--no-filter" not in args

    # --- Initialise pygame ---
    pygame.init()
    pygame.joystick.init()

    # --- Discover encoders ---
    manager = EncoderManager(strict_filter=strict_filter)

    print("\n=== Arcade Encoder Input Test ===")
    print("Scanning for joystick devices…\n")
    manager.print_all_joysticks()
    print()

    manager.init()

    # Fallback: if strict filter found nothing, retry without it
    if manager.count == 0 and strict_filter:
        print(
            "\n[run_input_test] No encoders matched the name filter.\n"
            "Retrying with --no-filter (all joysticks treated as encoders)…\n"
        )
        manager = EncoderManager(strict_filter=False)
        manager.init()

    if manager.count == 0:
        print(
            "\n[run_input_test] ERROR: No joystick devices found at all.\n"
            "Please connect your USB encoders and try again."
        )
        pygame.quit()
        sys.exit(1)

    print(f"\n{manager.count} encoder(s) ready for testing.\n")
    for enc in manager.encoders:
        info = enc.info()
        print(
            f"  {enc.label}: {enc.name!r}  "
            f"hats={info['num_hats']}  "
            f"axes={info['num_axes']}  "
            f"buttons={info['num_buttons']}"
        )

    print(
        "\nStarting input test…\n"
        "  • Follow the on-screen instructions.\n"
        "  • Each input must be pressed AND released to advance.\n"
        "  • Press ESC or close the window to quit early.\n"
    )

    # --- Run the test ---
    test = InputTest(manager, window_title="Arcade Encoder Input Test")
    passed = test.run()

    # --- Result ---
    pygame.quit()
    if passed:
        print("\n✓  All inputs confirmed — encoders are working correctly!")
        sys.exit(0)
    else:
        print("\n✗  Test was not completed (window closed or ESC pressed).")
        sys.exit(1)


if __name__ == "__main__":
    main()
