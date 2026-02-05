import argparse
import logging
import signal
import sys
import time
import os
import subprocess

# Local package imports
from .input_manager import InputManager
from .screenshot_engine import ScreenshotEngine
from .screenshot_worker import ScreenshotWorker
from .report_generator import ReportGenerator
from .monitor_manager import MonitorManager
from .key_buffer import KeyBuffer
from .i18n import _, init_i18n, _instance
from .config import load_config, resolve_output_path, resolve_style_path, ConfigError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def signal_handler(sig, frame):
    """
    Handles SIGINT (Ctrl+C) for a graceful exit.
    """
    print(f"\n{_('abort_user')}")
    sys.exit(0)


def send_notification(title, message, file_path=None):
    """
    Sends a system notification as the original user via notify-send.

    Args:
        title (str): The title of the notification.
        message (str): The message body of the notification.
        file_path (str, optional): Path to the report file to open on click.
    """
    sudo_user = os.environ.get("SUDO_USER")
    if not sudo_user:
        # Not running as sudo, just send it
        try:
            if file_path:
                abs_path = os.path.abspath(file_path)
                inner_cmd = (
                    f'ACTION=$(notify-send "{title}" "{message}" ' 
                    f'--action="default={_('gui_open')}" -i info); ' 
                    f'[ "$ACTION" == "default" ] && xdg-open "{abs_path}"'
                )
                subprocess.Popen(
                    ["bash", "-c", inner_cmd],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL
                )
            else:
                subprocess.Popen(
                    ["notify-send", title, message, "-i", "error"],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL
                )
        except Exception:
            pass
        return

    try:
        import pwd
        pw = pwd.getpwnam(sudo_user)
        uid = pw.pw_uid
        gid = pw.pw_gid
        home = pw.pw_dir

        # Prepare environment for the user
        env = os.environ.copy()
        env["HOME"] = home
        env["USER"] = sudo_user
        env["LOGNAME"] = sudo_user
        env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
        if "DBUS_SESSION_BUS_ADDRESS" not in env:
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{uid}/bus"

        def drop_privileges():
            os.setgid(gid)
            os.setuid(uid)

        if file_path:
            abs_path = os.path.abspath(file_path)
            # Use a shell script to catch the action
            inner_cmd = (
                f'ACTION=$(notify-send "{title}" "{message}" ' 
                f'--action="default={_('gui_open')}" -i info); ' 
                f'[ "$ACTION" == "default" ] && xdg-open "{abs_path}"'
            )
            subprocess.Popen(
                ["bash", "-c", inner_cmd],
                preexec_fn=drop_privileges,
                env=env,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL
            )
        else:
            subprocess.Popen(
                ["notify-send", title, message, "-i", "error"],
                preexec_fn=drop_privileges,
                env=env,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL
            )

    except Exception as e:
        logger.debug(f"Konnte Benachrichtigung nicht senden: {e}")
        # Fallback: Print to stderr
        print(f"\n[{title}] {message}")


def parse_arguments():
    """
    Parses command line arguments.
    Config: CLI overrides wsr.yaml over hardcoded defaults.
    Returns:
        argparse.Namespace: The parsed arguments.
    """
    config = load_config()

    parser = argparse.ArgumentParser(
        description="WSR - Wayland Session Recorder (Python Port)"
    )

    parser.add_argument(
        "-o", "--out",
        type=str,
        default="output.html",
        help="Expliziter Pfad zur Ausgabedatei (überschreibt location + filename-format)"
    )

    parser.add_argument(
        "-l", "--location",
        type=str,
        default="~/Pictures/wsr/",
        help="Zielverzeichnis für Reports (Standard: ~/Pictures/wsr/)"
    )

    parser.add_argument(
        "-f", "--filename-format",
        type=str,
        dest="filename_format",
        default="report-{%datetime}.html",
        help="Dateinamen-Format mit Platzhaltern: {%%date}, {%%datetime}, {%%n}"
    )

    parser.add_argument(
        "-s", "--style",
        type=str,
        default=None,
        help="Pfad zu eigener CSS-Datei (überschreibt Default-Styles)"
    )

    parser.add_argument(
        "--image-format",
        choices=["png", "jpg", "webp"],
        default="png",
        help="Bildformat der Screenshots (Standard: png)"
    )

    def quality_type(x):
        x = float(x)
        if x < 0.1 or x > 1.0:
            raise argparse.ArgumentTypeError("Qualität muss zwischen 0.1 und 1.0 liegen")
        return x

    parser.add_argument(
        "--image-quality",
        type=quality_type,
        default=0.9,
        help="Qualitätsfaktor für jpg/webp (0.1-1.0, Standard: 0.9)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Aktiviert ausführliches Logging (DEBUG Level)"
    )

    parser.add_argument(
        "--countdown",
        type=int,
        default=3,
        help="Verzögerung vor dem Start in Sekunden (Standard: 3)"
    )

    parser.add_argument(
        "--no-keys",
        action="store_true",
        help="Deaktiviert das Loggen von Tastatureingaben (Sicherheitsmodus)"
    )

    parser.add_argument(
        "--key-interval",
        type=int,
        default=500,
        help="Zeitintervall in ms, um Tastenanschläge zu gruppieren (Standard: 500)"
    )

    parser.add_argument(
        "--lang",
        type=str,
        default=None,
        help="Sprache wählen (de, en). Standard: System-Sprache."
    )

    parser.set_defaults(**config)
    return parser.parse_args()


def main():
    """
    Main entry point of the application.
    """
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)

    try:
        args = parse_arguments()
    except ConfigError as e:
        print(f"Configuration error:\n{e}", file=sys.stderr)
        sys.exit(1)

    # Initialize i18n
    init_i18n(args.lang)

    # Resolve output path from location + filename_format (or explicit -o)
    output_path = resolve_output_path(args.location, args.filename_format, args.out)

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Update logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode activated.")

    logger.info(_("initializing"))
    logger.info(_("output_file", path=output_path))

    if args.countdown > 0:
        logger.info(_("starting_in", n=args.countdown))
        try:
            for i in range(args.countdown, 0, -1):
                print(f"{i}...", end=" ", flush=True)
                time.sleep(1)
            print("Start!")
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)

    logger.info(_("recording_started"))

    monitor_mgr = MonitorManager()
    input_mgr = InputManager(cursor_position_fn=monitor_mgr.get_cursor_position)
    key_buffer = KeyBuffer(args.key_interval)

    if monitor_mgr.monitors:
        max_x = max(m['x'] + m['width'] for m in monitor_mgr.monitors)
        max_y = max(m['y'] + m['height'] for m in monitor_mgr.monitors)
        logger.info(_("virtual_desktop_size", width=max_x, height=max_y))

    input_mgr.log_keys = not args.no_keys
    screenshot_engine = ScreenshotEngine()
    screenshot_worker = ScreenshotWorker(screenshot_engine, max_workers=2)

    # Resolve style path and get language for report
    style_path = resolve_style_path(args.style)
    lang = _instance.lang if _instance else "en"
    report_gen = ReportGenerator(
        output_path,
        lang=lang,
        custom_style_path=style_path,
        image_format=args.image_format,
        image_quality=args.image_quality
    )

    captured_events = []

    try:
        input_mgr.start()

        while True:
            # Check for key buffer timeout
            if key_buffer.is_timed_out():
                text = key_buffer.flush()
                if text:
                    captured_events.append({
                        'type': 'key_group',
                        'text': text,
                        'time': time.time()
                    })

            while not input_mgr.event_queue.empty():
                event = input_mgr.event_queue.get()
                logger.debug(f"Event verarbeitet: {event}")

                if event['type'] == 'key':
                    # Add to buffer, if it returns False, flush first
                    if not key_buffer.add(event['key']):
                        text = key_buffer.flush()
                        if text:
                            captured_events.append({
                                'type': 'key_group',
                                'text': text,
                                'time': event['time']
                            })
                        key_buffer.add(event['key'])

                elif event['type'] == 'click':
                    # Flush buffer on click to ensure order
                    text = key_buffer.flush()
                    if text:
                        captured_events.append({
                            'type': 'key_group',
                            'text': text,
                            'time': event['time']
                        })

                    # Determine monitor
                    mon_name = monitor_mgr.get_monitor_at(event['x'], event['y'])
                    rel_x, rel_y = monitor_mgr.get_relative_coordinates(
                        event['x'], event['y'], mon_name
                    )

                    logger.info(
                        _("click_on_monitor", name=mon_name, x=rel_x, y=rel_y)
                    )
                    # Event sofort zur Liste hinzufügen (ohne Screenshot)
                    captured_events.append(event)
                    # Screenshot asynchron anfordern - wird in-place zum Event hinzugefügt
                    screenshot_worker.request_screenshot(
                        event,
                        mon_name,
                        rel_x,
                        rel_y,
                        image_format=args.image_format,
                        image_quality=int(args.image_quality * 100)
                    )
                else:
                    captured_events.append(event)

            time.sleep(0.05)

    except KeyboardInterrupt:
        logger.info(_("recording_stopped"))
    except Exception as e:
        error_msg = _("error_unexpected", error=str(e))
        logger.error(error_msg)
        send_notification(_("notif_error_title"), error_msg)
    finally:
        if 'input_mgr' in locals():
            input_mgr.stop()

        # Warte auf ausstehende Screenshots (mit Timeout)
        if 'screenshot_worker' in locals():
            pending = screenshot_worker.pending_count()
            if pending > 0:
                logger.info(_("waiting_screenshots", n=pending))
            screenshot_worker.wait_for_pending(timeout=5.0)
            screenshot_worker.shutdown(wait=False)

        if captured_events:
            logger.info(_("generating_report", n=len(captured_events)))
            report_gen.generate(captured_events)
            send_notification(
                _("notif_success_title"),
                _("notif_success_message", path=output_path),
                file_path=output_path
            )
        else:
            logger.warning(_("no_events"))

        sys.exit(0)


if __name__ == "__main__":
    main()