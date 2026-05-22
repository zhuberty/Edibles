"""
input_test.py
-------------
Guided input-test sequence for all connected Zero Delay USB Encoders.

The test walks the user through every input on every encoder in order:

  For each encoder (1, then 2, ...):
    1. Joystick UP
    2. Joystick DOWN
    3. Joystick LEFT
    4. Joystick RIGHT
    5. Button 1  (index 0)
    6. Button 2  (index 1)
    ...
    12. Button 8  (index 7)

The test renders a pygame window with clear on-screen instructions and
highlights each input as it is detected.  Once an input is confirmed the
test automatically advances to the next step.

This module is completely independent of the Edibles snake game.
"""

import pygame
from .encoder_device import (
    EncoderDevice,
    DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIR_NONE,
)
from .encoder_manager import EncoderManager


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
BLACK       = (  0,   0,   0)
WHITE       = (255, 255, 255)
DARK_GREY   = ( 30,  30,  30)
MID_GREY    = ( 80,  80,  80)
LIGHT_GREY  = (180, 180, 180)
GREEN       = ( 50, 220,  80)
YELLOW      = (255, 220,  40)
CYAN        = ( 40, 220, 220)
RED         = (220,  50,  50)
ORANGE      = (255, 150,  44)

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------
WINDOW_W    = 700
WINDOW_H    = 520
FPS         = 60

# Joystick visualisation
JOY_CX      = WINDOW_W // 2        # centre-x of the joystick diagram
JOY_CY      = 200                  # centre-y
JOY_RADIUS  = 50                   # outer circle radius
ARROW_LEN   = 36                   # length of direction arrows

# Button grid
BTN_COLS    = 4
BTN_SIZE    = 64
BTN_GAP     = 16
BTN_GRID_TOP = 330


def _build_steps(encoder: EncoderDevice) -> list:
    """
    Build the ordered list of test steps for one encoder.

    Each step is a dict:
        kind        : "direction" | "button"
        label       : human-readable name shown on screen
        check       : callable(encoder) -> bool  (True = step passed)
        release     : callable(encoder) -> bool  (True = input released, ready for next)
    """
    steps = []

    # --- Joystick directions ---
    for direction, name in [
        (DIR_UP,    "UP"),
        (DIR_DOWN,  "DOWN"),
        (DIR_LEFT,  "LEFT"),
        (DIR_RIGHT, "RIGHT"),
    ]:
        d = direction  # capture loop variable
        steps.append({
            "kind":    "direction",
            "label":   f"Push joystick {name}",
            "dir":     d,
            "check":   lambda enc, _d=d: enc.get_direction() == _d,
            "release": lambda enc: enc.get_direction() == DIR_NONE,
        })

    # --- Buttons ---
    for btn_idx in range(8):
        b = btn_idx  # capture loop variable
        steps.append({
            "kind":    "button",
            "label":   f"Press Button {btn_idx + 1}",
            "btn":     b,
            "check":   lambda enc, _b=b: enc.get_button(_b),
            "release": lambda enc, _b=b: not enc.get_button(_b),
        })

    return steps


class InputTest:
    """
    Runs a full guided input test for all encoders managed by *manager*.

    Parameters
    ----------
    manager : EncoderManager
        An already-initialised EncoderManager.
    window_title : str
        Title shown in the pygame window title bar.
    """

    def __init__(self, manager: EncoderManager, window_title: str = "Arcade Encoder Input Test"):
        self._manager = manager
        self._window_title = window_title

        # State machine
        self._enc_idx   = 0   # which encoder we are currently testing
        self._step_idx  = 0   # which step within that encoder's list
        self._waiting_release = False   # True after a step passes, waiting for release
        self._all_done  = False

        # Per-encoder step lists (built lazily in run())
        self._step_lists: list[list] = []

        # Pygame objects (created in run())
        self._screen = None
        self._clock  = None
        self._font_large  = None
        self._font_medium = None
        self._font_small  = None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> bool:
        """
        Open a pygame window and run the interactive test.

        Returns True if all inputs were confirmed, False if the user
        closed the window or pressed Escape before finishing.
        """
        if self._manager.count == 0:
            print("[InputTest] No encoders available – aborting test.")
            return False

        # Build step lists for every encoder
        self._step_lists = [
            _build_steps(enc) for enc in self._manager.encoders
        ]
        self._enc_idx  = 0
        self._step_idx = 0
        self._waiting_release = False
        self._all_done = False

        # Set up display
        self._screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption(self._window_title)

        self._clock = pygame.time.Clock()

        # Fonts – fall back to the default pygame font if the custom one
        # is not available in this standalone context.
        try:
            self._font_large  = pygame.font.Font("fonts/Condition.ttf", 36)
            self._font_medium = pygame.font.Font("fonts/Condition.ttf", 24)
            self._font_small  = pygame.font.Font("fonts/Condition.ttf", 18)
        except FileNotFoundError:
            self._font_large  = pygame.font.SysFont(None, 42)
            self._font_medium = pygame.font.SysFont(None, 28)
            self._font_small  = pygame.font.SysFont(None, 22)

        running = True
        while running:
            self._clock.tick(FPS)

            # --- Event handling ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            if self._all_done:
                self._draw_done()
                pygame.display.flip()
                # Wait a moment then exit
                pygame.time.wait(2500)
                break

            # --- Update state machine ---
            self._update()

            # --- Draw ---
            self._draw()
            pygame.display.flip()

        return self._all_done

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def _update(self) -> None:
        """Advance the test state based on current encoder input."""
        # Pump events so joystick state is fresh
        pygame.event.pump()

        enc   = self._manager.get_encoder(self._enc_idx)
        steps = self._step_lists[self._enc_idx]
        step  = steps[self._step_idx]

        if self._waiting_release:
            # Wait until the user releases the input before moving on
            if step["release"](enc):
                self._waiting_release = False
                self._advance()
        else:
            # Check if the required input is active
            if step["check"](enc):
                self._waiting_release = True

    def _advance(self) -> None:
        """Move to the next step, or the next encoder, or finish."""
        steps = self._step_lists[self._enc_idx]
        self._step_idx += 1

        if self._step_idx >= len(steps):
            # Finished all steps for this encoder
            self._step_idx = 0
            self._enc_idx += 1

            if self._enc_idx >= self._manager.count:
                self._all_done = True

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        self._screen.fill(DARK_GREY)

        if self._enc_idx >= self._manager.count:
            return

        enc   = self._manager.get_encoder(self._enc_idx)
        steps = self._step_lists[self._enc_idx]
        step  = steps[self._step_idx]

        # --- Header ---
        self._draw_header(enc)

        # --- Progress bar ---
        total_steps = sum(len(sl) for sl in self._step_lists)
        done_steps  = (
            sum(len(self._step_lists[i]) for i in range(self._enc_idx))
            + self._step_idx
        )
        self._draw_progress(done_steps, total_steps)

        # --- Instruction ---
        self._draw_instruction(step)

        # --- Joystick diagram ---
        direction = enc.get_direction()
        self._draw_joystick(direction, step)

        # --- Button grid ---
        buttons = enc.get_all_buttons()
        self._draw_buttons(buttons, step)

    def _draw_header(self, enc: EncoderDevice) -> None:
        title_surf = self._font_large.render(
            f"Testing: {enc.label}  ({enc.name})", True, CYAN
        )
        self._screen.blit(title_surf, (20, 16))

        sub_surf = self._font_small.render(
            "Press ESC to quit  |  Each input must be pressed then released",
            True, LIGHT_GREY
        )
        self._screen.blit(sub_surf, (20, 58))

    def _draw_progress(self, done: int, total: int) -> None:
        bar_x, bar_y = 20, 88
        bar_w, bar_h = WINDOW_W - 40, 10
        pygame.draw.rect(self._screen, MID_GREY, (bar_x, bar_y, bar_w, bar_h), border_radius=5)
        if total > 0:
            fill_w = int(bar_w * done / total)
            pygame.draw.rect(self._screen, GREEN, (bar_x, bar_y, fill_w, bar_h), border_radius=5)

        pct_surf = self._font_small.render(f"{done}/{total} inputs confirmed", True, LIGHT_GREY)
        self._screen.blit(pct_surf, (bar_x, bar_y + 14))

    def _draw_instruction(self, step: dict) -> None:
        colour = YELLOW if not self._waiting_release else GREEN
        label  = step["label"] if not self._waiting_release else f"✓  {step['label']}  — now release"
        surf   = self._font_medium.render(label, True, colour)
        rect   = surf.get_rect(centerx=WINDOW_W // 2, centery=130)
        self._screen.blit(surf, rect)

    def _draw_joystick(self, direction: str, step: dict) -> None:
        """Draw a simple joystick diagram with the active direction highlighted."""
        cx, cy = JOY_CX, JOY_CY

        # Outer ring
        pygame.draw.circle(self._screen, MID_GREY, (cx, cy), JOY_RADIUS, 3)

        # Cross-hair lines
        pygame.draw.line(self._screen, MID_GREY, (cx - JOY_RADIUS, cy), (cx + JOY_RADIUS, cy), 1)
        pygame.draw.line(self._screen, MID_GREY, (cx, cy - JOY_RADIUS), (cx, cy + JOY_RADIUS), 1)

        # Direction arrows
        arrow_defs = {
            DIR_UP:    (cx,              cy - ARROW_LEN, "UP"),
            DIR_DOWN:  (cx,              cy + ARROW_LEN, "DOWN"),
            DIR_LEFT:  (cx - ARROW_LEN,  cy,             "LEFT"),
            DIR_RIGHT: (cx + ARROW_LEN,  cy,             "RIGHT"),
        }

        for d, (ax, ay, dlabel) in arrow_defs.items():
            is_target  = (step["kind"] == "direction" and step["dir"] == d)
            is_active  = (direction == d)

            if is_active and is_target:
                colour = GREEN if self._waiting_release else YELLOW
            elif is_active:
                colour = ORANGE
            elif is_target:
                colour = WHITE
            else:
                colour = MID_GREY

            pygame.draw.line(self._screen, colour, (cx, cy), (ax, ay), 3)
            # Arrowhead dot
            pygame.draw.circle(self._screen, colour, (ax, ay), 6)

            lbl_surf = self._font_small.render(dlabel, True, colour)
            offset_x = ax - cx
            offset_y = ay - cy
            lbl_x = ax + (12 if offset_x > 0 else (-12 - lbl_surf.get_width() if offset_x < 0 else -lbl_surf.get_width() // 2))
            lbl_y = ay + (10 if offset_y > 0 else -24)
            self._screen.blit(lbl_surf, (lbl_x, lbl_y))

        # Centre dot
        pygame.draw.circle(self._screen, WHITE, (cx, cy), 6)

    def _draw_buttons(self, buttons: list, step: dict) -> None:
        """Draw an 8-button grid with the target button highlighted."""
        total_w = BTN_COLS * BTN_SIZE + (BTN_COLS - 1) * BTN_GAP
        start_x = (WINDOW_W - total_w) // 2

        for i in range(8):
            col = i % BTN_COLS
            row = i // BTN_COLS
            bx  = start_x + col * (BTN_SIZE + BTN_GAP)
            by  = BTN_GRID_TOP + row * (BTN_SIZE + BTN_GAP)

            is_target  = (step["kind"] == "button" and step["btn"] == i)
            is_pressed = buttons[i] if i < len(buttons) else False

            if is_pressed and is_target:
                bg_colour  = GREEN if self._waiting_release else YELLOW
                txt_colour = BLACK
            elif is_pressed:
                bg_colour  = ORANGE
                txt_colour = BLACK
            elif is_target:
                bg_colour  = MID_GREY
                txt_colour = WHITE
            else:
                bg_colour  = (20, 20, 20)
                txt_colour = MID_GREY

            pygame.draw.rect(self._screen, bg_colour,
                             (bx, by, BTN_SIZE, BTN_SIZE), border_radius=10)
            if not is_pressed:
                pygame.draw.rect(self._screen, MID_GREY,
                                 (bx, by, BTN_SIZE, BTN_SIZE), 2, border_radius=10)

            lbl = self._font_medium.render(str(i + 1), True, txt_colour)
            lbl_rect = lbl.get_rect(center=(bx + BTN_SIZE // 2, by + BTN_SIZE // 2))
            self._screen.blit(lbl, lbl_rect)

    def _draw_done(self) -> None:
        self._screen.fill(DARK_GREY)
        msg1 = self._font_large.render("All inputs confirmed!", True, GREEN)
        msg2 = self._font_medium.render(
            f"Both encoders passed the test  ({self._manager.count} device(s))",
            True, WHITE
        )
        msg3 = self._font_small.render("Window will close automatically…", True, LIGHT_GREY)

        self._screen.blit(msg1, msg1.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2 - 50)))
        self._screen.blit(msg2, msg2.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2 + 10)))
        self._screen.blit(msg3, msg3.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2 + 50)))
