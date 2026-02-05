# WSR - Wayland Session Recorder

A modern Python rebuild of `xsr` for Wayland environments. WSR records user actions (clicks, keystrokes) and generates an illustrated HTML report.

## Features

- **Global Input Tracking:** Captures mouse movements, clicks, and keystrokes via `/dev/input/`.
- **Multi-Monitor Support:** Automatically detects the active monitor and takes screenshots only on that display.
- **Keystroke Grouping:** Combines rapid keystrokes into readable text blocks.
- **Screenshot Engine:** Automatic screenshots on mouse clicks (supports `grim` for wlroots/Hyprland and `gnome-screenshot`).
- **Cursor Overlay:** Draws the mouse cursor at the correct position in the screenshot.
- **Privacy Mode:** Use `--no-keys` to exclude keyboard input from the log.
- **Portable HTML Report:** Generates a single HTML file with embedded Base64 images.
- **Internationalization:** Supports English and German locales.

## Requirements

- **Linux** with Wayland.
- **Screenshot Tool:**
  - For Hyprland/Sway: `grim` (recommended)
  - For GNOME: `gnome-screenshot`
- **Permissions:** Access to `/dev/input/` (see below).

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/wsr.git
cd wsr

# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

### Arch Linux (AUR)

```bash
# Using PKGBUILD
makepkg -si
```

## Usage

```bash
# Basic start (3 second countdown)
sudo -E wsr -o my_report.html

# Without key logging (clicks & screenshots only)
sudo -E wsr --no-keys

# Adjust key interval (e.g., 800ms instead of 500ms)
sudo -E wsr --key-interval 800

# Show help
wsr --help
```

## Multi-Monitor Support

WSR supports automatic mapping of clicks to the corresponding monitor under Wayland (wlroots/Hyprland). It uses `hyprctl` to query the monitor layout. Screenshots are then taken only for the affected display, reducing report size and improving clarity.

## Waybar Integration

WSR can be integrated directly into Waybar.

1. **Sudoers Rule (Required for passwordless start):**
   To allow Waybar to start `wsr`, add the following using `sudo visudo`:
   ```text
   %input ALL=(ALL) NOPASSWD: /usr/local/bin/wsr
   ```
   (Adjust the path if `wsr` is installed elsewhere, e.g., check with `which wsr`).

2. **Waybar Configuration (`config`):**

   **Standard (with blink animation):**
   ```json
   "custom/wsr": {
       "exec": "wsr-waybar",
       "return-type": "json",
       "interval": 2,
       "format": "{icon}",
       "format-icons": {
           "recording": "⏺ REC",
           "idle": "📸 WSR"
       },
       "on-click": "wsr-waybar --toggle",
       "signal": 8
   }
   ```

   **With countdown display:**
   ```json
   "custom/wsr": {
       "exec": "wsr-waybar --show-countdown",
       "return-type": "json",
       "interval": 1,
       "format": "{icon} {text}",
       "format-icons": {
           "recording": "⏺",
           "countdown": "⏳",
           "idle": "📸"
       },
       "on-click": "wsr-waybar --toggle"
   }
   ```
   > **Note:** For countdown display, `interval` must be set to `1`!

   **Without blink animation:**
   ```json
   "exec": "wsr-waybar --no-blink"
   ```

   **Available arguments:**
   - `--show-countdown` — Shows the countdown in the module text
   - `--no-blink` — Disables blink animation during recording
   - `--toggle` — Starts/stops recording (for `on-click`)
   - `--lang de|en` — Language for tooltips

3. **Waybar Style (`style.css`):**
   ```css
   #custom-wsr.recording {
       color: #ffffff;
       background: #ff0000;
       font-weight: bold;
   }
   #custom-wsr.blink {
       animation: wsr-blink 0.5s infinite;
   }
   @keyframes wsr-blink {
       50% { opacity: 0; }
   }
   #custom-wsr.countdown {
       color: #ffcc00;
   }
   #custom-wsr.idle {
       color: #ffffff;
   }
   ```

## Running Without Root (sudo)

To run WSR without `sudo`, your user needs access to the input devices.

1. Create a udev rule:
   ```bash
   echo 'KERNEL=="event*", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/99-input.rules
   ```
2. Add your user to the `input` group:
   ```bash
   sudo usermod -aG input $USER
   ```
3. Log out and log back in.

## Development & Testing

```bash
# Run tests
make test

# Run linting
make lint

# Build package
make build
```

## License

MIT License - see [LICENSE](LICENSE) for details.
