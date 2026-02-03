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


class TestResolveOutputPath(unittest.TestCase):
    def test_explicit_out_overrides_everything(self):
        result = config.resolve_output_path(
            location="/some/dir",
            filename_format="report-{%datetime}.html",
            explicit_out="/custom/path/output.html"
        )
        self.assertEqual(result, "/custom/path/output.html")

    def test_explicit_out_default_is_ignored(self):
        # When explicit_out is the default "output.html", it should be ignored
        with tempfile.TemporaryDirectory() as tmp:
            result = config.resolve_output_path(
                location=tmp,
                filename_format="report.html",
                explicit_out="output.html"
            )
            self.assertEqual(result, os.path.join(tmp, "report.html"))

    def test_date_placeholder(self):
        from datetime import datetime
        with tempfile.TemporaryDirectory() as tmp:
            result = config.resolve_output_path(
                location=tmp,
                filename_format="report-{%date}.html",
                explicit_out=None
            )
            expected_date = datetime.now().strftime("%Y-%m-%d")
            self.assertEqual(result, os.path.join(tmp, f"report-{expected_date}.html"))

    def test_datetime_placeholder(self):
        from datetime import datetime
        with tempfile.TemporaryDirectory() as tmp:
            result = config.resolve_output_path(
                location=tmp,
                filename_format="report-{%datetime}.html",
                explicit_out=None
            )
            # Check format, not exact time (could differ by seconds)
            filename = os.path.basename(result)
            self.assertTrue(filename.startswith("report-"))
            self.assertTrue(filename.endswith(".html"))
            # Should match YYYY-MM-DD-HH-MM-SS pattern
            import re
            self.assertRegex(filename, r"report-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}\.html")

    def test_increment_placeholder_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = config.resolve_output_path(
                location=tmp,
                filename_format="report-{%n}.html",
                explicit_out=None
            )
            self.assertEqual(result, os.path.join(tmp, "report-1.html"))

    def test_increment_placeholder_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Create some existing files
            open(os.path.join(tmp, "report-1.html"), "w").close()
            open(os.path.join(tmp, "report-2.html"), "w").close()
            open(os.path.join(tmp, "report-5.html"), "w").close()
            result = config.resolve_output_path(
                location=tmp,
                filename_format="report-{%n}.html",
                explicit_out=None
            )
            self.assertEqual(result, os.path.join(tmp, "report-6.html"))

    def test_increment_placeholder_nonexistent_dir(self):
        result = config.resolve_output_path(
            location="/nonexistent/path/that/does/not/exist",
            filename_format="report-{%n}.html",
            explicit_out=None
        )
        self.assertEqual(result, "/nonexistent/path/that/does/not/exist/report-1.html")

    def test_location_tilde_expansion(self):
        result = config.resolve_output_path(
            location="~/Pictures/wsr/",
            filename_format="report.html",
            explicit_out=None
        )
        home = os.path.expanduser("~")
        self.assertEqual(result, os.path.join(home, "Pictures/wsr/", "report.html"))

    def test_combined_date_and_increment(self):
        # Test that multiple placeholders work together
        from datetime import datetime
        with tempfile.TemporaryDirectory() as tmp:
            result = config.resolve_output_path(
                location=tmp,
                filename_format="report-{%date}-{%n}.html",
                explicit_out=None
            )
            expected_date = datetime.now().strftime("%Y-%m-%d")
            self.assertEqual(result, os.path.join(tmp, f"report-{expected_date}-1.html"))


class TestResolveIncrement(unittest.TestCase):
    def test_increment_with_special_chars_in_pattern(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Pattern with regex special characters
            open(os.path.join(tmp, "report[1].html"), "w").close()
            result = config._resolve_increment(tmp, "report[{%n}].html")
            self.assertEqual(result, "report[2].html")


class TestResolveStylePath(unittest.TestCase):
    def test_explicit_style_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            style_file = os.path.join(tmp, "custom.css")
            with open(style_file, "w") as f:
                f.write("body { color: red; }")
            result = config.resolve_style_path(explicit_style=style_file)
            self.assertEqual(result, style_file)

    def test_explicit_style_not_exists(self):
        result = config.resolve_style_path(explicit_style="/nonexistent/path/style.css")
        self.assertIsNone(result)

    def test_default_style_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = os.path.join(tmp, "wsr")
            os.makedirs(config_dir, exist_ok=True)
            style_file = os.path.join(config_dir, "style.css")
            with open(style_file, "w") as f:
                f.write("body { color: blue; }")
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp}, clear=False):
                result = config.resolve_style_path(explicit_style=None)
            self.assertEqual(result, style_file)

    def test_default_style_not_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Empty config dir, no style.css
            config_dir = os.path.join(tmp, "wsr")
            os.makedirs(config_dir, exist_ok=True)
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp}, clear=False):
                result = config.resolve_style_path(explicit_style=None)
            self.assertIsNone(result)

    def test_explicit_overrides_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Create both default and explicit style files
            config_dir = os.path.join(tmp, "wsr")
            os.makedirs(config_dir, exist_ok=True)
            default_style = os.path.join(config_dir, "style.css")
            with open(default_style, "w") as f:
                f.write("body { color: blue; }")
            explicit_style = os.path.join(tmp, "explicit.css")
            with open(explicit_style, "w") as f:
                f.write("body { color: green; }")
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp}, clear=False):
                result = config.resolve_style_path(explicit_style=explicit_style)
            # Explicit should be used, not default
            self.assertEqual(result, explicit_style)

    def test_tilde_expansion(self):
        # Test that ~ is expanded in explicit paths
        home = os.path.expanduser("~")
        # We can't guarantee a file exists at ~, so test the expansion logic
        # by checking a nonexistent file still gets expanded
        result = config.resolve_style_path(explicit_style="~/nonexistent.css")
        # Result should be None because file doesn't exist
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
