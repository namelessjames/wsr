# WSR - Wayland Session Recorder

Ein modernes Python-Rebuild von `xsr` für Wayland-Umgebungen. WSR zeichnet Benutzeraktionen (Klicks, Tastenanschläge) auf und generiert einen bebilderten HTML-Report.

## Features
- **Globales Input-Tracking:** Erfasst Mausbewegungen, Klicks und Tastenanschläge via `/dev/input/`.
- **Multi-Monitor Support:** Erkennt automatisch den aktiven Monitor und erstellt nur dort einen Screenshot.
- **Keystroke Grouping:** Fasst schnell aufeinanderfolgende Tastenanschläge zu lesbaren Textblöcken zusammen.
- **Screenshot-Engine:** Automatische Screenshots bei Mausklicks (unterstützt `grim` für wlroots/Hyprland und `gnome-screenshot`).
- **Cursor-Overlay:** Zeichnet den Mauszeiger an der korrekten Position in den Screenshot ein.
- **Sicherheitsmodus:** Mit `--no-keys` können Tastatureingaben vom Log ausgeschlossen werden.
- **Portabler HTML-Report:** Generiert eine einzige HTML-Datei mit eingebetteten Base64-Bildern.

## Voraussetzungen
- **Linux** mit Wayland.
- **Screenshot-Tool:** 
    - Für Hyprland/Sway: `grim` (empfohlen)
    - Für GNOME: `gnome-screenshot`
- **Berechtigungen:** Zugriff auf `/dev/input/` (siehe unten).

## Installation

```bash
# Repository klonen
git clone <repository-url>
cd wsr

# Virtual Environment erstellen und installieren
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

## Benutzung

```bash
# Einfacher Start (3 Sekunden Countdown)
sudo -E wsr -o mein_report.html

# Ohne Tasten-Logging (nur Klicks & Screenshots)
sudo -E wsr --no-keys

# Tasten-Intervall anpassen (z.B. 800ms statt 500ms)
sudo -E wsr --key-interval 800

# Hilfe anzeigen
wsr --help
```

## Multi-Monitor Support
WSR unterstützt unter Wayland (wlroots/Hyprland) das automatische Mapping von Klicks auf den entsprechenden Monitor. Dabei wird das Tool `hyprctl` genutzt, um das Monitor-Layout abzufragen. Screenshots werden dann nur für den betroffenen Bildschirm erstellt, was die Report-Größe reduziert und die Übersichtlichkeit erhöht.

## Waybar Integration
WSR kann direkt in Waybar integriert werden.

1. **Sudoers-Regel (Wichtig für Start ohne Passwort):**
   Damit Waybar `wsr` starten kann, fügen Sie folgendes mit `sudo visudo` hinzu:
   ```text
   %input ALL=(ALL) NOPASSWD: /usr/local/bin/wsr
   ```
   (Passen Sie den Pfad an, falls `wsr` woanders installiert ist, z.B. `which wsr`).

2. **Waybar Konfiguration (`config`):**

   **Standard (mit Blink-Animation):**
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

   **Mit Countdown-Anzeige:**
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
   > **⚠️ WICHTIG:** Für die Countdown-Anzeige muss `interval` auf `1` gesetzt werden!

   **Ohne Blink-Animation:**
   ```json
   "exec": "wsr-waybar --no-blink"
   ```

   **Verfügbare Argumente:**
   - `--show-countdown` — Zeigt den Countdown im Modul-Text an
   - `--no-blink` — Deaktiviert die Blink-Animation während der Aufnahme
   - `--toggle` — Startet/Stoppt die Aufnahme (für `on-click`)
   - `--lang de|en` — Sprache für Tooltips

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

## Ausführung ohne Root (sudo)
Um WSR ohne `sudo` auszuführen, muss Ihr Benutzer Zugriff auf die Input-Geräte haben.

1. Erstellen Sie eine udev-Regel:
   ```bash
   echo 'KERNEL=="event*", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/99-input.rules
   ```
2. Fügen Sie Ihren Benutzer der Gruppe `input` hinzu:
   ```bash
   sudo usermod -aG input $USER
   ```
3. Melden Sie sich neu an.

## Entwicklung & Tests
```bash
# Tests ausführen
PYTHONPATH=. python3 -m unittest discover tests
```
