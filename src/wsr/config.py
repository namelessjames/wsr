"""
Configuration loading for wsr.
Uses XDG Base Directory: $XDG_CONFIG_HOME/wsr/wsr.yaml (default ~/.config/wsr/wsr.yaml).
Priority: CLI > wsr.yaml > hardcoded defaults.
"""
import os
import logging

logger = logging.getLogger(__name__)

# Default YAML content written when config file does not exist
_DEFAULT_YAML_CONTENT = """# wsr – Wayland Session Recorder
# CLI-Parameter überschreiben diese Werte.

location: "~/Pictures/wsr/"
filename_format: "report-{%datetime}.html"
out: "output.html"
style: "~/.config/wsr/style.css"
image_format: "png"
image_quality: 0.9
cursor: "system"
debug: false
capture_window_only: false
verbose: false
countdown: 3
no_keys: false
key_interval: 500
lang: null
"""

# Keys whose values are paths to expand with expanduser
_PATH_KEYS = frozenset({"location", "style", "cursor", "out"})


def get_config_dir():
    """
    Return wsr config directory per XDG Base Directory.
    Uses $XDG_CONFIG_HOME/wsr, or ~/.config/wsr if unset.
    """
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if not xdg:
        xdg = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(xdg, "wsr")


def get_config_path():
    """Return full path to wsr.yaml."""
    return os.path.join(get_config_dir(), "wsr.yaml")


def get_default_config():
    """
    Return hardcoded default config as a dict (single source of truth for lowest priority).
    """
    return {
        "location": "~/Pictures/wsr/",
        "filename_format": "report-{%datetime}.html",
        "out": "output.html",
        "style": "~/.config/wsr/style.css",
        "image_format": "png",
        "image_quality": 0.9,
        "cursor": "system",
        "debug": False,
        "capture_window_only": False,
        "verbose": False,
        "countdown": 3,
        "no_keys": False,
        "key_interval": 500,
        "lang": None,
    }


def _expand_paths(config):
    """Expand ~ in path values; leave others unchanged."""
    result = dict(config)
    for key in _PATH_KEYS:
        if key in result and result[key] is not None and isinstance(result[key], str):
            result[key] = os.path.expanduser(result[key])
    return result


def ensure_config_file():
    """
    If wsr.yaml does not exist, create config dir and write default wsr.yaml.
    """
    path = get_config_path()
    if os.path.isfile(path):
        return
    try:
        dirpath = get_config_dir()
        os.makedirs(dirpath, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(_DEFAULT_YAML_CONTENT)
        logger.debug("Created default config at %s", path)
    except OSError as e:
        logger.warning("Could not create config file %s: %s", path, e)


def load_config():
    """
    Load config: defaults + wsr.yaml (if present). Path values are expanded.
    If wsr.yaml does not exist, it is created with default content, then defaults are returned.
    """
    import yaml

    defaults = get_default_config()
    path = get_config_path()

    if not os.path.isfile(path):
        ensure_config_file()
        return _expand_paths(defaults)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as e:
        logger.warning("Could not load config from %s: %s. Using defaults.", path, e)
        return _expand_paths(defaults)

    if not isinstance(data, dict):
        return _expand_paths(defaults)

    # Merge: user file over defaults (only known keys)
    merged = dict(defaults)
    for key in defaults:
        if key in data:
            merged[key] = data[key]
    return _expand_paths(merged)
