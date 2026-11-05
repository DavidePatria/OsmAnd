"""Bootstrap must never reset existing work or clone during an offline check."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("junction_bootstrap", Path(__file__).parents[1] / "bootstrap.py")
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


class BootstrapTests(unittest.TestCase):
    def fixture(self, root):
        repository = root / "project"
        repository.mkdir()
        lock = root / "lock.json"
        lock.write_text(json.dumps({"siblings": [{"directory": "resources", "url": "https://example.invalid/source", "commit": "expected"}]}))
        return patch.multiple(bootstrap, ROOT=repository, LOCK=lock)

    def test_offline_check_does_not_clone_missing_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.fixture(Path(tmp)), patch.object(bootstrap, "git") as git:
                self.assertEqual(bootstrap.bootstrap(True), 1)
                git.assert_not_called()

    def test_existing_wrong_revision_is_never_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "resources").mkdir()
            with self.fixture(root), patch.object(bootstrap, "git", side_effect=[str(root / "resources"), "other", ""]) as git:
                self.assertEqual(bootstrap.bootstrap(False), 1)
                self.assertFalse(any("checkout" in call.args or "clone" in call.args or "reset" in call.args for call in git.call_args_list))

    def test_parent_repository_is_not_accepted_as_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "resources").mkdir()
            with self.fixture(root), patch.object(bootstrap, "git", return_value=str(root)) as git:
                self.assertEqual(bootstrap.bootstrap(False), 1)
                self.assertEqual(git.call_count, 1)
