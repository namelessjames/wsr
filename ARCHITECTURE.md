# WSR Architecture Guide for AI Agents

## Overview

WSR (Wayland Session Recorder) is a Python CLI tool that records user interactions under Wayland and generates an illustrated HTML report. The tool replaces the original `xsr` for X11.

## Core Concept

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               main.py                                       │
│                         (Orchestrator/Event-Loop)                           │
└────────┬───────────┬───────────┬───────────┬───────────┬───────────┬────────┘
         │           │           │           │           │           │
         ▼           ▼           ▼           ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│InputManager │ │Screenshot   │ │MonitorMgr   │ │ KeyBuffer   │ │ReportGen    │ │Config      │
│ (evdev)     │ │Worker+Engine│ │ (hyprctl)   │ │ (Grouping)  │ │(HTML+Base64)│ │ (Validation)│
└─────────────┘ └──────┬──────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
                       │
                       ▼
               ┌─────────────────┐
               │ThreadPoolExecutor│
               │ (2 Workers)      │
               └─────────────────┘
```

## Module Structure

```
src/wsr/
├── __init__.py          # Empty (namespace package)
├── main.py              # CLI entry point, event loop, orchestration
├── config.py            # YAML config with schema validation, XDG paths
├── input_manager.py     # /dev/input listener via evdev (mouse + keyboard)
├── screenshot_engine.py # Screenshot capture (grim/gnome-screenshot) + cursor overlay
├── screenshot_worker.py # Async screenshot queue via ThreadPoolExecutor
├── report_generator.py  # HTML report with embedded Base64 images
├── monitor_manager.py   # Multi-monitor layout detection via hyprctl
├── key_buffer.py        # Grouping rapid keystrokes into text blocks
├── i18n.py              # JSON-based localization (de/en)
├── waybar_module.py     # Waybar integration (JSON output, toggle, blink/countdown)
└── locales/
    ├── de.json          # German translations
    └── en.json          # English translations
```

---

## Module Details

### 1. `main.py` – Entry Point & Orchestrator

**Purpose:** CLI parsing, event loop, signal handling, module coordination.

**Critical Functions:**
- `main()` – Initializes all modules, starts event loop
- `parse_arguments()` – CLI args with config merge (CLI > YAML > Defaults)
- `signal_handler()` – Graceful shutdown on SIGINT (Ctrl+C)
- `send_notification()` – Desktop notification via `notify-send` (as original user under sudo)

**Event Loop Logic:**
```python
while True:
    # 1. Check KeyBuffer timeout → flush to key_group
    # 2. Process event queue:
    #    - 'key' → KeyBuffer.add() or flush + add
    #    - 'click' → KeyBuffer flush, determine monitor,
    #                event immediately to captured_events[],
    #                screenshot_worker.request_screenshot() (async)
    # 3. Sleep 50ms

# On SIGINT:
screenshot_worker.wait_for_pending()  # Wait for pending screenshots
report_gen.generate(captured_events)
```

**Important Data Structure (captured_events):**
```python
[
    {
        'type': 'click', 'button': 'BTN_LEFT', 'x': 1234, 'y': 567, 'time': float,
        'screenshot_bytes': bytes,  # Added async by ScreenshotWorker
        'screenshot_mime': str      # e.g., "image/webp"
    },
    {'type': 'key_group', 'text': 'Hello World', 'time': float},
]
```

**State File for Waybar:** `/tmp/wsr_state.json` is written during countdown/recording, removed on exit.

---

### 2. `config.py` – Configuration Management

**Purpose:** XDG-compliant config management with priority chain and schema validation.

**Priority:** `CLI arguments > ~/.config/wsr/wsr.yaml > Hardcoded defaults`

**Critical Functions:**
- `load_config()` – Loads YAML, merges with defaults, validates against schema
- `validate_config(config)` → `list[str]` – Checks types and value ranges, returns errors
- `resolve_output_path(location, filename_format, explicit_out)` – Placeholder substitution
- `resolve_style_path()` – Custom CSS path resolution

**Schema Validation (`_CONFIG_SCHEMA`):**
```python
{
    "image_format": (str, lambda v: v in ("png", "jpg", "jpeg", "webp"), "..."),
    "image_quality": ((int, float), lambda v: 0.1 <= v <= 1.0, "..."),
    "countdown": (int, lambda v: v >= 0, "..."),
    # ... more keys
}
```

**Filename Placeholders:**
| Placeholder | Replacement |
|-------------|-------------|
| `{%datetime}` | `2024-01-15-14-30-00` |
| `{%date}` | `2024-01-15` |
| `{%n}` | Incremental number (finds next available) |

**Config Path:** `$XDG_CONFIG_HOME/wsr/wsr.yaml` (Default: `~/.config/wsr/wsr.yaml`)

**Exception:** `ConfigError` is thrown on invalid values – contains formatted error list

---

### 3. `input_manager.py` – Input Device Handling

**Purpose:** Global capturing of mouse and keyboard events via Linux evdev.

**Class:** `InputManager`

**Critical Mechanisms:**
- Scans `/dev/input/event*` for mice (EV_REL) and keyboards (EV_KEY + KEY_A)
- Runs in separate daemon thread
- Relative mouse position is tracked virtually (no absolute position under Wayland)
- Events land in `self.event_queue` (thread-safe Queue)

**Required Permissions:** Root or `input` group membership

**Event Structure:**
```python
# Mouse click
{'type': 'click', 'button': 'BTN_LEFT', 'x': 1920, 'y': 540, 'time': float}

# Key press
{'type': 'key', 'key': 'KEY_A', 'time': float}
```

**Weakness:** Mouse position is tracked relatively – drift can occur with pointer warping (e.g., Wayland pointer jumps). Screen size must be set externally (MonitorManager).

---

### 4. `screenshot_engine.py` – Screenshot Capture

**Purpose:** Take screenshots and add cursor overlay.

**Class:** `ScreenshotEngine`

**Backend Detection (Priority):**
1. `grim` (wlroots/Hyprland/Sway) – preferred, supports `-o <monitor>`
2. `gnome-screenshot` – Fallback for GNOME

**Critical Methods:**
- `capture(monitor_name=None)` → `PIL.Image`
- `add_cursor(screenshot, x, y)` → Compositing the cursor overlay
- `capture_with_cursor_compressed(x, y, monitor_name, format, quality)` → `(bytes, mime_type)` – Memory-efficient variant, compresses immediately to ~50-200 KB instead of holding 31.6 MB PIL.Image in RAM

**Cursor:** Simple white polygon with black border (24x24px). Dynamically composited onto screenshot.

**Environment Variable:** `WAYLAND_DISPLAY` must be set (hence `sudo -E`).

---

### 4b. `screenshot_worker.py` – Asynchronous Screenshot Queue

**Purpose:** Decouples screenshot capture from event loop, prevents UI lag during rapid click sequences.

**Class:** `ScreenshotWorker`

**Architecture:**
```
main.py Event-Loop                    ThreadPoolExecutor (2 Workers)
        │                                      │
        ├── request_screenshot(event, ...) ────┤
        │   (non-blocking, returns immediately)│
        │                                      ▼
        │                              ┌───────────────┐
        │                              │ _do_screenshot│
        │                              │ (background)  │
        │                              └───────┬───────┘
        │                                      │
        │                    event['screenshot_bytes'] = bytes
        │                    event['screenshot_mime'] = mime
```

**Critical Methods:**
- `request_screenshot(event, monitor_name, rel_x, rel_y, format, quality)` – Queues screenshot request, mutates event dict in-place
- `wait_for_pending(timeout=5.0)` → `int` – Waits for all pending requests
- `pending_count()` → `int` – Number of incomplete requests
- `shutdown(wait=True)` – Shuts down thread pool

**Design Decision:** Event dict is mutated in-place rather than using return values, since the worker runs asynchronously and the event is already in `captured_events[]`.

---

### 5. `report_generator.py` – HTML Report Generation

**Purpose:** Standalone HTML with embedded Base64 images.

**Class:** `ReportGenerator`

**Configuration Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `image_format` | `png` | `png`, `jpg`, `webp` |
| `image_quality` | `0.9` | 0.1–1.0 (only for jpg/webp) |
| `custom_style_path` | None | Path to custom CSS |

**HTML Features:**
- Dark/Light mode via CSS `prefers-color-scheme`
- CSS variables for easy theming
- Responsive images (`max-width: 100%`)

**Generated Structure:**
```html
<div class="step">
    <div class="meta">14:30:00.123</div>
    <div class="description">Click: BTN_LEFT at (1234, 567)</div>
    <img src="data:image/png;base64,..." alt="Screenshot">
</div>
```

---

### 6. `monitor_manager.py` – Multi-Monitor Support

**Purpose:** Mapping global coordinates to individual monitors.

**Class:** `MonitorManager`

**Data Source:** `hyprctl monitors -j` (JSON)

**Monitor Data Structure:**
```python
{'name': 'DP-1', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080}
{'name': 'HDMI-A-1', 'x': 1920, 'y': 0, 'width': 2560, 'height': 1440}
```

**Critical Methods:**
- `get_monitor_at(x, y)` → Monitor name or None
- `get_relative_coordinates(x, y, monitor_name)` → (rel_x, rel_y)

**Limitation:** Only supports Hyprland via `hyprctl`. For Sway, `swaymsg -t get_outputs` would be needed.

---

### 7. `key_buffer.py` – Keyboard Grouping

**Purpose:** Combine rapid keystrokes into readable text.

**Class:** `KeyBuffer`

**Logic:**
- Keys within `interval_ms` (default: 500ms) are buffered
- Buffer is flushed on timeout or mouse click
- Result: `key_group` event instead of many individual `key` events

**Key Mapping:**
```python
KEY_A     → 'A'
KEY_SPACE → ' '
KEY_ENTER → '\n'
KEY_BACKSPACE → '⌫'
KEY_SHIFT → '[SHIFT]'
```

**Methods:**
- `add(key_name)` → True (added) or False (flush needed)
- `is_timed_out()` → True if interval exceeded
- `flush()` → Concatenated string or None

---

### 8. `i18n.py` – Internationalization

**Purpose:** JSON-based translations with placeholders.

**Class:** `I18n`

**Language Detection:** `locale.getdefaultlocale()` → Fallback `en`

**API:**
```python
from .i18n import _, init_i18n

init_i18n("de")  # or None for auto-detect
print(_("report_title"))  # → "WSR Session Recording"
print(_("click_on_monitor", name="DP-1", x=100, y=200))  # → Formatted
```

**Locale Files:** `src/wsr/locales/{lang}.json`

---

### 9. `waybar_module.py` – Desktop Integration

**Purpose:** Waybar custom module for status display and toggle.

**Entry Point:** `wsr-waybar` (via pyproject.toml)

**CLI Parameters:**
| Parameter | Effect |
|-----------|--------|
| `--toggle` | Starts/stops wsr |
| `--no-blink` | Disables `blink` CSS class in recording state |
| `--show-countdown` | Shows countdown seconds in text |
| `--lang` | Language for tooltips |

**JSON Output for Waybar:**
```json
{"text": "", "alt": "idle", "class": "idle", "tooltip": "Click to start"}
{"text": "", "alt": "recording", "class": "recording blink", "tooltip": "Recording..."}
{"text": "3", "alt": "countdown", "class": "countdown", "tooltip": "Starting in 3..."}
```

**State File:** `/tmp/wsr_state.json` – Contains `state`, `pid`, `remaining`/`end_time` for coordination between main.py and waybar_module.py

**Toggle Logic:**
- Running: `os.kill(pid, SIGINT)` via state file (no pkill, direct PID)
- Stopped: `sudo -E wsr ... &` (in background)

---

## Data Flow

```
User Input (Mouse/Keyboard)
         │
         ▼
    InputManager
    (evdev Thread)
         │
         ▼
    Event Queue ──────────────────────────┐
         │                                │
         ▼                                ▼
    main.py Event Loop              KeyBuffer
    (Orchestrator)                  (Grouping)
         │                                │
         ├── 'click' Event ───────────────┤
         │         │                      │
         │         ▼                      │
         │   MonitorManager               │
         │   (get_monitor_at)             │
         │         │                      │
         │         ▼                      │
         │   ScreenshotWorker             │
         │   (async queue)                │
         │         │                      │
         │         ▼                      │
         │   ThreadPoolExecutor ─────────►│ ScreenshotEngine.capture_with_cursor_compressed()
         │   (background thread)          │ → event['screenshot_bytes'] = bytes
         │         │                      │ → event['screenshot_mime'] = mime_type
         └─────────┴──────────────────────┘
                   │
                   ▼
            captured_events[]
            (events with screenshot_bytes/mime)
                   │
                   ▼ (on SIGINT)
            wait_for_pending()  ← Wait for pending screenshots
                   │
                   ▼
            ReportGenerator
                   │
                   ▼
            output.html
```

**Important:** Screenshots are no longer taken synchronously in the event loop. The worker mutates the event dict asynchronously in-place. Before report generation, `wait_for_pending()` must be called.

---

## Configuration Hierarchy

```
┌─────────────────────────────┐
│     CLI Arguments           │  Highest Priority
│  (--out, --no-keys, ...)    │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ ~/.config/wsr/wsr.yaml      │  YAML Config
│ (location, key_interval...) │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   Hardcoded Defaults        │  Lowest Priority
│   (in config.py)            │
└─────────────────────────────┘
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| evdev | - | Input device handling |
| Pillow | - | Screenshot manipulation |
| PyYAML | - | Config parsing |

**External Tools:**
- `grim` or `gnome-screenshot` – Screenshot capture
- `hyprctl` – Monitor layout query
- `notify-send` – Desktop notifications

---

## Permission Model

```
┌────────────────────────────────────────────────────────────────┐
│  sudo -E wsr                                                   │
│  └── -E preserves WAYLAND_DISPLAY, XDG_RUNTIME_DIR, etc.      │
└────────────────────────────────────────────────────────────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
    ▼                     ▼                     ▼
/dev/input/           grim (Wayland)      notify-send
(root required)       (User session)      (User session)
                           │                    │
                      Env variables       drop_privileges()
                      from -E             → Original user
```

**Alternative (without sudo):**
```bash
# Create udev rule
echo 'KERNEL=="event*", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/99-input.rules
sudo usermod -aG input $USER
# Log out and back in
```

---

## Extension Points

### Adding a New Screenshot Backend
→ `screenshot_engine.py`: Extend `_detect_backend()`, add new branch in `capture()`.

### Adding a New Monitor Manager (e.g., Sway)
→ `monitor_manager.py`: Extend `refresh()` with `swaymsg -t get_outputs`.

### Adding a New Language
→ Create `src/wsr/locales/{lang}.json`, copy keys from `en.json`.

### Custom CSS
→ Create `~/.config/wsr/style.css`, override CSS variables.

---

## Known Limitations

1. **Mouse Position Drift:** Relative tracking can become inaccurate with pointer warping.
2. **Hyprland Only:** MonitorManager only works with `hyprctl`.
3. **No Touchpad Gestures:** Only clicks are captured.
4. **Root Required:** For `/dev/input` access (or udev rule).
5. **No Password Masking:** All keystrokes are logged (use privacy mode with `--no-keys`).

---

## Test Structure

```
tests/
├── test_cli.py              # CLI argument parsing
├── test_config.py           # Config loading, path resolution, validation
├── test_i18n.py             # Translations
├── test_input.py            # InputManager (mocked)
├── test_key_buffer.py       # KeyBuffer grouping
├── test_monitor.py          # MonitorManager
├── test_report.py           # ReportGenerator
├── test_screenshot.py       # ScreenshotEngine
└── test_screenshot_worker.py # ScreenshotWorker (async queue)
```

**Run Tests:**
```bash
make test
# or
PYTHONPATH=. python3 -m unittest discover tests
```

---

## Quick Reference for AI Agents

| Action | File | Function/Class |
|--------|------|----------------|
| Modify CLI args | `main.py` | `parse_arguments()` |
| Add new event type | `main.py` | Event loop in `main()` |
| Extend screenshot backend | `screenshot_engine.py` | `_detect_backend()`, `capture()` |
| Modify screenshot processing | `screenshot_worker.py` | `ScreenshotWorker._do_screenshot()` |
| Change HTML styling | `report_generator.py` | `_build_header()` |
| Add new config option | `config.py` | `get_default_config()`, `_DEFAULT_YAML_CONTENT`, `_CONFIG_SCHEMA` |
| Extend config validation | `config.py` | `_CONFIG_SCHEMA`, `validate_config()` |
| Add translation | `locales/*.json` | Add key-value pair |
| Extend monitor support | `monitor_manager.py` | `refresh()` |
| Extend Waybar status | `waybar_module.py` | `get_status()` |
