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

- **Linux** with Wayland
- **Screenshot Tool:**
  - Hyprland/Sway: `grim`
  - GNOME: `gnome-screenshot`
- **Optional:** `hyprctl` for multi-monitor support (auto-detected)
- **Permissions:** Read access to `/dev/input/` (via `sudo` or `input` group, see below)

## Installation

```bash
git clone https://github.com/namelessjames/wsr.git
cd wsr
pipx install .
```

This installs `wsr` and `wsr-waybar` to `~/.local/bin/`.

### Arch Linux (AUR)

```bash
makepkg -si
```

### Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
# Start recording (3 second countdown, then Ctrl+C to stop)
sudo -E wsr

# Explicit output path
sudo -E wsr -o my_report.html

# Without key logging (clicks & screenshots only)
sudo -E wsr --no-keys
```

Stop recording with **Ctrl+C**. The report is generated on exit.

Without `-o`, reports are saved to `~/Pictures/wsr/report-<datetime>.html`.

### CLI Options

| Option | Description | Default |
|---|---|---|
| `-o, --out` | Output file path | `~/Pictures/wsr/report-{datetime}.html` |
| `-l, --location` | Target directory for reports | `~/Pictures/wsr/` |
| `-f, --filename-format` | Filename format (`{%date}`, `{%datetime}`, `{%n}`) | `report-{%datetime}.html` |
| `-s, --style` | Custom CSS file for the report | — |
| `--image-format` | Screenshot format: `png`, `jpg`, `webp` | `png` |
| `--image-quality` | Quality for jpg/webp (0.1–1.0) | `0.9` |
| `--countdown` | Delay before start (seconds) | `3` |
| `--no-keys` | Disable keyboard logging | — |
| `--key-interval` | Keystroke grouping interval (ms) | `500` |
| `--lang` | Language (`de`, `en`) | System locale |
| `--toggle` | Start/stop recording (Waybar integration) | — |
| `-v, --verbose` | Debug logging | — |

Defaults can be overridden via `wsr.yaml` (CLI takes priority).

## Waybar Integration

### 1. Sudoers Rule

Passwordless `sudo` for Waybar:

```bash
sudo visudo -f /etc/sudoers.d/wsr
```
```text
%input ALL=(ALL) NOPASSWD:SETENV: /home/<user>/.local/bin/wsr, /usr/bin/kill
```

Replace `<user>` with your username. Verify the path with `which wsr`.
`SETENV:` is required so `sudo -E` can pass `WAYLAND_DISPLAY` to `grim`. `/usr/bin/kill` is needed to stop the root-owned recording process.

### 2. Waybar Config

```json
"custom/wsr": {
    "exec": "wsr-waybar",
    "return-type": "json",
    "interval": 2,
    "format": "{icon}",
    "format-icons": {
        "recording": "⏺",
        "idle": ""
    },
    "on-click": "wsr --toggle",
    "signal": 8
}
```

For countdown display, use `"exec": "wsr-waybar --show-countdown"` with `"interval": 1` and add `"countdown": ""` to `format-icons`.

**`on-click` toggle:** `wsr --toggle` starts/stops recording. The `--toggle` flag is available on both `wsr` and `wsr-waybar`.

**`wsr-waybar` arguments (status polling):**

| Argument | Description |
|---|---|
| `--toggle` | Start/stop recording (for `on-click`) |
| `--show-countdown` | Show countdown in module text (requires `interval: 1`) |
| `--no-blink` | Disable blink animation during recording |
| `--lang de\|en` | Tooltip language |

### 3. Waybar Style

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

## Running Without Root

Add your user to the `input` group and create a udev rule for `/dev/input/` access:

```bash
sudo usermod -aG input $USER
echo 'KERNEL=="event*", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/99-input.rules
```

Re-login for group changes to take effect.

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
