# WSR Architecture Guide for AI Agents

## Übersicht

WSR (Wayland Session Recorder) ist ein Python-CLI-Tool, das Benutzerinteraktionen unter Wayland aufzeichnet und einen bebilderten HTML-Report generiert. Das Tool ersetzt das ursprüngliche `xsr` für X11.

## Kernkonzept

```
┌─────────────────────────────────────────────────────────────────┐
│                          main.py                                │
│                    (Orchestrator/Event-Loop)                    │
└────────┬───────────┬───────────┬───────────┬───────────┬────────┘
         │           │           │           │           │
         ▼           ▼           ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│InputManager │ │ScreenshotEng│ │MonitorMgr   │ │ KeyBuffer   │ │ReportGen    │
│ (evdev)     │ │ (grim/gnome)│ │ (hyprctl)   │ │ (Grouping)  │ │ (HTML+Base64)│
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

## Modulstruktur

```
src/wsr/
├── __init__.py          # Leer (Namespace-Package)
├── main.py              # CLI-Entry-Point, Event-Loop, Orchestrierung
├── config.py            # YAML-Config, XDG-Pfade, CLI-Argument-Merge
├── input_manager.py     # /dev/input-Listener via evdev (Maus + Tastatur)
├── screenshot_engine.py # Screenshot-Capture (grim/gnome-screenshot) + Cursor-Overlay
├── report_generator.py  # HTML-Report mit eingebetteten Base64-Bildern
├── monitor_manager.py   # Multi-Monitor-Layout-Erkennung via hyprctl
├── key_buffer.py        # Gruppierung schneller Tastenanschläge zu Textblöcken
├── i18n.py              # JSON-basierte Lokalisierung (de/en)
├── waybar_module.py     # Waybar-Integration (JSON-Output, Toggle-Funktion)
└── locales/
    ├── de.json          # Deutsche Übersetzungen
    └── en.json          # Englische Übersetzungen
```

---

## Modul-Details

### 1. `main.py` – Entry-Point & Orchestrator

**Zweck:** CLI-Parsing, Event-Loop, Signal-Handling, Modul-Koordination.

**Kritische Funktionen:**
- `main()` – Initialisiert alle Module, startet Event-Loop
- `parse_arguments()` – CLI-Args mit Config-Merge (CLI > YAML > Defaults)
- `signal_handler()` – Graceful Shutdown bei SIGINT (Ctrl+C)
- `send_notification()` – Desktop-Notification via `notify-send` (als Original-User bei sudo)

**Event-Loop-Logik:**
```python
while True:
    # 1. KeyBuffer-Timeout prüfen → flush zu key_group
    # 2. Event-Queue abarbeiten:
    #    - 'key' → KeyBuffer.add() oder flush + add
    #    - 'click' → KeyBuffer flush, Monitor ermitteln, Screenshot + Cursor
    # 3. Sleep 50ms
```

**Wichtige Datenstruktur (captured_events):**
```python
[
    {'type': 'click', 'button': 'BTN_LEFT', 'x': 1234, 'y': 567, 'time': float, 'screenshot': PIL.Image},
    {'type': 'key_group', 'text': 'Hallo Welt', 'time': float},
]
```

---

### 2. `config.py` – Konfigurationsmanagement

**Zweck:** XDG-konforme Config-Verwaltung mit Prioritätskette.

**Priorität:** `CLI-Argumente > ~/.config/wsr/wsr.yaml > Hardcoded-Defaults`

**Kritische Funktionen:**
- `load_config()` – Lädt YAML, merged mit Defaults
- `resolve_output_path(location, filename_format, explicit_out)` – Platzhalter-Ersetzung
- `resolve_style_path()` – Custom-CSS-Pfad-Auflösung

**Platzhalter im Dateinamen:**
| Platzhalter | Ersetzung |
|-------------|-----------|
| `{%datetime}` | `2024-01-15-14-30-00` |
| `{%date}` | `2024-01-15` |
| `{%n}` | Inkrementelle Nummer (findet nächste freie) |

**Config-Pfad:** `$XDG_CONFIG_HOME/wsr/wsr.yaml` (Default: `~/.config/wsr/wsr.yaml`)

---

### 3. `input_manager.py` – Input-Device-Handling

**Zweck:** Globales Capturing von Maus- und Tastaturevents via Linux evdev.

**Klasse:** `InputManager`

**Kritische Mechanismen:**
- Scannt `/dev/input/event*` nach Mäusen (EV_REL) und Tastaturen (EV_KEY + KEY_A)
- Läuft in separatem Daemon-Thread
- Relative Mausposition wird virtuell getracked (keine absolute Position unter Wayland)
- Events landen in `self.event_queue` (thread-safe Queue)

**Benötigte Berechtigungen:** Root oder Gruppe `input`

**Event-Struktur:**
```python
# Mausklick
{'type': 'click', 'button': 'BTN_LEFT', 'x': 1920, 'y': 540, 'time': float}

# Tastendruck
{'type': 'key', 'key': 'KEY_A', 'time': float}
```

**Schwachstelle:** Die Mausposition ist relativ getracked – bei Sprüngen (z.B. Wayland-Pointer-Warping) kann es zu Drift kommen. Screen-Size muss extern (MonitorManager) gesetzt werden.

---

### 4. `screenshot_engine.py` – Screenshot-Capture

**Zweck:** Screenshots erstellen und Cursor-Overlay hinzufügen.

**Klasse:** `ScreenshotEngine`

**Backend-Erkennung (Priorität):**
1. `grim` (wlroots/Hyprland/Sway) – bevorzugt, unterstützt `-o <monitor>`
2. `gnome-screenshot` – Fallback für GNOME

**Kritische Methoden:**
- `capture(monitor_name=None)` → `PIL.Image`
- `add_cursor(screenshot, x, y)` → Compositing des Cursor-Overlays

**Cursor:** Einfaches weißes Polygon mit schwarzem Rand (24x24px). Wird dynamisch auf Screenshot composited.

**Umgebungsvariable:** `WAYLAND_DISPLAY` muss gesetzt sein (daher `sudo -E`).

---

### 5. `report_generator.py` – HTML-Report-Generierung

**Zweck:** Standalone-HTML mit eingebetteten Base64-Bildern.

**Klasse:** `ReportGenerator`

**Konfigurationsoptionen:**
| Option | Default | Beschreibung |
|--------|---------|--------------|
| `image_format` | `png` | `png`, `jpg`, `webp` |
| `image_quality` | `0.9` | 0.1–1.0 (nur für jpg/webp) |
| `custom_style_path` | None | Pfad zu Custom-CSS |

**HTML-Features:**
- Dark/Light-Mode via CSS `prefers-color-scheme`
- CSS-Variablen für einfaches Theming
- Responsive Bilder (`max-width: 100%`)

**Generierte Struktur:**
```html
<div class="step">
    <div class="meta">14:30:00.123</div>
    <div class="description">Klick: BTN_LEFT bei (1234, 567)</div>
    <img src="data:image/png;base64,..." alt="Screenshot">
</div>
```

---

### 6. `monitor_manager.py` – Multi-Monitor-Support

**Zweck:** Mapping von globalen Koordinaten auf einzelne Monitore.

**Klasse:** `MonitorManager`

**Datenquelle:** `hyprctl monitors -j` (JSON)

**Monitor-Datenstruktur:**
```python
{'name': 'DP-1', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080}
{'name': 'HDMI-A-1', 'x': 1920, 'y': 0, 'width': 2560, 'height': 1440}
```

**Kritische Methoden:**
- `get_monitor_at(x, y)` → Monitor-Name oder None
- `get_relative_coordinates(x, y, monitor_name)` → (rel_x, rel_y)

**Limitation:** Unterstützt nur Hyprland via `hyprctl`. Für Sway wäre `swaymsg -t get_outputs` nötig.

---

### 7. `key_buffer.py` – Tastatur-Gruppierung

**Zweck:** Schnelle Tastenanschläge zu lesbarem Text zusammenfassen.

**Klasse:** `KeyBuffer`

**Logik:**
- Tasten innerhalb `interval_ms` (Default: 500ms) werden gebuffert
- Bei Timeout oder Mausklick wird Buffer geflusht
- Ergebnis: `key_group`-Event statt vieler einzelner `key`-Events

**Key-Mapping:**
```python
KEY_A     → 'A'
KEY_SPACE → ' '
KEY_ENTER → '\n'
KEY_BACKSPACE → '⌫'
KEY_SHIFT → '[SHIFT]'
```

**Methoden:**
- `add(key_name)` → True (hinzugefügt) oder False (flush nötig)
- `is_timed_out()` → True wenn Intervall überschritten
- `flush()` → Concatenated String oder None

---

### 8. `i18n.py` – Internationalisierung

**Zweck:** JSON-basierte Übersetzungen mit Platzhaltern.

**Klasse:** `I18n`

**Spracherkennung:** `locale.getdefaultlocale()` → Fallback `en`

**API:**
```python
from .i18n import _, init_i18n

init_i18n("de")  # oder None für Auto-Detect
print(_("report_title"))  # → "WSR Sitzungsaufzeichnung"
print(_("click_on_monitor", name="DP-1", x=100, y=200))  # → Formatiert
```

**Locale-Dateien:** `src/wsr/locales/{lang}.json`

---

### 9. `waybar_module.py` – Desktop-Integration

**Zweck:** Waybar-Custom-Module für Status-Anzeige und Toggle.

**Entry-Point:** `wsr-waybar` (via pyproject.toml)

**JSON-Output für Waybar:**
```json
{"text": "", "alt": "idle", "class": "idle", "tooltip": "Klicken zum Starten"}
{"text": "", "alt": "recording", "class": "recording", "tooltip": "Aufnahme läuft..."}
```

**Toggle-Logik:**
- Running: `pkill -INT -f wsr.main` (SIGINT → graceful shutdown)
- Stopped: `sudo -E wsr ... &` (im Hintergrund)

---

## Datenfluss

```
User-Input (Maus/Tastatur)
         │
         ▼
    InputManager
    (evdev Thread)
         │
         ▼
    Event-Queue ──────────────────────────┐
         │                                │
         ▼                                ▼
    main.py Event-Loop              KeyBuffer
    (Orchestrator)                  (Grouping)
         │                                │
         ├── 'click' Event ───────────────┤
         │         │                      │
         │         ▼                      │
         │   MonitorManager               │
         │   (get_monitor_at)             │
         │         │                      │
         │         ▼                      │
         │   ScreenshotEngine             │
         │   (capture + cursor)           │
         │         │                      │
         └─────────┴──────────────────────┘
                   │
                   ▼
            captured_events[]
                   │
                   ▼ (on SIGINT)
            ReportGenerator
                   │
                   ▼
            output.html
```

---

## Konfigurationshierarchie

```
┌─────────────────────────────┐
│     CLI-Argumente           │  Höchste Priorität
│  (--out, --no-keys, ...)    │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ ~/.config/wsr/wsr.yaml      │  YAML-Config
│ (location, key_interval...) │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   Hardcoded Defaults        │  Niedrigste Priorität
│   (in config.py)            │
└─────────────────────────────┘
```

---

## Abhängigkeiten

| Paket | Version | Zweck |
|-------|---------|-------|
| evdev | - | Input-Device-Handling |
| Pillow | - | Screenshot-Manipulation |
| PyYAML | - | Config-Parsing |

**Externe Tools:**
- `grim` oder `gnome-screenshot` – Screenshot-Capture
- `hyprctl` – Monitor-Layout-Abfrage
- `notify-send` – Desktop-Benachrichtigungen

---

## Berechtigungsmodell

```
┌────────────────────────────────────────────────────────┐
│  sudo -E wsr                                           │
│  └── -E erhält WAYLAND_DISPLAY, XDG_RUNTIME_DIR etc.  │
└────────────────────────────────────────────────────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
    ▼                     ▼                     ▼
/dev/input/           grim (Wayland)      notify-send
(root nötig)          (User-Session)      (User-Session)
                           │                    │
                      Env-Variablen       drop_privileges()
                      von -E              → Original-User
```

**Alternative (ohne sudo):**
```bash
# udev-Regel erstellen
echo 'KERNEL=="event*", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/99-input.rules
sudo usermod -aG input $USER
# Neu einloggen
```

---

## Erweiterungspunkte

### Neues Screenshot-Backend hinzufügen
→ `screenshot_engine.py`: `_detect_backend()` erweitern, neuen Branch in `capture()` hinzufügen.

### Neuen Monitor-Manager hinzufügen (z.B. Sway)
→ `monitor_manager.py`: `refresh()` erweitern mit `swaymsg -t get_outputs`.

### Neue Sprache hinzufügen
→ `src/wsr/locales/{lang}.json` erstellen, Keys aus `en.json` kopieren.

### Custom-CSS
→ `~/.config/wsr/style.css` erstellen, CSS-Variablen überschreiben.

---

## Bekannte Limitationen

1. **Mausposition-Drift:** Relative Tracking kann bei Pointer-Warping ungenau werden.
2. **Nur Hyprland:** MonitorManager funktioniert nur mit `hyprctl`.
3. **Keine Touchpad-Gesten:** Nur Klicks werden erfasst.
4. **Root erforderlich:** Für `/dev/input`-Zugriff (oder udev-Regel).
5. **Keine Passwort-Maskierung:** Alle Tastenanschläge werden geloggt (Sicherheitsmodus mit `--no-keys`).

---

## Test-Struktur

```
tests/
├── test_cli.py         # CLI-Argument-Parsing
├── test_config.py      # Config-Loading, Pfad-Resolution
├── test_i18n.py        # Übersetzungen
├── test_input.py       # InputManager (mocked)
├── test_key_buffer.py  # KeyBuffer-Gruppierung
├── test_monitor.py     # MonitorManager
├── test_report.py      # ReportGenerator
└── test_screenshot.py  # ScreenshotEngine
```

**Test ausführen:**
```bash
PYTHONPATH=. python3 -m unittest discover tests
```

---

## Quick Reference für AI Agents

| Aktion | Datei | Funktion/Klasse |
|--------|-------|-----------------|
| CLI-Args ändern | `main.py` | `parse_arguments()` |
| Neues Event-Type hinzufügen | `main.py` | Event-Loop in `main()` |
| Screenshot-Backend erweitern | `screenshot_engine.py` | `_detect_backend()`, `capture()` |
| HTML-Styling ändern | `report_generator.py` | `_build_header()` |
| Neue Config-Option | `config.py` | `get_default_config()`, `_DEFAULT_YAML_CONTENT` |
| Übersetzung hinzufügen | `locales/*.json` | Key-Value hinzufügen |
| Monitor-Support erweitern | `monitor_manager.py` | `refresh()` |
