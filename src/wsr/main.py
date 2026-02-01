import argparse
import logging
import signal
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def signal_handler(sig, frame):
    """Handles SIGINT (Ctrl+C) for a graceful exit."""
    print("\nAbbruch durch Benutzer. Beende...")
    sys.exit(0)

def parse_arguments():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        description="WSR - Wayland Session Recorder (Python Port)"
    )
    
    parser.add_argument(
        "-o", "--out",
        type=str,
        default="output.html",
        help="Pfad zur Ausgabedatei (Standard: output.html)"
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
        default=150,
        help="Zeitintervall in ms, um Tastenanschläge zu gruppieren (Standard: 150)"
    )
    
    return parser.parse_args()

def main():
    """Main entry point of the application."""
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    args = parse_arguments()
    
    # Update logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode activated.")
    
    logger.info(f"Initialisiere WSR...")
    logger.info(f"Ausgabedatei: {args.out}")
    
    if args.countdown > 0:
        logger.info(f"Starte in {args.countdown} Sekunden...")
        try:
            for i in range(args.countdown, 0, -1):
                print(f"{i}...", end=" ", flush=True)
                time.sleep(1)
            print("Start!")
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)

    logger.info("Aufnahme gestartet (Drücke Ctrl+C zum Beenden)...")
    
    from .input_manager import InputManager
    from .screenshot_engine import ScreenshotEngine
    from .report_generator import ReportGenerator
    from .monitor_manager import MonitorManager
    from .key_buffer import KeyBuffer
    
    monitor_mgr = MonitorManager()
    input_mgr = InputManager()
    key_buffer = KeyBuffer(args.key_interval)
    # Update input_mgr screen size based on monitors
    if monitor_mgr.monitors:
        max_x = max(m['x'] + m['width'] for m in monitor_mgr.monitors)
        max_y = max(m['y'] + m['height'] for m in monitor_mgr.monitors)
        input_mgr.screen_width = max_x
        input_mgr.screen_height = max_y
        logger.info(f"Virtuelle Desktop-Größe: {max_x}x{max_y}")

    input_mgr.log_keys = not args.no_keys
    screenshot_engine = ScreenshotEngine()
    report_gen = ReportGenerator(args.out)
    
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
                    # Add to buffer, if it returns False, it means we need to flush first
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
                    rel_x, rel_y = monitor_mgr.get_relative_coordinates(event['x'], event['y'], mon_name)
                    
                    logger.info(f"Klick erkannt auf Monitor {mon_name} bei {rel_x}, {rel_y}...")
                    shot = screenshot_engine.capture(monitor_name=mon_name)
                    if shot:
                        shot_with_cursor = screenshot_engine.add_cursor(shot, rel_x, rel_y)
                        event['screenshot'] = shot_with_cursor
                    
                    captured_events.append(event)
                else:
                    captured_events.append(event)

            time.sleep(0.05)
            
    except KeyboardInterrupt:
        logger.info("Aufnahme beendet.")
    finally:
        if 'input_mgr' in locals():
            input_mgr.stop()
        
        if captured_events:
            report_gen.generate(captured_events)
        else:
            logger.warning("Keine Ereignisse aufgezeichnet.")
            
        sys.exit(0)

if __name__ == "__main__":
    main()