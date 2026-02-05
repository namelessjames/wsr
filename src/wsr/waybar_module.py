#!/usr/bin/env python3
import json
import subprocess
import sys
import os
import argparse
import time

# Add package dir to path for imports to work when run as script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wsr.i18n import _, init_i18n, _instance

STATE_FILE = "/tmp/wsr_state.json"


def read_state() -> dict | None:
    """Liest State-Datei, gibt None bei Fehler."""
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def is_pid_alive(pid: int) -> bool:
    """Prüft ob PID existiert (Signal 0 = nur prüfen)."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def is_wsr_running() -> tuple[bool, dict | None]:
    """Prüft WSR-Status via State-Datei + PID-Validierung."""
    state = read_state()
    if state and "pid" in state:
        if is_pid_alive(state["pid"]):
            return True, state
        # Verwaiste State-Datei aufräumen
        try:
            os.unlink(STATE_FILE)
        except OSError:
            pass
    return False, None


def get_status(show_countdown: bool = False, no_blink: bool = False) -> dict:
    """
    Returns JSON structure for Waybar.
    'text' can be empty or countdown, 'alt' is used for format-icons.
    """
    running, state = is_wsr_running()

    if not running:
        return {
            "text": "",
            "alt": "idle",
            "class": "idle",
            "tooltip": _("tooltip_idle")
        }

    # Countdown-Phase
    if state.get("state") == "countdown" and show_countdown:
        remaining = state.get("remaining", 0)
        if remaining <= 0 and "end_time" in state:
            remaining = max(0, int(state["end_time"] - time.time()))
        return {
            "text": _("countdown_text", n=remaining),
            "alt": "countdown",
            "class": "countdown",
            "tooltip": _("tooltip_countdown", n=remaining)
        }

    # Recording-Phase
    classes = "recording"
    if not no_blink:
        classes += " blink"

    return {
        "text": "",
        "alt": "recording",
        "class": classes,
        "tooltip": _("tooltip_active")
    }


def toggle_wsr():
    """Starts or stops WSR."""
    running, state = is_wsr_running()
    if running and state:
        # Send SIGINT to the actual PID
        try:
            os.kill(state["pid"], 2)  # SIGINT = 2
        except OSError:
            # Fallback to pkill
            subprocess.run(["pkill", "-INT", "-f", "wsr.main"])
    else:
        # Pass the current language to the new process if possible
        lang_flag = ""
        if _instance and _instance.lang:
            lang_flag = f"--lang {_instance.lang}"

        cmd = f"sudo -E wsr {lang_flag} -o ~/wsr_report.html > /dev/null 2>&1 &"
        subprocess.Popen(["bash", "-c", cmd])


def main():
    parser = argparse.ArgumentParser(description="WSR Waybar Module Helper")
    parser.add_argument("--toggle", action="store_true", help="Toggle recording state")
    parser.add_argument("--lang", type=str, default=None, help="Language (de, en)")
    parser.add_argument("--no-blink", action="store_true",
                        help="Disable blink animation class")
    parser.add_argument("--show-countdown", action="store_true",
                        help="Show countdown in module text")

    args = parser.parse_args()

    # Initialize i18n
    init_i18n(args.lang)

    if args.toggle:
        toggle_wsr()
    else:
        # Waybar will use the 'alt' value to pick an icon from 'format-icons'
        status = get_status(
            show_countdown=args.show_countdown,
            no_blink=args.no_blink
        )
        print(json.dumps(status))


if __name__ == "__main__":
    main()
