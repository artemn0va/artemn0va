import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from scripts import update_profile as profile


class ProfileCardsTest(unittest.TestCase):
    def test_service_error_cannot_replace_a_working_card(self):
        good = b'<svg xmlns="http://www.w3.org/2000/svg"><text>Working card</text></svg>'
        bad = b'<svg xmlns="http://www.w3.org/2000/svg"><text>Something went wrong!</text></svg>'
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(profile, "ASSETS", Path(folder)):
                profile.write_svg("stats.svg", good)
                for content in (bad, b"Payment required", b"<html>Service unavailable</html>"):
                    with self.assertRaises((ValueError, ET.ParseError)):
                        profile.write_svg("stats.svg", content)
                    self.assertEqual((Path(folder) / "stats.svg").read_bytes(), good)

    def test_empty_activity_is_a_real_zero_graph(self):
        today = date(2026, 10, 22)
        days = {(today - timedelta(days=i)).isoformat(): 0 for i in range(31)}
        root = ET.fromstring(profile.render_activity(days, today))
        self.assertEqual(len(root.findall(f".//{{{profile.SVG_NS}}}circle")), 31)
        self.assertIn("0 contributions from 2026-09-22 through 2026-10-22", " ".join(root.itertext()))

    def test_missing_activity_is_not_silently_reported_as_zero(self):
        with self.assertRaises(KeyError):
            profile.render_activity({}, date(2026, 10, 22))

    def test_language_padding_preserves_content_coordinates(self):
        source = b'<svg xmlns="http://www.w3.org/2000/svg" width="495" height="190" viewBox="0 0 495 190"><text x="25" y="35">Languages</text></svg>'
        root = ET.fromstring(profile.pad_languages_card(source))
        self.assertEqual(root.get("height"), "195")
        self.assertEqual(root.get("viewBox"), "0 0 495 195")
        self.assertEqual(root.find(f"{{{profile.SVG_NS}}}text").get("y"), "35")


if __name__ == "__main__":
    unittest.main()
