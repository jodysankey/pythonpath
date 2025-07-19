"""Module for linux to make and scale scans. Relies on scanimage
(SANE) for the scanning and ImageMagick for the image manipulation.
Most of this is really pretty old."""

# ========================================================
# Copyright Jody M Sankey 2010 - 2025
# ========================================================
# PublicPermissions: True
# ========================================================

import itertools
import math
import os
import re
import subprocess
import sys
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple


# Fixed path and default file prefix for scan outputs.
SCAN_PATH: str = os.path.expanduser("~/tmp/scan")
SCAN_PREFIX: str = "scan_"
# Pull scanner URL from the environment.
if "SCANNER_URL" not in os.environ:
    print("ERROR: Could not find a SCANNER_URL environment variable")
    sys.exit(1)
SCANNER_URL = os.environ["SCANNER_URL"]

# Base command lines that we customize below.
# (Note HP scanner resets resolution unless it is the last argument, hence we need the suffix.
BASE_SCAN_COMMAND = [
    "scanimage",
    "-d",
    SCANNER_URL,
    "--buffer-size=1024",
    "--format=tiff",
    "--mode=Color",
]
BASE_SCAN_SUFFIX = ["--res=300"]
BASE_CONVERT_COMMAND = ["convert"]

# Time within which we consider a return code of one to be just scanner wasn't warmed up.
COLD_START_FAIL_TIME_SEC = 2


class ScanError(Exception):
    """An error occurred during scanning."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class ScanOptions:
    """Dataclass to store the very similar extra options."""

    def __init__(self, view: bool, check: bool, debug: bool) -> None:
        self.view = view
        self.check = check
        self.debug = debug


class ScanOutput:
    """Dataclass to store metadata for the scan output files."""

    def __init__(self, path: str, index: int) -> None:
        self.path = path
        self.index = index
        self.needs_inversion = False
        self.target_path: Optional[str] = None

    def __repr__(self):
        ret = f"ScanOutput: scan='{self.path}', idx={self.index}"
        if self.target_path:
            ret += f" target='{self.target_path}'"
        return ret

    def __eq__(self, other):
        if not isinstance(other, ScanOutput):
            return NotImplemented
        return (
            self.path == other.path
            and self.index == other.index
            and self.needs_inversion == other.needs_inversion
            and self.target_path == other.target_path
        )


class Customization:
    """A single customization of the default scan behavior."""

    def __init__(
        self,
        labels: Tuple[str, ...],
        description: str,
        scan: None | List[str] | Tuple[List[str], Dict[str, List[str]]] = None,
        convert: None | List[str] | Tuple[List[str], Dict[str, List[str]]] = None,
        extras: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.purpose: Optional[str] = None
        self.labels = labels
        self.description = description
        self.commands: Dict[str, Tuple[List[str], Dict[str, List[str]]]] = {}
        if scan:
            self.commands["scan"] = (scan, {}) if isinstance(scan, list) else scan
        if convert:
            self.commands["convert"] = (convert, {}) if isinstance(convert, list) else convert
        self.extras = extras if extras else {}

    def command_args(self, command: str, all_labels: List[str]) -> List[str]:
        """Returns the composite argument list needed for the suppled command, including args set
        based on this customization and those set conditionally based on the label of another
        customization."""
        command_entry = self.commands.get(command)
        if command_entry is None:
            return []
        args = command_entry[0]
        for contextual_args in [v for k, v in command_entry[1].items() if k in all_labels]:
            args.extend(contextual_args)
        return args


class CustomizationOptions:
    """A set of customizations options for some purpose."""

    def __init__(self, purpose: str, *options: Customization) -> None:
        self.purpose = purpose
        self.options = list(options)

    def __iter__(self) -> Iterator:
        return self.options.__iter__()

    def by_label(self, label: str) -> Customization:
        """Returns the option with the specified label, throwing a KeyError if not found."""
        for option in self.options:
            if label in option.labels:
                return option
        raise KeyError(f"Invalid option for {self.purpose}: {label}")


class SelectedCustomizations:
    """A collection of customizations to the default scan behavior."""

    def __init__(self) -> None:
        self.customizations: Dict[str, Customization] = {}

    def add_by_label(self, options: CustomizationOptions, label: str) -> None:
        """Append a new customization to the set by its label, raising KeyError if not found."""
        self.customizations[options.purpose] = options.by_label(label)

    @staticmethod
    def from_labels(source: str, paper: str, scale: str, color: str):
        customizations = SelectedCustomizations()
        customizations.add_by_label(SOURCES, source)
        customizations.add_by_label(PAPERS, paper)
        customizations.add_by_label(SCALES, scale)
        customizations.add_by_label(COLORS, color)
        return customizations

    def first_extra(self, key: str) -> Optional[Any]:
        """Returns the requested key in the first matching customization."""
        for customization in self.customizations.values():
            extra = customization.extras.get(key, None)
            if extra:
                return extra
        return None

    def summary(self, leader: str) -> str:
        """Returns a human readable summary of all the customizations in this set, with each line
        being prefixed by the leader string."""
        lines = [f"{leader}{p:10} {c.description}" for p, c in self.customizations.items()]
        return "\n".join(lines)

    def labels(self) -> List[str]:
        """Returns all labels in the customizations in the set."""
        label_lists = [c.labels for c in self.customizations.values()]
        return list(itertools.chain.from_iterable(label_lists))

    def scan_command(self) -> List[str]:
        """Returns the scan command needed for these customizations."""
        args = list(BASE_SCAN_COMMAND)
        for c in self.customizations.values():
            args.extend(c.command_args("scan", self.labels()))
        args.extend(BASE_SCAN_SUFFIX)
        return args

    def convert_command(self, output: ScanOutput, is_first: bool) -> List[str]:
        """Returns the command needed for convert the supplied output with these customizations."""
        args = list(BASE_CONVERT_COMMAND)
        args.append(output.path)
        # Add all the basic convertion commands first.
        for c in self.customizations.values():
            args.extend(c.command_args("convert", self.labels()))
        # Then the inversion.
        if output.needs_inversion:
            args.extend(["-rotate", "180"])
        # Then any additional color/gray modifiers.
        is_color = self.first_extra("first_col" if is_first else "other_col")
        for c in self.customizations.values():
            extra = c.extras.get("convert_color" if is_color else "convert_gray")
            if extra:
                args.extend(extra)
        # And finally the target path.
        if not output.target_path:
            raise RuntimeError(f"Target path not set before conversion: {output.path}")
        args.append(output.target_path)
        return args


class Beeper:
    """Simple class to alternate betwene high and low beeping tones."""

    def __init__(self) -> None:
        self.high = False

    def beep(self) -> None:
        """Plays a short tone."""
        subprocess.check_call(
            [
                "play",
                "--no-show-progress",
                "--null",
                "--channels",
                "1",
                "synth",
                "1.5",
                "sine",
                "1200" if self.high else "880",
            ]
        )
        self.high = not self.high


# Attribute maps to define behavior.
SOURCES = CustomizationOptions(
    "Source",
    Customization(
        labels=("p", "platen"),
        description="Flatbed, single sheet",
        scan=["--source=Flatbed"],
        extras={"multi": "off"},
    ),
    Customization(
        labels=("m", "manual"),
        description="Flatbed, confirm each sheet",
        scan=["--source=Flatbed"],
        extras={"multi": "manual"},
    ),
    Customization(
        labels=("1", "simplex"),
        description="ADF, single sided",
        scan=["--source=ADF"],
        extras={"multi": "driver"},
    ),
    Customization(
        labels=("2", "duplex"),
        description="ADF, double sided",
        scan=["--source=ADF Duplex"],
        extras={"multi": "driver"},
    ),
    Customization(
        labels=("3", "dualsimplex"),
        description="ADF, single sided, fed twice",
        scan=["--source=ADF"],
        extras={"multi": "double"},
    ),
    Customization(
        labels=("f", "dualsimplex-front"),
        description="ADF, single sided, fed front side",
        scan=["--source=ADF"],
        extras={"multi": "driver", "skip_alternate": "forward"},
    ),
    Customization(
        labels=("b", "dualsimplex-back"),
        description="ADF, single sided, fed back side in reverse",
        scan=["--source=ADF"],
        extras={"multi": "driver", "skip_alternate": "backward"},
    ),
)

PAPERS = CustomizationOptions(
    "Paper",
    Customization(
        labels=("l", "letter"),
        description="US Letter",
        scan=(
            ["-x", "218", "-y", "279"],
            {
                "simplex": ["-l", "1"],
                "dualsimplex": ["-l", "1"],
                "dualsimplex-front": ["-l", "1"],
                "dualsimplex-back": ["-l", "1"],
                "duplex": ["-l", "3"],
            },
        ),
    ),
    Customization(
        labels=("p", "payslip"),
        description="Payslip non standard",
        scan=(
            ["-x", "191", "-y", "241"],
            {
                "simplex": ["-l", "15"],
                "dualsimplex": ["-l", "15"],
                "dualsimplex-front": ["-l", "15"],
                "dualsimplex-back": ["-l", "15"],
                "duplex": ["-l", "15"],
            },
        ),
    ),
    Customization(
        labels=("g", "legal"),
        description="US Legal ",
        scan=(
            ["-x", "218", "-y", "355"],
            {
                "simplex": ["-l", "1"],
                "dualsimplex": ["-l", "1"],
                "dualsimplex-front": ["-l", "1"],
                "dualsimplex-back": ["-l", "1"],
                "duplex": ["-l", "1"],
            },
        ),
    ),
    Customization(
        labels=("4", "a4"),
        description="ISO A4",
        scan=(
            ["-x", "210", "-y", "297"],
            {
                "simplex": ["-l 5"],
                "dualsimplex": ["-l 5"],
                "dualsimplex-front": ["-l 5"],
                "dualsimplex-back": ["-l 5"],
                "duplex": ["-l 5"],
            },
        ),
    ),
    # {'labels':('a','auto'),'description':'(Attempt) auto cropping','crop':False,
    # 'scan':'','sources':{}, 'convert':'-trim +repage'},
)

# Note order is important for convert, 'convert' gets added before 'color' or 'gray'
SCALES = CustomizationOptions(
    "Scale",
    Customization(
        labels=("s", "small"),
        description=r"Small (40% 300dpi)",
        convert=["-resize", "40%"],
        extras={
            "file_type": "png",
            "convert_color": ["-colors", "32", "-contrast", "-despeckle", "-colors", "32"],
            "convert_gray": [
                "-colorspace",
                "gray",
                "-colors",
                "8",
                "-contrast",
                "-despeckle",
                "-colorspace",
                "gray",
                "-colors",
                "8",
            ],
        },
    ),
    Customization(
        labels=("m", "medium"),
        description=r"Medium (60% 300dpi)",
        convert=["-resize", "60%"],
        extras={"file_type": "jpg"},
    ),
    Customization(
        labels=("l", "large"),
        description=r"Large (Unscaled 300dpi)",
        convert=[""],
        extras={"file_type": "jpg"},
    ),
)

COLORS = CustomizationOptions(
    "Color",
    Customization(
        labels=("c", "color", "colour"),
        description="All pages colour",
        extras={"first_col": True, "other_col": True},
    ),
    Customization(
        labels=("g", "gray", "grey"),
        description="All pages greyscale",
        extras={"first_col": False, "other_col": False},
    ),
    Customization(
        labels=("f", "first"),
        description="First page colour, others greyscale",
        extras={"first_col": True, "other_col": False},
    ),
)


def largest_filename_in_dir(dest_dir: str, prefix: str, extention: str) -> int:
    """Returns the largest numbered file matching pattern in the supplied dir, or 0 if not found."""
    regex_pat = os.path.join(f"{prefix}([0-9]{{3}}).{extention}")
    max_page = 0
    for f in os.listdir(dest_dir):
        match = re.search(regex_pat, f)
        if match is not None and int(match.groups()[0]) > max_page:
            max_page = int(match.groups()[0])
    return max_page


def answer_question_interactively(question: str) -> bool:
    """Returns True or False for a yes/no question to the user"""
    while True:
        answer = input(question + "? [Y or N]: ")
        if answer.lower() == "y":
            return True
        if answer.lower() == "n":
            return False


# Scanning and conversion subroutines
# ===================================


def scan_file_name(index: int) -> str:
    """Returns the scan output filename for the supplied index."""
    return f"{SCAN_PATH}/{SCAN_PREFIX}{index:0>3}.tif"


def batch_scan_image(command: List[str], start_num: int, debug: bool = False) -> None:
    """Calls the scanimage command given by base_command in batch scan mode
    beginning at start_num and checks the return code."""
    command.extend([f"--batch={SCAN_PATH}/{SCAN_PREFIX}%03d.tif", f"--batch-start={start_num}"])
    if debug:
        print("RUNNING: " + " ".join(command))
    for attempt in range(1, 4):
        start = time.time()
        ret = subprocess.call(command, stdout=sys.stdout)
        if ret in (0, 7):
            # 0 is success, 7 is out of documents when doing a batch feed
            return
        if ret == 1 and time.time() - start < COLD_START_FAIL_TIME_SEC:
            # Sometimes the scanner returns 1 quickly if its not warmed up yet.
            print(f"Retrying scan command after immediate fail on attempt {attempt}")
            continue
        raise ScanError(f"ERROR {ret} calling scanimage")
    raise ScanError("ERROR repeated retcode 1 calling scanimage")


def single_scan_image(command: List[str], num: int, debug: bool = False) -> str:
    """Calls the scanimage command given by base_command in single scan mode for
    index num, checks the return code, and returns the filename"""
    scan_file = scan_file_name(num)
    if debug:
        print("RUNNING: " + " ".join(command))
    with open(scan_file, "wb") as out_file:
        for attempt in range(1, 4):
            start = time.time()
            ret = subprocess.call(command, stdout=out_file)
            if ret == 0:
                # 0 is success
                return scan_file
            if ret == 1 and time.time() - start < COLD_START_FAIL_TIME_SEC:
                # Sometimes the scanner returns 1 quickly if its not warmed up yet.
                print(f"Retrying scan command after immediate fail on attempt {attempt}")
                continue
            raise ScanError(f"ERROR {ret} calling scanimage")
    raise ScanError("ERROR repeated retcode 1 calling scanimage")


def acquire_scans(
    customizations: SelectedCustomizations,
    scan_start_num: int,
    debug: bool = False,
) -> Tuple[List[ScanOutput], Optional[ScanError]]:
    """Runs an external command to acquire a set of scans, returning metadata and an error if
    encountered."""
    cmd = customizations.scan_command()
    scans = []
    error = None

    multi_mode = customizations.first_extra("multi")
    if multi_mode == "driver":
        try:
            batch_scan_image(cmd, scan_start_num, debug=debug)
        except ScanError as err:
            print("Caught scan error during scan, continuing to process remaining images")
            error = err
        end_scan_num = largest_filename_in_dir(SCAN_PATH, SCAN_PREFIX, "tif")
        for num in range(scan_start_num, end_scan_num + 1):
            if customizations.first_extra("skip_alternate") == "forward":
                index = 1 + (num - scan_start_num) * 2
            elif customizations.first_extra("skip_alternate") == "backward":
                index = 1 + (end_scan_num - num) * 2
            else:
                index = 1 + (num - scan_start_num)
            scans.append(ScanOutput(scan_file_name(num), index))
            if customizations.first_extra("flip_even") and (num - scan_start_num) % 2:
                scans[-1].needs_inversion = True

    elif multi_mode == "double":
        # Not tested since refactor

        def scan_one_direction(start_index: int, name: str) -> int:
            """Scans either front or back, returning the number of pages."""
            try:
                batch_scan_image(cmd, start_index, debug=debug)
            except ScanError as err:
                print("Caught scan error during scan, continuing to process remaining images")
                error = err
                error.message += f" (during {name} scan)"
            return largest_filename_in_dir(SCAN_PATH, SCAN_PREFIX, "tif") - start_index + 1

        def append_outputs(start: int, count: int, index_fn: Callable[[int], int]) -> None:
            for num in range(start, start + count):
                scans.append(ScanOutput(scan_file_name(num), index_fn(num)))

        print("Load the document front side of first sheet up")
        front_pages = scan_one_direction(scan_start_num, "front side")
        append_outputs(scan_start_num, front_pages, lambda i: 1 + (i - scan_start_num) * 2)
        if error is not None:
            return scans, error
        input("Load the document back side of last page up then press enter")
        scan_start_back = scan_start_num + front_pages
        back_pages = scan_one_direction(scan_start_back, "back side")
        if back_pages != front_pages:
            front_pages = back_pages = max(front_pages, back_pages)
            if error is None:
                error = ScanError("Number of front and back pages don't match")
        append_outputs(
            scan_start_back,
            back_pages,
            lambda i: (1 + (2 * back_pages) - 1) - ((i - scan_start_back) * 2),
        )

    elif multi_mode == "manual":
        num = scan_start_num
        out = 1
        try:
            while True:
                scans.append(ScanOutput(single_scan_image(cmd, num, debug), out))
                # Optionally could beep() here
                if input("Return to scan another or any other key to stop: ") != "":
                    break
                num += 1
                out += 1
        except ScanError:
            print("Caught scan error during scan, stopping manual scan")

    else:
        scans.append(ScanOutput(single_scan_image(cmd, scan_start_num), 1))

    return scans, error


def remove_killed_files(outputs: List[ScanOutput], kill_indices: Set[int]) -> List[ScanOutput]:
    """Removes the supplied set of files from a list of ScanOutputs, both deleting on disk and
    removing from the list. Files to remove are specified as indices."""
    remaining: List[ScanOutput] = []
    remaining_indices = set(kill_indices)

    for output in outputs:
        if output.index in remaining_indices:
            os.remove(output.path)
            remaining_indices.remove(output.index)
        else:
            output.index -= len([i for i in kill_indices if i < output.index])
            remaining.append(output)
    for kill in remaining_indices:
        print(f"WARNING: Page {kill} was not created so could not be killed")
    return remaining


def remove_unwanted_files(outputs: List[ScanOutput]) -> List[ScanOutput]:
    """Removes a user-selected set of files from a list of ScanOutputs. The user is presented
    with thumbnails of the file contents to decide which to remove."""
    kill_indices = set()
    for output in outputs:
        subprocess.call(["display", "-resize", r"25%", output.path])
        if not answer_question_interactively("Keep " + output.path):
            kill_indices.add(output.index)
    return remove_killed_files(outputs, kill_indices)


def renumber_files(
    outputs: List[ScanOutput],
    dest_dir: str,
    dest_prefix: str,
    extention: str,
) -> int:
    """Increases the index in the outputs to avoid existing files in the destinations, renames
    those files to a consistent number of digits, and sets the target name in the output entries.
    Returns the new start output index."""
    unnumbered_path = os.path.join(dest_dir, f"{dest_prefix}.{extention}")

    def format_string(num_digits: int) -> str:
        return os.path.join(dest_dir, f"{dest_prefix} p{{:0{num_digits}d}}.{extention}")

    def max_existing_file_num() -> int:
        num = 1 if os.path.isfile(unnumbered_path) else 0
        formats = [format_string(i) for i in range(4)]
        while any(f for f in formats if os.path.isfile(f.format(num + 1))):
            num += 1
        return num

    # Calculate the total number of new and existing files and the number of page digits.
    index_increment = max_existing_file_num()
    max_output_index: int = max(outputs, key=lambda o: o.index).index
    num_digits = int(math.log(float(max_output_index + index_increment), 10)) + 1

    # Rename files that already exist in the directory if needed. Didn't have a number first...
    number_1_path = format_string(num_digits).format(1)
    if os.path.isfile(unnumbered_path) and not os.path.isfile(number_1_path):
        os.rename(unnumbered_path, number_1_path)
    # ... then all cases with less than the required number of digits.
    for fmt in [format_string(d) for d in range(1, num_digits)]:
        for num in range(index_increment + 1):
            correct_path = format_string(num_digits).format(num)
            if os.path.isfile(fmt.format(num)) and not os.path.isfile(correct_path):
                os.rename(fmt.format(num), correct_path)

    # Set a target path on each of the output files
    for output in outputs:
        if len(outputs) == 1 and index_increment == 0:
            output.target_path = os.path.join(dest_dir, f"{dest_prefix}.{extention}")
        else:
            output.index += index_increment
            output.target_path = format_string(num_digits).format(output.index)
    return index_increment + 1


def convert_scans(
    outputs: List[ScanOutput],
    customizations: SelectedCustomizations,
    debug=False,
) -> None:
    """Convert a set of raw scans into the desired output format and filename."""
    for output in outputs:
        command = customizations.convert_command(output, output == outputs[0])
        if debug:
            print("RUNNING: " + " ".join(command))
        ret_val = subprocess.call(command, stdout=sys.stdout)
        if ret_val != 0 and output.target_path and not os.path.exists(output.target_path):
            print(f"WARNING: Could not convert {output.path} (error code: {ret_val})")
        else:
            print(f"Converted {output.path} to {output.target_path} ", end="")
            print(f" (despite error code {ret_val})" if ret_val != 0 else "successfully")
            os.remove(output.path)


def scan_and_convert(
    dest_dir: str,
    dest_prefix: str,
    customizations: SelectedCustomizations,
    kills: Set[int],
    options: ScanOptions,
) -> None:
    """Do the bulk of the work to execute scans and convert."""
    if not os.path.isdir(dest_dir):
        print(f"ERROR:Supplied path '{dest_dir}' does not exist")
        sys.exit(1)

    extention = str(customizations.first_extra("file_type"))
    scan_start_index = largest_filename_in_dir(SCAN_PATH, SCAN_PREFIX, "tif") + 1

    # Summarize what we're going to do
    print(customizations.summary("   "))
    print("   Dest       " + os.path.join(dest_dir, dest_prefix))
    print("   InitialScanFile " + str(scan_start_index))
    print("", end="", flush=True)

    # Do the scanning and remove unwanted pages
    outputs, error = acquire_scans(customizations, scan_start_index, debug=options.debug)
    outputs = remove_killed_files(outputs, kills)
    if options.check:
        outputs = remove_unwanted_files(outputs)
    if not outputs:
        print("ERROR: Could not find any remaining scans to process")
        sys.exit(1)

    # Calculate the file output indices and formats and renumber existing files if required.
    renumber_files(outputs, dest_dir, dest_prefix, extention)

    # Do the conversion
    convert_scans(
        outputs,
        customizations,
        debug=options.debug,
    )

    # Display a warning if an error occured
    if error is not None:
        print("WARNING: ERROR DURING SCANNING, OUTPUT MAY BE INCOMPLETE " + error.message)

    # Finally show the user what we've created, if they are interested
    if options.view:
        for output in outputs:
            subprocess.call(f"display -resize 25% '{output}' &", shell=True)


def perform_scan(
    destination: str,
    source: str,
    paper: str,
    scale: str,
    color: str,
    kills: Optional[List[int]] = None,
    view=False,
    check=False,
    debug=False,
):
    """Executes a scan using the supplied user inputs.

    destination - The destination base filename, optionally including path
    source - One of the paper source enumerations.
    paper - One of the paper size enumerations.
    scale - One of the output scale enumerations.
    color - One of the output color enumerations.
    kills - List out scan indexes to delete without saving.
    view - True to display the output files in addition to saving.
    check - True to ask whether to keep each scan before saving.
    debug - True to display command line invokations.
    """

    # Find each customization from the supplied string
    try:
        customizations = SelectedCustomizations()
        customizations.add_by_label(SOURCES, source)
        customizations.add_by_label(PAPERS, paper)
        customizations.add_by_label(SCALES, scale)
        customizations.add_by_label(COLORS, color)
    except KeyError as err:
        print(err)
        sys.exit(3)

    # Do some basic validation on the (overly general API) destination.
    if destination is None:
        (dest_dir, dest_prefix) = (SCAN_PATH, DEFAULT_OUTPUT_PREFIX)
    else:
        (dest_dir, dest_prefix) = os.path.split(destination)
        if not dest_prefix:
            print("ERROR: Supplied path must include filename")
            sys.exit(2)
        dest_dir = os.path.expanduser(dest_dir) if dest_dir else SCAN_PATH

    # Call the function
    scan_and_convert(
        dest_dir,
        dest_prefix,
        customizations,
        set(kills) if kills else set(),
        ScanOptions(view=view, check=check, debug=debug),
    )
