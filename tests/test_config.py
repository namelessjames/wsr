"""Unit tests for wsr.config."""
import os
import tempfile
import unittest
from unittest.mock import patch

from wsr import config


class TestConfigPaths(unittest.TestCase):
    def test_get_config_dir_uses_xdg_config_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp}, clear=False):
                dir_path = config.get_config_dir()
            self.assertEqual(dir_path, os.path.join(tmp, "wsr"))

    def test_get_config_dir_fallback_when_xdg_unset(self):
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": ""}, clear=False):
            dir_path = config.get_config_dir()
        home = os.path.expanduser("~")
        self.assertEqual(dir_path, os.path.join(home, ".config", "wsr"))

    def test_get_config_dir_strips_whitespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp + "  "}, clear=False):
                dir_path = config.get_config_dir()
            self.assertEqual(dir_path, os.path.join(tmp.strip(), "wsr"))

    def test_get_config_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp}, clear=False):
                path = config.get_config_path()
            self.assertEqual(path, os.path.join(tmp, "wsr", "wsr.yaml"))


class TestDefaultConfig(unittest.TestCase):
    def test_get_default_config_has_expected_keys(self):
        defaults = config.get_default_config()
        expected = {
            "location", "filename_format", "out", "style",
            "image_format", "image_quality", "cursor", "debug",
            "capture_window_only", "verbose", "countdown", "no_keys",
            "key_interval", "lang",
        }
        self.assertEqual(set(defaults.keys()), expected)

    def test_get_default_config_values(self):
        defaults = config.get_default_config()
        self.assertEqual(defaults["out"], "output.html")
        self.assertEqual(defaults["countdown"], 3)
        self.assertEqual(defaults["key_interval"], 500)
        self.assertIsNone(defaults["lang"])
        self.assertFalse(defaults["verbose"])
        self.assertFalse(defaults["no_keys"])


class TestEnsureAndLoadConfig(unittest.TestCase):
    def test_load_config_creates_file_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp}, clear=False):
                cfg = config.load_config()
                path = config.get_config_path()  # path while env is patched
            self.assertTrue(os.path.isfile(path))
            self.assertEqual(cfg["out"], "output.html")
            self.assertEqual(cfg["countdown"], 3)

    def test_load_config_merges_file_over_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = os.path.join(tmp, "wsr")
            os.makedirs(config_dir, exist_ok=True)
            yaml_path = os.path.join(config_dir, "wsr.yaml")
            with open(yaml_path, "w", encoding="utf-8") as f:
                f.write("countdown: 10\nout: custom.html\n")
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp}, clear=False):
                cfg = config.load_config()
            self.assertEqual(cfg["countdown"], 10)
            self.assertEqual(cfg["out"], "custom.html")
            self.assertEqual(cfg["key_interval"], 500)

    def test_load_config_expands_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = os.path.join(tmp, "wsr")
            os.makedirs(config_dir, exist_ok=True)
            yaml_path = os.path.join(config_dir, "wsr.yaml")
            with open(yaml_path, "w", encoding="utf-8") as f:
                f.write('location: "~/Pictures/wsr/"\n')
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp}, clear=False):
                cfg = config.load_config()
            self.assertEqual(cfg["location"], os.path.expanduser("~/Pictures/wsr/"))

    def test_load_config_invalid_yaml_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = os.path.join(tmp, "wsr")
            os.makedirs(config_dir, exist_ok=True)
            yaml_path = os.path.join(config_dir, "wsr.yaml")
            with open(yaml_path, "w", encoding="utf-8") as f:
                f.write("invalid: yaml: content:\n")
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp}, clear=False):
                cfg = config.load_config()
            self.assertEqual(cfg["out"], "output.html")
            self.assertEqual(cfg["countdown"], 3)


if __name__ == "__main__":
    unittest.main()
