# Edibles
A two-player snake game with arcade joystick support via Zero Delay USB Encoders.

---

## Hardware

The game supports **Reyann Easyget Zero Delay USB Encoders** (DragonRise chipset).
Each encoder provides:
- 1 joystick (up / down / left / right)
- 8 buttons

Both encoders report the **same USB GUID** because they use identical chipsets.
The game identifies them by their **physical USB port** (stable across reboots),
so keep each encoder plugged into the same USB port after setup.

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up player assignments *(run once)*

This step tells the game which physical controller belongs to Player 1 and
which belongs to Player 2.

```bash
python -m arcade_encoders.encoder_setup
```

A window will appear with on-screen instructions:

1. **Player 1** — press any button on the Player 1 controller.
2. **Player 2** — press any button on the Player 2 controller.
3. The mapping is saved to `arcade_encoders/encoder_player_map.json`.

> **Re-run this any time you swap USB ports or want to reassign players.**

### 3. Test the encoders *(optional but recommended)*

Verify that all joystick directions and buttons are working correctly:

```bash
python -m arcade_encoders.run_input_test
```

Follow the on-screen prompts — each input must be pressed and released to advance.

### 4. Run the game

```bash
python Runner.py
```

---

## Encoder Tools Reference

| Command | Description |
|---|---|
| `python -m arcade_encoders.encoder_setup` | **One-time setup** — assign Player 1 & Player 2 to specific controllers |
| `python -m arcade_encoders.run_input_test` | Guided test of all joystick directions and buttons |
| `python -m arcade_encoders.diagnose` | Raw joystick data dump (headless, for debugging) |

---

## How Player Assignment Works

Both Zero Delay encoders use the same DragonRise chipset and therefore report
an **identical USB GUID** — the GUID alone cannot tell them apart.

Instead, the setup script reads the **Linux sysfs USB port path**
(e.g. `2-1.3` or `3-2`) for each joystick device. This path is determined by
which physical USB socket the encoder is plugged into, and it remains stable
across reboots.

The mapping is saved to `arcade_encoders/encoder_player_map.json`:

```json
{
  "player1": "2-1.3",
  "player2": "3-2"
}
```

This file is **machine-specific** and is excluded from version control
(listed in `.gitignore`). Each machine running the game needs to run
`encoder_setup` once.

When `EncoderManager.init()` is called at game startup, it reads this file
and labels each encoder `"Player 1"` or `"Player 2"` accordingly. If the file
is missing, encoders are assigned in USB discovery order with a warning.

---

## arcade_encoders Module API

```python
from arcade_encoders import EncoderManager, EncoderSetup

# Initialise (call after pygame.init())
manager = EncoderManager()
manager.init()

# Get encoders by player number (requires encoder_setup to have been run)
player1 = manager.get_player(1)
player2 = manager.get_player(2)

# Read input
direction = player1.get_direction()   # "up" | "down" | "left" | "right" | "none"
buttons   = player1.get_all_buttons() # list of 8 bools

# Each EncoderDevice also exposes:
player1.usb_port_path   # e.g. "2-1.3"  — stable USB port identifier
player1.guid            # SDL GUID (same for both encoders — not unique)
player1.info()          # dict of all diagnostics
```

---

## Troubleshooting

**Encoders not detected automatically**

Run the input test with `--no-filter` to bypass the name-matching filter:

```bash
python -m arcade_encoders.run_input_test --no-filter
```

**Player assignment is wrong after moving USB cables**

Re-run setup:

```bash
python -m arcade_encoders.encoder_setup
```

**Only one encoder found**

Make sure both USB cables are fully seated. Run the diagnose tool to see
what the OS reports:

```bash
python -m arcade_encoders.diagnose
```
