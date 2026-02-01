import logging
import threading
import select
import time
import queue
import evdev

logger = logging.getLogger(__name__)


class InputManager:
    """
    Manages global input devices and listens for keyboard and mouse events.
    """

    def __init__(self):
        """
        Initializes the InputManager with default settings.
        """
        self.devices = []
        self.mouse_devices = []
        self.keyboard_devices = []
        self.running = False
        self.thread = None
        self.event_queue = queue.Queue()
        self.log_keys = True

        # Virtual mouse position (relative tracking)
        # Default starting position
        self.mouse_x = 960
        self.mouse_y = 540
        self.screen_width = 1920
        self.screen_height = 1080

    def find_devices(self):
        """
        Scans /dev/input/event* for keyboards and mice.
        """
        self.devices = []
        self.mouse_devices = []
        self.keyboard_devices = []

        try:
            path_list = evdev.list_devices()
        except PermissionError:
            logger.error(
                "Keine Berechtigung für /dev/input/. "
                "Bitte als root oder User der Gruppe 'input' ausführen."
            )
            return

        for path in path_list:
            try:
                dev = evdev.InputDevice(path)
                caps = dev.capabilities()

                is_mouse = False
                is_keyboard = False

                if evdev.ecodes.EV_REL in caps:
                    is_mouse = True

                if evdev.ecodes.EV_KEY in caps:
                    # Check for KEY_A to identify real keyboards
                    if evdev.ecodes.KEY_A in caps[evdev.ecodes.EV_KEY]:
                        is_keyboard = True

                if is_mouse:
                    self.mouse_devices.append(dev)
                    self.devices.append(dev)
                    logger.debug(f"Maus gefunden: {dev.name} ({dev.path})")

                if is_keyboard:
                    self.keyboard_devices.append(dev)
                    if dev not in self.devices:
                        self.devices.append(dev)
                    logger.debug(f"Tastatur gefunden: {dev.name} ({dev.path})")

            except (PermissionError, OSError) as e:
                logger.warning(f"Konnte Gerät {path} nicht öffnen: {e}")

        logger.info(
            f"Geräte gefunden: {len(self.mouse_devices)} Mäuse, "
            f"{len(self.keyboard_devices)} Tastaturen."
        )

    def start(self):
        """
        Starts the input listening thread.
        """
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
        """
        Stops the input listening thread and closes devices.
        """
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

        for dev in self.devices:
            try:
                dev.close()
            except Exception:
                pass
        logger.info("Input Listener gestoppt.")

    def _loop(self):
        """
        Main loop that reads events from devices.
        """
        while self.running:
            try:
                # select(rlist, wlist, xlist, timeout)
                r, _, _ = select.select(self.devices, [], [], 0.5)

                for dev in r:
                    for event in dev.read():
                        self._handle_event(dev, event)

            except Exception as e:
                if self.running:
                    logger.error(f"Fehler im Input-Loop: {e}")
                    time.sleep(1)

    def _handle_event(self, dev, event):
        """
        Processes a single input event.
        """
        # --- Mouse Movement ---
        if event.type == evdev.ecodes.EV_REL:
            if event.code == evdev.ecodes.REL_X:
                self.mouse_x += event.value
            elif event.code == evdev.ecodes.REL_Y:
                self.mouse_y += event.value

            # Clamp to screen size
            self.mouse_x = max(0, min(self.mouse_x, self.screen_width))
            self.mouse_y = max(0, min(self.mouse_y, self.screen_height))

        # --- Key Press ---
        elif event.type == evdev.ecodes.EV_KEY:
            # Mouse buttons are also EV_KEY
            is_mbutton = event.code in [
                evdev.ecodes.BTN_LEFT,
                evdev.ecodes.BTN_RIGHT,
                evdev.ecodes.BTN_MIDDLE
            ]

            if is_mbutton:
                if event.value == 1:
                    btn_name = evdev.ecodes.BTN[event.code]
                    logger.info(
                        f"Mausklick: {btn_name} bei {self.mouse_x},{self.mouse_y}"
                    )
                    self.event_queue.put({
                        'type': 'click',
                        'button': btn_name,
                        'x': self.mouse_x,
                        'y': self.mouse_y,
                        'time': time.time()
                    })
            elif self.log_keys and event.value == 1:  # Key Down
                key_name = (
                    evdev.ecodes.KEY[event.code]
                    if event.code in evdev.ecodes.KEY
                    else f"UNK_{event.code}"
                )
                logger.info(f"Taste gedrückt: {key_name} (auf {dev.name})")
                self.event_queue.put({
                    'type': 'key',
                    'key': key_name,
                    'time': time.time()
                })