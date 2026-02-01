import time

class KeyBuffer:
    def __init__(self, interval_ms):
        self.interval = interval_ms / 1000.0
        self.buffer = []
        self.last_time = 0

    def add(self, key_name):
        # Mapping for better readability
        char = self._map_key(key_name)
        
        now = time.time()
        # If buffer is empty or within interval, add to buffer
        if not self.buffer or (now - self.last_time) <= self.interval:
            self.buffer.append(char)
            self.last_time = now
            return True
        return False # Buffer should be flushed before adding this key

    def is_timed_out(self):
        if not self.buffer:
            return False
        return (time.time() - self.last_time) > self.interval

    def flush(self):
        if not self.buffer:
            return None
        text = "".join(self.buffer)
        self.buffer = []
        return text

    def _map_key(self, key_name):
        # Very basic mapping, can be expanded
        if key_name.startswith("KEY_"):
            k = key_name[4:]
            if len(k) == 1:
                return k # A, B, C...
            if k == "SPACE":
                return " "
            if k == "ENTER":
                return "\n"
            if k == "BACKSPACE":
                return "⌫"
            return f"[{k}]"
        return key_name
