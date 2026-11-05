"""Structural checks for real probe captures; these are not fake router fixtures."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("junction_route_probe", Path(__file__).parents[1] / "route_probe.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class CaptureValidationTests(unittest.TestCase):
    def fixture(self):
        return {"probeVersion": 1, "status": "captured", "coherent": True,
                "locationCount": 2, "locationsLatLon": [[41.0, 12.0], [41.001, 12.001]],
                "locationSegmentIds": ["s0", "s0"], "segments": [{"id": "s0", "attachments": []}],
                "directions": [{"routePointOffset": 1}]}

    def test_indexed_route_is_accepted(self):
        self.assertEqual(probe.validate(self.fixture()), [])

    def test_unknown_segment_reference_is_rejected(self):
        value = self.fixture()
        value["locationSegmentIds"][1] = "missing"
        self.assertTrue(probe.validate(value))

    def test_out_of_route_maneuver_is_rejected(self):
        value = self.fixture()
        value["directions"][0]["routePointOffset"] = 2
        self.assertTrue(probe.validate(value))

    def test_changed_and_unavailable_captures_are_not_success(self):
        for field, replacement in [("coherent", False), ("status", "unavailable"), ("probeVersion", 2)]:
            value = self.fixture()
            value[field] = replacement
            self.assertTrue(probe.validate(value))

    def test_nonfinite_location_is_rejected(self):
        value = self.fixture()
        value["locationsLatLon"][0][0] = float("nan")
        self.assertTrue(probe.validate(value))
