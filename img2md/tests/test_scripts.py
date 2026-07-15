import io
import json
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

from PIL import Image


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from extract_utils import crop_image, package_zip  # noqa: E402
from prepare_image import prepare  # noqa: E402


class CropTests(unittest.TestCase):
    def test_pixel_coordinates_under_1000_are_not_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            output = Path(tmp) / "crop.png"
            Image.new("RGB", (800, 600), "white").save(source)

            crop_image(source, output, 100, 100, 500, 500)

            with Image.open(output) as cropped:
                self.assertEqual(cropped.size, (400, 400))

    def test_unit_coordinates_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            output = Path(tmp) / "crop.png"
            Image.new("RGB", (800, 600), "white").save(source)

            crop_image(
                source,
                output,
                0.25,
                0.25,
                0.75,
                0.75,
                coordinate_system="unit",
            )

            with Image.open(output) as cropped:
                self.assertEqual(cropped.size, (400, 300))


class PrepareTests(unittest.TestCase):
    def test_long_image_result_is_valid_json_and_ordered(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "long.png"
            Image.new("RGB", (200, 1700), "white").save(source)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                result = prepare(source, Path(tmp) / "parts")

            parsed = json.loads(stdout.getvalue())
            self.assertEqual(parsed, result)
            self.assertTrue(result["needs_split"])
            self.assertGreaterEqual(len(result["files_to_read"]), 2)
            self.assertTrue(all(Path(path).is_file() for path in result["files_to_read"]))

    def test_multipage_tiff_is_expanded_in_page_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "pages.tiff"
            first = Image.new("RGB", (100, 100), "white")
            second = Image.new("RGB", (100, 100), "black")
            first.save(source, save_all=True, append_images=[second])
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                result = prepare(source, Path(tmp) / "pages")

            self.assertEqual(result["image_info"]["frame_count"], 2)
            self.assertEqual(len(result["files_to_read"]), 2)
            self.assertTrue(result["files_to_read"][0].endswith("page001.png"))
            self.assertTrue(result["files_to_read"][1].endswith("page002.png"))

    def test_animated_gif_is_stabilized_to_first_frame_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "animated.gif"
            first = Image.new("RGB", (20, 20), "white")
            second = Image.new("RGB", (20, 20), "black")
            first.save(
                source,
                save_all=True,
                append_images=[second],
                duration=100,
                loop=0,
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                result = prepare(source, Path(tmp) / "frames")

            self.assertEqual(result["image_info"]["frame_count"], 2)
            self.assertEqual(len(result["files_to_read"]), 1)
            frame_path = Path(result["files_to_read"][0])
            self.assertTrue(frame_path.name.endswith("frame001.png"))
            with Image.open(frame_path) as frame:
                self.assertEqual(frame.convert("RGB").getpixel((0, 0)), (255, 255, 255))


class PackageTests(unittest.TestCase):
    def test_zip_contains_markdown_and_relative_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            md_path = root / "report.md"
            image_path = root / "img" / "chart.png"
            image_path.parent.mkdir()
            md_path.write_text("![chart](img/chart.png)\n", encoding="utf-8")
            Image.new("RGB", (10, 10), "white").save(image_path)
            zip_path = root / "out" / "report.zip"

            package_zip(md_path, zip_path)

            with zipfile.ZipFile(zip_path) as archive:
                self.assertEqual(
                    set(archive.namelist()), {"report.md", "img/chart.png"}
                )


if __name__ == "__main__":
    unittest.main()
