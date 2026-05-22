"""
diagnose.py
-----------
Prints raw joystick data (hats, axes, buttons) for all connected devices.
Move the joystick in all directions and press buttons while this runs.

Run with:
    python -m arcade_encoders.diagnose
  or:
    python arcade_encoders/diagnose.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

def main():
    pygame.init()
    pygame.joystick.init()

    count = pygame.joystick.get_count()
    print(f"Joysticks found: {count}")
    if count == 0:
        print("No joysticks detected. Exiting.")
        pygame.quit()
        sys.exit(1)

    joysticks = []
    for i in range(count):
        js = pygame.joystick.Joystick(i)
        js.init()
        joysticks.append(js)
        print(f"  [{i}] {js.get_name()!r}  hats={js.get_numhats()}  axes={js.get_numaxes()}  buttons={js.get_numbuttons()}")

    print("\nReading input — move joystick and press buttons. Press Ctrl+C to quit.\n")

    # Headless loop (no display needed)
    try:
        while True:
            pygame.event.pump()
            for js in joysticks:
                hats    = [js.get_hat(h)   for h in range(js.get_numhats())]
                axes    = [round(js.get_axis(a), 3) for a in range(js.get_numaxes())]
                buttons = [js.get_button(b) for b in range(js.get_numbuttons())]

                # Only print when something is non-zero / non-idle
                hat_active = any(h != (0, 0) for h in hats)
                axis_active = any(abs(a) > 0.05 for a in axes)
                btn_active  = any(buttons)

                if hat_active or axis_active or btn_active:
                    print(
                        f"[{js.get_name()!r}]  "
                        f"hats={hats}  "
                        f"axes={axes}  "
                        f"buttons={[i for i,b in enumerate(buttons) if b]}"
                    )

            pygame.time.wait(50)   # ~20 Hz polling

    except KeyboardInterrupt:
        print("\nDone.")
        pygame.quit()

if __name__ == "__main__":
    main()
