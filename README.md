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
sudo wsr -o mein_report.html

# Ohne Tasten-Logging (nur Klicks & Screenshots)
sudo wsr --no-keys

# Tasten-Intervall anpassen (z.B. 800ms statt 500ms)
sudo wsr --key-interval 800

# Hilfe anzeigen
wsr --help
```

## Multi-Monitor Support
WSR unterstützt unter Wayland (wlroots/Hyprland) das automatische Mapping von Klicks auf den entsprechenden Monitor. Dabei wird das Tool `hyprctl` genutzt, um das Monitor-Layout abzufragen. Screenshots werden dann nur für den betroffenen Bildschirm erstellt, was die Report-Größe reduziert und die Übersichtlichkeit erhöht.

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
