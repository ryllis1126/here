"""Guard the image builder against touching existing files or devices."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/lab-image.py"


class ImageSafety(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("lab_image", SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_rejects_paths_and_device_names(self):
        for name in ("/dev/sda", "../disk.img", "dir/disk.img", "disk", ".img"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.module.reserve_image(self.root, name, 40)

    def test_preserves_existing_files_and_symlinks(self):
        file = self.root / "user.img"
        file.write_bytes(b"preserve me")
        link = self.root / "link.img"
        link.symlink_to(file)
        for name in (file.name, link.name):
            with self.subTest(name=name), self.assertRaises(FileExistsError):
                self.module.reserve_image(self.root, name, 40)
        self.assertEqual(file.read_bytes(), b"preserve me")

    def test_reserves_only_a_new_regular_image(self):
        image = self.module.reserve_image(self.root, "owned.img", 40)
        self.assertTrue(image.is_file())
        self.assertEqual(image.stat().st_size, 40 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
