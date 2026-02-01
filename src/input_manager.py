import evdev
import logging
import threading
import select
import time

logger = logging.getLogger(__name__)

class InputManager:
    def __init__(self):
        self.devices = []
        self.mouse_devices = []
        self.keyboard_devices = []
        self.running = False
        self.thread = None
        
        # Virtual mouse position (relative tracking)
        # Assuming 1920x1080 center as start, but this is arbitrary without calibration
        self.mouse_x = 960
        self.mouse_y = 540
        self.screen_width = 1920
        self.screen_height = 1080

    def find_devices(self):
        """Scans /dev/input/event* for keyboards and mice."""
        self.devices = []
        self.mouse_devices = []
        self.keyboard_devices = []

        try:
            path_list = evdev.list_devices()
        except PermissionError:
            logger.error("Keine Berechtigung für /dev/input/. Bitte als root oder User der Gruppe 'input' ausführen.")
            return

        for path in path_list:
            try:
                dev = evdev.InputDevice(path)
                caps = dev.capabilities()
                
                # Simple heuristic for classification
                is_mouse = False
                is_keyboard = False
                
                if evdev.ecodes.EV_REL in caps:
                    is_mouse = True
                
                if evdev.ecodes.EV_KEY in caps:
                    # Check for some common keys to rule out power buttons etc.
                    # This is a bit rough, can be improved.
                    if evdev.ecodes.KEY_A in caps[evdev.ecodes.EV_KEY]:
                        is_keyboard = True

                if is_mouse:
                    self.mouse_devices.append(dev)
                    self.devices.append(dev)
                    logger.debug(f"Maus gefunden: {dev.name} ({dev.path})")
                
                if is_keyboard:
                    self.keyboard_devices.append(dev)
                    # Don't add twice if it's a combo device
                    if dev not in self.devices:
                        self.devices.append(dev)
                    logger.debug(f"Tastatur gefunden: {dev.name} ({dev.path})")

            except (PermissionError, OSError) as e:
                logger.warning(f"Konnte Gerät {path} nicht öffnen: {e}")

        logger.info(f"Geräte gefunden: {len(self.mouse_devices)} Mäuse, {len(self.keyboard_devices)} Tastaturen.")

    def start(self):
        """Starts the input listening thread."""
        if not self.devices:
            self.find_devices()
        
        if not self.devices:
            logger.error("Keine Eingabegeräte gefunden. Abbruch.")
            return

        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        logger.info("Input Listener gestartet.")

    def stop(self):
        """Stops the input listening thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        
        for dev in self.devices:
            try:
                dev.close()
            except:
                pass
        logger.info("Input Listener gestoppt.")

    def _loop(self):
        """Main loop that reads events from devices."""
        # Map file descriptors to devices for quick lookup
        fd_to_dev = {dev.fd: dev for dev in self.devices}
        
        while self.running:
            try:
                # select(rlist, wlist, xlist, timeout)
                r, w, x = select.select(self.devices, [], [], 0.5)
                
                for dev in r:
                    for event in dev.read():
                        self._handle_event(dev, event)
            
            except Exception as e:
                if self.running:
                    logger.error(f"Fehler im Input-Loop: {e}")
                    time.sleep(1) # Avoid busy loop on error

    def _handle_event(self, dev, event):
        """Processes a single input event."""
        
        # --- Mouse Movement ---
        if event.type == evdev.ecodes.EV_REL:
            if event.code == evdev.ecodes.REL_X:
                self.mouse_x += event.value
            elif event.code == evdev.ecodes.REL_Y:
                self.mouse_y += event.value
            
            # Clamp to screen size (guesswork without real screen info)
            self.mouse_x = max(0, min(self.mouse_x, self.screen_width))
            self.mouse_y = max(0, min(self.mouse_y, self.screen_height))
            
            # Log only occasionally or on specific debug level to avoid spam
            # logger.debug(f"Maus: {self.mouse_x}, {self.mouse_y}")

        # --- Key Press ---
        elif event.type == evdev.ecodes.EV_KEY:
            # event.value: 0=up, 1=down, 2=hold
            if event.value == 1: # Key Down
                key_name = evdev.ecodes.KEY[event.code] if event.code in evdev.ecodes.KEY else f"UNK_{event.code}"
                logger.info(f"Taste gedrückt: {key_name} (auf {dev.name})")
            
            # --- Mouse Click ---
            # Mouse buttons are also EV_KEY
            if event.code in [evdev.ecodes.BTN_LEFT, evdev.ecodes.BTN_RIGHT, evdev.ecodes.BTN_MIDDLE]:
                 if event.value == 1:
                    btn_name = evdev.ecodes.BTN[event.code]
                    logger.info(f"Mausklick: {btn_name} bei {self.mouse_x},{self.mouse_y}")

