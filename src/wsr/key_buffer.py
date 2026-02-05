import time


class KeyBuffer:
    """
    Groups rapid keystrokes into a single string event based on a timeout.
    """

    def __init__(self, interval_ms):
        """
        Initializes the KeyBuffer.

        Args:
            interval_ms (int): Max time in ms between keys to be grouped.

        Raises:
            ValueError: If interval_ms is negative.
        """
        if interval_ms < 0:
            raise ValueError("interval_ms must be non-negative")
        self.interval = interval_ms / 1000.0
        self.buffer = []
        self.last_time = 0

    def add(self, key_name):
        """
        Adds a key to the buffer if within the interval.

        Args:
            key_name (str): The raw Linux key name (e.g., 'KEY_A').

        Returns:
            bool: True if added, False if buffer needs flushing first.
        """
        char = self._map_key(key_name)
        now = time.time()

        if not self.buffer or (now - self.last_time) <= self.interval:
            self.buffer.append(char)
            self.last_time = now
            return True
        return False

    def is_timed_out(self):
        """
        Checks if the buffer has timed out.

        Returns:
            bool: True if the interval has passed since the last key.
        """
        if not self.buffer:
            return False
        return (time.time() - self.last_time) > self.interval

    def flush(self):
        """
        Clears the buffer and returns the concatenated string.

        Returns:
            str or None: The grouped text or None if empty.
        """
        if not self.buffer:
            return None
        text = "".join(self.buffer)
        self.buffer = []
        return text

    def _map_key(self, key_name):
        """
        Internal helper to map Linux keycodes to readable characters.
        """
        if not key_name:
            return ""
        if key_name.startswith("KEY_"):
            k = key_name[4:]
            if len(k) == 1:
                return k
            if k == "SPACE":
                return " "
            if k == "ENTER":
                return "\n"
            if k == "BACKSPACE":
                return "⌫"
            return f"[{k}]"
        return key_name