#!/usr/bin/env python3
import json
import subprocess
import sys
import os
import argparse

def is_wsr_running():
    """Checks if the wsr process is currently running."""
    try:
        # Match the main entry point
        output = subprocess.check_output(["pgrep", "-f", "wsr.main"]).decode().strip()
        return len(output) > 0
    except subprocess.CalledProcessError:
        return False

def get_status():
    """
    Returns the JSON structure. 
    'text' can be empty or a default, 'alt' is used for format-icons.
    """
    if is_wsr_running():
        return {
            "text": "", 
            "alt": "recording",
            "class": "recording",
            "tooltip": "WSR: Aufnahme läuft. Klicken zum Beenden."
        }
    else:
        return {
            "text": "",
            "alt": "idle",
            "class": "idle",
            "tooltip": "WSR: Inaktiv. Klicken zum Starten."
        }

def toggle_wsr():
    """Starts or stops WSR."""
    if is_wsr_running():
        subprocess.run(["pkill", "-INT", "-f", "wsr.main"])
    else:
        cmd = "sudo -E wsr -o ~/wsr_report.html > /dev/null 2>&1 &"
        subprocess.Popen(["bash", "-c", cmd])

def main():
    parser = argparse.ArgumentParser(description="WSR Waybar Module Helper")
    parser.add_argument("--toggle", action="store_true", help="Toggle recording state")
    
    args = parser.parse_args()

    if args.toggle:
        toggle_wsr()
    else:
        # Waybar will use the 'alt' value to pick an icon from 'format-icons'
        print(json.dumps(get_status()))

if __name__ == "__main__":
    main()
