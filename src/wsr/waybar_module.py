#!/usr/bin/env python3
import json
import subprocess
import sys
import os
import argparse

# Add package dir to path for imports to work when run as script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wsr.i18n import _, init_i18n, _instance

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
            "tooltip": _("tooltip_active")
        }
    else:
        return {
            "text": "",
            "alt": "idle",
            "class": "idle",
            "tooltip": _("tooltip_idle")
        }

def toggle_wsr():
    """Starts or stops WSR."""
    from wsr.i18n import _instance
    if is_wsr_running():
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
    
    args = parser.parse_args()
    
    # Initialize i18n
    init_i18n(args.lang)

    if args.toggle:
        toggle_wsr()
    else:
        # Waybar will use the 'alt' value to pick an icon from 'format-icons'
        print(json.dumps(get_status()))

if __name__ == "__main__":
    main()
