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
    
    from src.input_manager import InputManager
    from src.screenshot_engine import ScreenshotEngine
    from src.report_generator import ReportGenerator
    
    input_mgr = InputManager()
    screenshot_engine = ScreenshotEngine()
    report_gen = ReportGenerator(args.out)
    
    captured_events = []
    
    try:
        input_mgr.start()
        
        while True:
            while not input_mgr.event_queue.empty():
                event = input_mgr.event_queue.get()
                logger.debug(f"Event verarbeitet: {event}")
                
                if event['type'] == 'click':
                    logger.info(f"Klick erkannt. Erstelle Screenshot an {event['x']}, {event['y']}...")
                    shot = screenshot_engine.capture()
                    if shot:
                        shot_with_cursor = screenshot_engine.add_cursor(shot, event['x'], event['y'])
                        event['screenshot'] = shot_with_cursor
                    
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