"""Regression checks for truthful setup readiness; no SDK/device is required."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("junction_dev", Path(__file__).parents[1] / "dev.py")
dev = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev)


class DoctorTests(unittest.TestCase):
    def run_doctor(self, overrides):
        healthy = {"present": True, "ok": True}
        with tempfile.TemporaryDirectory() as tmp:
            with patch.multiple(
                dev,
                check_java=lambda cfg: overrides.get("java", healthy),
                check_gradle_wrapper=lambda: healthy,
                check_android_sdk=lambda cfg: healthy,
                check_ndk=lambda cfg: healthy,
                check_sibling=lambda name, markers: overrides.get(name, healthy),
                check_garmin=lambda cfg: overrides.get("garmin_sdk", healthy),
                check_adb=lambda cfg: overrides.get("adb", healthy),
            ):
                code = dev.doctor({}, Path(tmp))
            return code, json.loads((Path(tmp) / "environment.json").read_text())

    def test_broken_installed_optional_capability_is_reported(self):
        code, report = self.run_doctor({"garmin_sdk": {"present": True, "ok": False}})
        self.assertEqual(code, 0)  # Android baseline can still be built.
        self.assertIn("garmin_sdk", report["missing_optional"])
        self.assertEqual(report["status"], "ready_with_warnings")

    def test_build_helper_checkout_is_required(self):
        code, report = self.run_doctor({"build": {"present": False}})
        self.assertEqual(code, 1)
        self.assertIn("build_dir", report["missing_required"])

    def test_adb_can_be_found_in_configured_sdk(self):
        with tempfile.TemporaryDirectory() as tmp:
            adb = Path(tmp) / "platform-tools" / "adb"
            adb.parent.mkdir()
            adb.touch()
            with patch.object(dev.shutil, "which", return_value=None), patch.object(
                dev, "run", return_value=(0, "List of devices attached\nTEST device\n", "")
            ) as run:
                result = dev.check_adb({"android_sdk": tmp})
            self.assertTrue(result["ok"])
            self.assertEqual(run.call_args.args[0][0], str(adb))

    def test_multiple_adb_devices_need_explicit_selection(self):
        with patch.object(dev.shutil, "which", return_value="/tool/adb"), patch.object(
            dev, "run", return_value=(0, "List of devices attached\nA device\nB device\n", "")
        ):
            self.assertFalse(dev.check_adb({})["ok"])
            self.assertTrue(dev.check_adb({"adb_serial": "B"})["ok"])

    def test_nonzero_java_exit_is_not_healthy(self):
        with patch.object(dev.shutil, "which", return_value="/tool/java"), patch.object(
            dev, "run", return_value=(1, "", 'openjdk version "21.0.1"\nfailed to start')
        ):
            self.assertFalse(dev.check_java({})["ok"])

    def test_garmin_compiler_without_device_profile_is_not_watch_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bin").mkdir()
            for name in ("monkeyc", "connectiq", "simulator"):
                (root / "bin" / name).touch()
            key = root / "development.pem"
            key.touch()
            with patch.object(dev, "run", return_value=(0, "Compiler 9.3.0", "")):
                result = dev.check_garmin({
                    "garmin_sdk": tmp,
                    "garmin_key": str(key),
                    "garmin_device_dir": str(root / "devices" / "fr970"),
                })
            self.assertFalse(result["ok"])
            self.assertIn("profile", result["detail"].lower())

    def test_wrapper_without_jar_and_properties_is_not_healthy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "gradlew").touch()
            with patch.object(dev, "REPO_ROOT", root):
                self.assertFalse(dev.check_gradle_wrapper()["ok"])

    def test_2048_bit_signing_key_is_rejected_before_compiling(self):
        with patch.object(dev, "run", return_value=(0, "Modulus=" + "F" * 512, "")):
            self.assertFalse(dev.check_signing_key(Path("test.der"))["ok"])

    def test_4096_bit_rsa_key_is_accepted(self):
        with patch.object(dev, "run", return_value=(0, "Modulus=" + "F" * 1024, "")):
            self.assertTrue(dev.check_signing_key(Path("test.der"))["ok"])


class WatchBuildTests(unittest.TestCase):
    def test_blocked_build_removes_previous_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "Junction.prg").write_bytes(b"previous successful build")
            with patch.object(dev, "check_garmin", return_value={"ok": False, "detail": "invalid signing key"}):
                self.assertNotEqual(dev.build_watch({}, out), 0)
            self.assertFalse((out / "Junction.prg").exists())
            self.assertEqual(json.loads((out / "build.json").read_text())["status"], "blocked")


class WatchSmokeTests(unittest.TestCase):
    def test_accepts_only_current_build_and_actual_970_frame_dimensions(self):
        self.assertFalse(dev.watch_frame_seen("JUNCTION_START build=T02-3", "T02-3"))
        self.assertFalse(dev.watch_frame_seen("JUNCTION_FRAME build=T02-2 width=454 height=454", "T02-3"))
        self.assertFalse(dev.watch_frame_seen("JUNCTION_FRAME build=T02-3 width=0 height=0", "T02-3"))
        self.assertTrue(dev.watch_frame_seen("JUNCTION_FRAME build=T02-3 width=454 height=454\r\n", "T02-3"))

    def test_failed_rebuild_never_attempts_simulator_deployment(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(dev, "build_watch", return_value=1), patch.object(dev.subprocess, "Popen") as launch:
                self.assertEqual(dev.watch_smoke({}, Path(tmp), 1), 1)
            launch.assert_not_called()


class EchoEvidenceTests(unittest.TestCase):
    def fixture(self, epoch="new"):
        watch = "JUNCTION_ECHO_REQUEST epoch=new id=1 displayed=0\n"
        watch += "\n".join(f"JUNCTION_ECHO_DISPLAY id={n}" for n in range(1, 7))
        phone = [{"transport": "TETHERED", "event": f"REQUEST epoch={epoch} id={n + 1} displayed={n}"} for n in range(1, 6)]
        return watch, phone

    def test_requires_phone_acknowledgment_of_actual_watch_draws(self):
        watch, phone = self.fixture()
        self.assertEqual(dev.echo_acknowledged(watch, phone), [1, 2, 3, 4, 5])
        self.assertEqual(dev.echo_acknowledged(watch, []), [])
        self.assertEqual(dev.echo_acknowledged("", phone), [])

    def test_old_run_with_same_ids_cannot_pass(self):
        watch, phone = self.fixture(epoch="old")
        self.assertEqual(dev.echo_acknowledged(watch, phone), [])

    def test_wireless_trace_cannot_validate_tethered_test(self):
        watch, phone = self.fixture()
        for event in phone:
            event["transport"] = "WIRELESS"
        self.assertEqual(dev.echo_acknowledged(watch, phone), [])


if __name__ == "__main__":
    unittest.main()
