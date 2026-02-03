# TODO - wsr Erweiterungen

## Konfiguration & Einstellungen
- Lass den Speicherort im waybar-modul definieren/überschreiben (Oder nutzen wir die Config?) Standardspeicherort muss überschrieben werden dürfen vom Nutzer mithilfe von --location|-l (standard: ~/Pictures/wsr/). Das dient vor allem bei der waybar-Nutzung für mehr Komfort
- Dateinamen der Reports darf überschrieben werden (-o|--output), standard ist "report-YYYY-MM-DD-HH-ii-ss.html". 
- Es darf ein eigenes Dateinamen-format angegeben werden mit --filename-format|-f, wobei platzhalter genutzt werden können. Mögliche Platzhalter:
  - Datum und/oder Uhrzeit "--filename 'report-{%date}'" oder "--filename 'my-report-{%datetime}'"
  - Inkrementeller Zähler "--filename 'report-{%n}'" (fügt eine Nummer an, sucht nach der dem Dateinamen mit 'report-1.html' und erhöht so lange, bis keine Datei mehr gefunden wurde.
- Nutzer sollen mit einer (eine, nicht mehrere) eigenen CSS-Datei in ~/.config/wsr/style.css die Default css überschreiben. Ein parameter --style|-s erlaubt das explizite anfügen einer css-Datei. Wird nicht validiert: Nutzerverantwortung.
- der html lang in report_generator soll die systemeinstellungen oder die einstellungen aus dem parameter --lang übernehmen, Bereits teilweise implementiert (--lang existiert). Prüfen, ob report_generator.py das nutzt.
- Nutzer sollen folgendes für die Speicherung von Bildern entscheiden: a) Ausgabe-Format (png,jpg,webp) --image-format {png|jpg|webp} b) Qualität --image-quality 0.1-1.0 (jpg und webp)
- Nutzer sollen ein eigenes png für den Mauszeiger anfügen dürfen. Dafür soll der Parameter --cursor|-c eingeführt werden. Dieser soll einen absoluten Pfad enthalten, oder aber den Wert 'system'. Der Wert 'system' soll den System-Cursor ausgeben.  Nutzer dürfen aber auch in ~/.config/wsr/ eine eigene cursor.png hinterlegen. Nutzerverantwortung, wird nicht validiert.
- [x] ~~Es soll eine zentrale ~/.config/wsr/wsr.yaml-Datei geben, in der alle Konfigurationen festgelegt werden können. Das soll command line parameter obsolet machen. Command line parameter überschreiben dennoch in letzter instanz. Priorität: cmd parameters > wsr.yaml > hard coded defaults~~ (Implementiert: `src/wsr/config.py`, XDG-konform unter `$XDG_CONFIG_HOME/wsr/wsr.yaml`)

### Alle neu geplanten Parameter

| Parameter              | Datentyp                    | Standardwert                                    | Effekt                                                                                       |
| ---------------------- | --------------------------- | ----------------------------------------------- | -------------------------------------------------------------------------------------------- |
| --location,-l          | String (Pfad)               | `~/Pictures/wsr/`                               | Überschreibt den Speicherort für Reports (Verzeichnis)                                      |
| --filename-format,-f   | String (Format-String)      | `report-{%datetime}.html`                       | Legt das Muster für den Report-Dateinamen fest (Platzhalter: `{%date}`, `{%datetime}`, `{%n}`) |
| --style,-s             | String (Pfad)                | `~/.config/wsr/style.css` (falls vorhanden)    | Pfad zu einer zusätzlichen/eigenen CSS-Datei; überschreibt die eingebauten Standard-Styles  |
| --image-format         | String (enum: png\|jpg\|webp) | `png`                                           | Bildformat der Screenshots                                                                   |
| --image-quality        | Float (0.1-1.0)             | `0.9`                                           | Qualitätsfaktor für `jpg`/`webp`                                                             |
| --cursor,-c            | String (Pfad oder "system")  | `system` (oder `~/.config/wsr/cursor.png`)      | Cursor-Quelle: absoluter Pfad zu einem PNG oder der Wert `system`                            |
| --debug,-d             | Boolean (Flag)               | `false`                                         | Aktiviert erweitertes Logging und schreibt Logdateien                                        |
| --capture-window-only  | Boolean (Flag)               | `false`                                         | Erstellt nur einen Screenshot des angeklickten Fensters statt des gesamten Monitors          |

## Installation & Deployment
- Erstelle ein Install/make-skript. beachte das Paket soll einfach im AUR gehosted werden, Building und Installation sollen damit funktionieren.
  - PKGBUILD für AUR
  - Makefile it install, uninstall, build
  - python setup bereits vorhanden

- Ersetze '/home/martinsauerbrey' durch generische und gegebenenfalls dynamische pfade, damit nutzer das venv in dem ordner erstellen können, wo das repo hin geklont wurde

## UI/UX Verbesserungen
- Erweiter das waybar-modul, sodass nutzer entscheiden können, ob der recording-zustand blinken soll oder nicht (in der waybar conf file, für das custom-wsr-modul)
- Aktiviere verbose-output im terminal via --verbose|-v, ansonsten wird nichts ausgegeben.

## Funktionalität & Features
- Prüfe ob bash commands durch Nutzer-konfigurierte shells ersetzt werden müssen oder der Nutzer die Option erhalten muss
- Füge die Option hinzu, lediglich das Fenster, welches angeklickt wird, zu screenshotten --capture-window-only

## Logging & Debugging
- Logging soll über --deubg|-d eingeschaltet werden können. Nutze das linux default-Verzeichnis für logging (/var/log?)

## Dokumentation
- Dokumentation in Github Wiki
