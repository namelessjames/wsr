import json
import os
import re
import locale
import logging

logger = logging.getLogger(__name__)

# Strict pattern for language codes – only lowercase ASCII, exactly 2 chars.
_LANG_RE = re.compile(r"^[a-z]{2}$")


class I18n:
    """
    Simple JSON-based localization helper.
    """
    def __init__(self, lang=None):
        self.translations = {}
        raw = lang or self._detect_language()
        # Sanitize: only accept strictly valid language codes.
        # Anything else falls back to 'en' – no path traversal, no injection.
        self.lang = raw if _LANG_RE.match(raw) else "en"
        self._load_translations()

    def _detect_language(self):
        """Detects system language, defaults to 'en'."""
        try:
            # e.g. 'de_DE.UTF-8' -> 'de'
            sys_lang = locale.getdefaultlocale()[0]
            if sys_lang:
                return sys_lang.split('_')[0]
        except Exception:
            pass
        return 'en'

    def _load_translations(self):
        """Loads the JSON file for the current language."""
        base_dir = os.path.dirname(__file__)
        path = os.path.join(base_dir, "locales", f"{self.lang}.json")
        
        # Fallback to English if file not found
        if not os.path.exists(path):
            path = os.path.join(base_dir, "locales", "en.json")
            self.lang = 'en'

        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        except Exception as e:
            logger.error(f"Could not load translations: {e}")
            self.translations = {}

    def translate(self, msg_key, **kwargs):
        """Translates a key and formats it with kwargs."""
        text = self.translations.get(msg_key, msg_key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text
        return text

# Global instance for easy use
_instance = None

def init_i18n(lang=None):
    global _instance
    _instance = I18n(lang)

def _(msg_key, **kwargs):
    if _instance is None:
        init_i18n()
    return _instance.translate(msg_key, **kwargs)