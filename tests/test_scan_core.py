import contextlib
import os
import sys
from typing import List
import unittest
from pathlib import Path
import tempfile

import scan_core

# pylint: disable=missing-function-docstring

# Overwrite the actual scanner URL and make scan and convert commands just echo.
scan_core.BASE_SCAN_COMMAND = ["echo"] + [
    "SCANURL" if c == scan_core.SCANNER_URL else c for c in scan_core.BASE_SCAN_COMMAND
]
scan_core.BASE_CONVERT_COMMAND = ["echo"] + scan_core.BASE_CONVERT_COMMAND


def build_customizations(source_paper_scale_color: str) -> scan_core.SelectedCustomizations:
    return scan_core.SelectedCustomizations.from_labels(
        source_paper_scale_color[0],
        source_paper_scale_color[1],
        source_paper_scale_color[2],
        source_paper_scale_color[3],
    )


def create_scan_files(num: int) -> None:
    for i in range(1, num + 1):
        Path(scan_core.scan_file_name(i)).touch()


def output(num: int, idx=None, invert=False):
    """Returns a new output file."""
    idx = idx if idx else num
    output = scan_core.ScanOutput(scan_core.scan_file_name(num), idx)
    if invert:
        output.needs_inversion = True
    return output


class TestScanCore(unittest.TestCase):
    """Unit tests covering the scan_code module."""

    def __init__(self, *args, **kwargs):
        super(TestScanCore, self).__init__(*args, **kwargs)
        self.maxDiff = None

    def run(self, result=None):
        # Run all tests with a file ready to redirect stdout and the DEFAULT_PATH set to a tmpdir.
        with tempfile.TemporaryFile(mode="w+") as stdout, tempfile.TemporaryDirectory() as scan_dir:
            scan_core.SCAN_PATH = scan_dir
            self.scan_dir = scan_dir
            self.stdout = stdout
            super(TestScanCore, self).run(result)

    def assertStdOut(self, expected):
        self.stdout.seek(0)
        self.assertEqual(self.stdout.read(), expected)

    def test_full_flow(self):
        create_scan_files(1)
        with contextlib.redirect_stdout(self.stdout):
            scan_core.perform_scan(os.path.join(self.scan_dir, "test"), "p", "l", "m", "c")

        # Because of implementation of single scan, the scan command got echoed into the scan file,
        # which was then deleted after a successful convert, so can't be validated.

        # Stdout should contain the convert and the info.
        self.assertStdOut(
            "   Source     Flatbed, single sheet\n"
            "   Paper      US Letter\n"
            "   Scale      Medium (60% 300dpi)\n"
            "   Color      All pages colour\n"
            f"   Dest       {self.scan_dir}/test\n"
            "   InitialScanFile 2\n"
            f"convert {self.scan_dir}/scan_002.tif -resize 60% {self.scan_dir}/test.jpg\n"
            f"Converted {self.scan_dir}/scan_002.tif to {self.scan_dir}/test.jpg successfully\n"
        )

    def test_acquire_scans_simplex(self):
        customizations = build_customizations("1lsc")
        create_scan_files(3)

        with contextlib.redirect_stdout(self.stdout):
            outputs, errors = scan_core.acquire_scans(customizations, 1)

        self.assertIsNone(errors)
        self.assertEqual(outputs, [output(1), output(2), output(3)])
        self.assertStdOut(
            "scanimage -d SCANURL --buffer-size=1024 --format=tiff --mode=Color "
            "--source=ADF -x 218 -y 279 -l 1 --res=300 "
            f"--batch={self.scan_dir}/scan_%03d.tif --batch-start=1\n",
        )

    def test_acquire_scans_duplex(self):
        customizations = build_customizations("24mc")
        create_scan_files(2)

        with contextlib.redirect_stdout(self.stdout):
            outputs, errors = scan_core.acquire_scans(customizations, 2)

        self.assertIsNone(errors)
        self.assertEqual(outputs, [output(2, 1)])
        self.assertStdOut(
            "scanimage -d SCANURL --buffer-size=1024 --format=tiff --mode=Color "
            "--source=ADF Duplex -x 210 -y 297 -l 5 --res=300 "
            f"--batch={self.scan_dir}/scan_%03d.tif --batch-start=2\n",
        )

    def test_acquire_scans_single(self):
        customizations = build_customizations("pgmc")
        create_scan_files(1)

        with contextlib.redirect_stdout(self.stdout):
            outputs, errors = scan_core.acquire_scans(customizations, 4, 1)

        expected_outputs = [output(4, 1)]
        self.assertIsNone(errors)
        self.assertEqual(outputs, expected_outputs)
        # Because of implementation of single scan, command got echoed into the file, not stdout.
        self.assertStdOut("")
        with open(expected_outputs[0].path) as f:
            self.assertEqual(
                f.read(),
                "scanimage -d SCANURL --buffer-size=1024 --format=tiff --mode=Color "
                "--source=Flatbed -x 218 -y 355 --res=300\n",
            )

    def test_remove_kill_empty(self):
        create_scan_files(3)
        outputs = [output(1), output(2), output(3)]

        with contextlib.redirect_stdout(self.stdout):
            modified = scan_core.remove_killed_files(list(outputs), set())

        self.assertStdOut("")
        self.assertEqual(outputs, modified)
        self.assertEqual(
            {entry.name for entry in os.scandir(self.scan_dir)},
            {f"scan_00{i}.tif" for i in (1, 2, 3)},
        )

    def test_remove_kill_multiple(self):
        create_scan_files(5)
        outputs = [output(1), output(2), output(3), output(4), output(5)]

        with contextlib.redirect_stdout(self.stdout):
            modified = scan_core.remove_killed_files(outputs, {2, 4, 100})

        self.assertStdOut("WARNING: Page 100 was not created so could not be killed\n")
        self.assertEqual([output(1), output(3, 2), output(5, 3)], modified)
        self.assertEqual(
            {entry.name for entry in os.scandir(self.scan_dir)},
            {f"scan_00{i}.tif" for i in (1, 3, 5)},
        )

    def test_renumber_files_single_empty(self):
        outputs = [output(1)]

        new_start = scan_core.renumber_files(outputs, self.scan_dir, "test", "gif")

        self.assertEqual(new_start, 1)
        self.assertEqual({entry.name for entry in os.scandir(self.scan_dir)}, set())
        self.assertEqual([o.index for o in outputs], [1])
        self.assertEqual([os.path.split(o.target_path)[1] for o in outputs], ["test.gif"])

    def test_renumber_files_single_addition(self):
        for f in ["test.gif"]:
            Path(os.path.join(self.scan_dir, f)).touch()
        outputs = [output(2, 1)]

        new_start = scan_core.renumber_files(outputs, self.scan_dir, "test", "gif")

        self.assertEqual(new_start, 2)
        self.assertEqual([o.index for o in outputs], [2])
        self.assertEqual({entry.name for entry in os.scandir(self.scan_dir)}, {"test p1.gif"})
        self.assertEqual([os.path.split(o.target_path)[1] for o in outputs], ["test p2.gif"])

    def test_renumber_files_multi_addition(self):
        for f in ["test p1.jpg", "test p2.jpg"]:
            Path(os.path.join(self.scan_dir, f)).touch()
        outputs = [output(8, 1), output(9, 3), output(10, 2)]

        new_start = scan_core.renumber_files(outputs, self.scan_dir, "test", "jpg")

        self.assertEqual(new_start, 3)
        self.assertEqual([o.index for o in outputs], [3, 5, 4])
        self.assertEqual(
            {entry.name for entry in os.scandir(self.scan_dir)}, {"test p1.jpg", "test p2.jpg"}
        )
        self.assertEqual(
            [os.path.split(o.target_path)[1] for o in outputs],
            ["test p3.jpg", "test p5.jpg", "test p4.jpg"],
        )

    def test_renumber_files_add_digits(self):
        for f in [f"test p{i}.jpg" for i in range(8)]:
            Path(os.path.join(self.scan_dir, f)).touch()
        outputs = [output(1), output(2), output(3), output(4)]

        new_start = scan_core.renumber_files(outputs, self.scan_dir, "test", "jpg")

        self.assertEqual(new_start, 8)
        self.assertEqual([o.index for o in outputs], [8, 9, 10, 11])
        self.assertEqual(
            {entry.name for entry in os.scandir(self.scan_dir)},
            {f"test p0{i}.jpg" for i in range(8)},
        )
        self.assertEqual(
            [os.path.split(o.target_path)[1] for o in outputs],
            ["test p08.jpg", "test p09.jpg", "test p10.jpg", "test p11.jpg"],
        )

    def test_convert_scans(self):
        customizations = build_customizations("1lsg")

        outputs = [output(4), output(5, invert=True), output(6)]
        for o in outputs:
            o.target_path = o.path.replace("tif", "jpg")
            Path(o.path).touch()

        with contextlib.redirect_stdout(self.stdout):
            scan_core.convert_scans(outputs, customizations)

        self.assertStdOut(
            f"convert {self.scan_dir}/scan_004.tif -resize 40% -colorspace gray -colors 8"
            f" -contrast -despeckle -colorspace gray -colors 8 {self.scan_dir}/scan_004.jpg\n"
            f"convert {self.scan_dir}/scan_005.tif -resize 40% -rotate 180 -colorspace gray -colors"
            f" 8 -contrast -despeckle -colorspace gray -colors 8 {self.scan_dir}/scan_005.jpg\n"
            f"convert {self.scan_dir}/scan_006.tif -resize 40% -colorspace gray -colors 8"
            f" -contrast -despeckle -colorspace gray -colors 8 {self.scan_dir}/scan_006.jpg\n"
            f"Converted {self.scan_dir}/scan_004.tif to {self.scan_dir}/scan_004.jpg successfully\n"
            f"Converted {self.scan_dir}/scan_005.tif to {self.scan_dir}/scan_005.jpg successfully\n"
            f"Converted {self.scan_dir}/scan_006.tif to {self.scan_dir}/scan_006.jpg successfully\n"
        )


if __name__ == "__main__":
    unittest.main()
