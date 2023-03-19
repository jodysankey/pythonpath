"""Module for linux to make and scale scans. Relies on scanimage
(SANE) for the scanning and ImageMagick for the image manipulation.
Most of this is really pretty old."""

#========================================================
# Copyright Jody M Sankey 2010 - 2018
#========================================================
# PublicPermissions: True
#========================================================

import collections
import itertools
import math
import os
import re
import subprocess
import sys
import time


# Define constants
SCAN_PATH = os.path.expanduser("~/tmp/scan")
SCAN_NAME = "scan_"

# Gamma4SI arguments are: gamma, floor, ceiling, table_size
GAMMA_TABLE = subprocess.check_output(
    ["gamma4scanimage", "1.2", "200", "3500", "4095"]).decode("utf-8")

if 'SCANNER_URL' not in os.environ:
    print('Could not find a SCANNER_URL environment variable')
    sys.exit(1)
SCANNER_URL = os.environ['SCANNER_URL']

BASE_SCAN_COMMAND = f"scanimage -d '{SCANNER_URL}' --buffer-size=1024 --format=tiff --mode=Color"

# HP scanner resets resolution unless it is the last argument
BASE_SCAN_SUFFIX = ("--res=300")

BASE_CONVERT_COMMAND = ("convert ")

COLD_START_FAIL_TIME_SEC = 2

SOURCES = [
    {'labels':('p', 'platen'),
     'description':'Flatbed, single sheet',
     'multi':'off',
     'scan':'--source=Flatbed'},
    {'labels':('m', 'manual'),
     'description':'Flatbed, confirm each sheet',
     'multi':'manual',
     'scan':'--source=Flatbed'},
    {'labels':('1', 'simplex'),
     'description':'ADF, single sided',
     'multi':'driver',
     'scan':"--source=ADF"},
    {'labels':('2', 'duplex'),
     'description':'ADF, double sided',
     'multi':'driver',
     'scan':"--source='ADF Duplex'"},
    {'labels':('3', 'dualsimplex'),
     'description':'ADF, single sided, fed twice',
     'multi':'double',
     'scan':"--source=ADF"},
    {'labels': ('f', 'dualsimplex-front'),
     'description': 'ADF, single sided, fed front side',
     'multi': 'driver',
     'skip_alternate': 'forward',
     'scan': "--source=ADF"},
    {'labels': ('b', 'dualsimplex-back'),
     'description': 'ADF, single sided, fed back side in reverse',
     'multi': 'driver',
     'skip_alternate': 'backward',
     'scan': "--source=ADF"},
]

PAPERS = [
    {'labels':('l', 'letter'),
     'description':'US Letter',
     'scan':'-x 218 -y 279',
     'scan_conditional': {
         'simplex': '-l 1',
         'dualsimplex': '-l 1',
         'dualsimplex-front': '-l 1',
         'dualsimplex-back': '-l 1',
         'duplex': '-l 3'}},
    {'labels':('p', 'payslip'),
     'description':'Payslip non standard',
     'scan':'-x 191 -y 241',
     'scan_conditional': {
         'simplex': '-l 15',
         'dualsimplex': '-l 15',
         'dualsimplex-front': '-l 15',
         'dualsimplex-back': '-l 15',
         'duplex': '-l 15'}},
    {'labels':('g', 'legal'), 'description':'US Legal ',
     'scan':'-x 218 -y 355',
     'scan_conditional':{
         'simplex': '-l 1',
         'dualsimplex': '-l 1',
         'dualsimplex-front': '-l 1',
         'dualsimplex-back': '-l 1',
         'duplex': '-l 1'}},
    {'labels':('4', 'a4'),
     'description':'ISO A4',
     'scan':'-x 210 -y 297',
     'scan_conditional':{
         'simplex': '-l 5',
         'dualsimplex': '-l 5',
         'dualsimplex-front': '-l 5',
         'dualsimplex-back': '-l 5',
         'duplex': '-l 5'}},
    #{'labels':('a','auto'),'description':'(Attempt) auto cropping','crop':False,
    # 'scan':'','sources':{}, 'convert':'-trim +repage'},
]

# Note order is important for convert, 'convert' gets added before 'color' or 'gray'
SCALES = [
    {'labels':('s', 'small'), 'description':'Small (40% 300dpi)',
     'file_type':'png',
     'convert':'-resize 40%',
     'convert_color':'-colors 32 -contrast -despeckle -colors 32',
     'convert_gray':'-colorspace gray -colors 8 -contrast -despeckle -colorspace gray -colors 8'},
    {'labels':('m', 'medium'), 'description':'Medium (60% 300dpi)',
     'file_type':'jpg',
     'convert':'-resize 60%'},
    {'labels':('l', 'large'), 'description':'Large (Unscaled 300dpi)',
     'file_type':'jpg',
     'convert':''},
]

COLORS = [
    {'labels':('c', 'color', 'colour'), 'description':'All pages colour',
     'first_col':True,
     'other_col':True},
    {'labels':('g', 'gray', 'grey'), 'description':'All pages greyscale',
     'first_col':False,
     'other_col':False},
    {'labels':('f', 'first'), 'description':'First page colour, others greyscale',
     'first_col':True,
     'other_col':False},
]


class ScanError(Exception):
    """An error occurred during scanning."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class Customization:
    """A single customization of the default scan behavior."""

    def __init__(self, purpose, dictionary):
        self.purpose = purpose
        for k in dictionary:
            setattr(self, k, dictionary[k])

    def attribute(self, attribute_name, conditional_names):
        """Returns the supplied attribute_name for this customization."""
        ret = []
        if hasattr(self, attribute_name):
            ret.append(getattr(self, attribute_name))
        if hasattr(self, attribute_name + "_conditional"):
            conditional = getattr(self, attribute_name + "_conditional")
            ret.extend([conditional[k] for k in conditional if k in conditional_names])
        return ret


class CustomizationSet:
    """A collection of customizations to the default scan behavior."""

    def __init__(self):
        self.customizations = []

    def append(self, new_customization):
        """Append a new customization to the set."""
        self.customizations.append(new_customization)

    def first_value(self, key):
        """Returns the requested key in the first matching customization."""
        for customization in self.customizations:
            if hasattr(customization, key):
                return getattr(customization, key)
        return None

    def summary(self, leader):
        """Returns a human readable summary of all the customizations in this set."""
        lines = [f"{leader}{c.purpose:10} {c.description}" for c in self.customizations]
        return "\n".join(lines)

    def labels(self):
        """Returns all labels in the customizations in the set."""
        label_lists = [c.labels for c in self.customizations]
        return list(itertools.chain.from_iterable(label_lists))

    def scan_flags(self):
        """Returns the scan command flags needed for these customizations."""
        flag_lists = [c.attribute("scan", self.labels()) for c in self.customizations]
        return list(itertools.chain.from_iterable(flag_lists))

    def convert_flags(self, is_color):
        """Returns the convert command flags needed for these customizations."""
        flag_lists = [c.attribute("convert", self.labels()) for c in self.customizations]
        if is_color:
            flag_lists.extend([c.attribute("convert_color", self.labels())
                               for c in self.customizations])
        else:
            flag_lists.extend([c.attribute("convert_gray", self.labels())
                               for c in self.customizations])
        return list(itertools.chain.from_iterable(flag_lists))


def find_option_or_die(option_set, label):
    """Return the option containing label, or None if not found."""
    label = label.lower()
    for option in option_set:
        if label in option['labels']:
            return option
    print(f"Invalid option: {label}")
    sys.exit(1)


def beep():
    """Plays a short tone."""
    subprocess.check_call([
        'play', '--no-show-progress', '--null', '--channels', '1',
        'synth', '1.5',
        'sine', '1200' if beep.high else '880'])
    beep.high = not beep.high
beep.high = False


def die(print_string):
    """Prints the specified string then exits with code 1"""
    print(print_string)
    sys.exit(1)


def largest_filename_in_dir(path, pattern):
    """Returns the largest numbered file matching pattern in dir"""
    regex_pat = pattern.replace('%', '([0-9]{3})')
    max_page = 0
    for f in os.listdir(path):
        match = re.search(regex_pat, f)
        if match is not None and int(match.groups()[0]) > max_page:
            max_page = int(match.groups()[0])
    return max_page


# Scanning and conversion subroutines


def get_start_output_page(dest, file_type):
    """Returns the initial output page number to avoid existing files."""
    start_page = 1
    if dest:
        (dest_dir, dest_name) = os.path.split(dest)
        if not dest_name:
            die("ERROR: Supplied path must include filename")
        if dest_dir:
            dest_dir = os.path.expanduser(dest_dir)
            if not os.path.isdir(dest_dir):
                die(f"ERROR:Supplied path '{dest_dir}' does not exist")
            dest = os.path.join(dest_dir, dest_name)
        else:
            dest = os.path.join(SCAN_PATH, dest_name)

        if os.path.isfile(f"{dest}.{file_type}"):
            start_page += 1
        while (os.path.isfile(f"{dest} p{start_page}.{file_type}")
               or os.path.isfile(f"{dest} p0{start_page}.{file_type}")
               or os.path.isfile(f"{dest} p00{start_page}.{file_type}")):
            start_page += 1
        if start_page > 1:
            print(f"Destination already exists, start at page {start_page}")
    return start_page


def get_start_scan_index(dest, file_type):
    """Returns the initial scan index to avoid existing scan files or direct retypes"""
    start_num = largest_filename_in_dir(SCAN_PATH, SCAN_NAME + "%.tif") + 1
    if not dest:
        start_num = max(start_num, largest_filename_in_dir(SCAN_PATH, SCAN_NAME+'%.'+file_type) + 1)
    return start_num


def batch_scan_image(base_command, start_num, debug=False):
    """Calls the scanimage command given by base_command in batch scan mode
    beginning at start_num and checks the return code."""
    full_command = (base_command + " --batch='{}/{}%03d.tif' --batch-start={}".format(
        SCAN_PATH, SCAN_NAME, start_num))
    if debug:
        print('RUNNING: ' + full_command)
    for attempt in range(1, 4):
        start = time.time()
        ret = subprocess.call(full_command, shell=True)
        if ret in (0, 7):
            # 0 is success, 7 is out of documents when doing a batch feed
            return
        if ret == 1 and time.time() - start < COLD_START_FAIL_TIME_SEC:
            # Sometimes the scanner returns 1 quickly if its not warmed up yet.
            print(f'Retrying scan command after immediate fail on attempt {attempt}')
            continue
        raise ScanError(f"ERROR {ret} calling scanimage")
    raise ScanError("ERROR repeated retcode 1 calling scanimage")


def single_scan_image(command, num, debug=False):
    """Calls the scanimage command given by base_command in single scan mode for
    index num, checks the return code, and returns the filename"""
    scan_file = scan_file_name(num)
    if debug:
        print('RUNNING: ' + command)
    ret = subprocess.call(f"{command} > '{scan_file}'", shell=True)
    if ret:
        raise ScanError(f"ERROR {ret} calling scanimage")
    return scan_file


def scan_file_name(index):
    """Returns the scan output filename for the supplied index."""
    return f'{SCAN_PATH}/{SCAN_NAME}{index:0>3}.tif'


def acquire_scans(customizations, scan_start_index, output_start_index, debug=False):
    """Runs an external command to acquire a set of scans and returns:
    1. A list of filenames,
    2. A dictionary of whether invertion is required for each filename
    3. A dictionary of output indices for each filename
    4. The error produced during scanning if one exists"""
    command = " ".join([BASE_SCAN_COMMAND] + customizations.scan_flags() + [BASE_SCAN_SUFFIX])
    scans = []
    index_map = {}
    invertion_map = collections.defaultdict(bool) # Invertion is false unless otherwise speciified
    mode = customizations.first_value('multi')
    error = None
    if mode == 'driver':
        try:
            batch_scan_image(command, scan_start_index, debug=debug)
        except ScanError as err:
            print("Caught scan error during scan, continuing to process remaining images")
            error = err
        end_scan_index = largest_filename_in_dir(SCAN_PATH, SCAN_NAME + "%.tif")
        if customizations.first_value('flip_even'):
            for num in range(scan_start_index, end_scan_index + 1):
                # The duplexer scans every other sheet upside down, need to mark these now while
                # we're certain which images it applies to (mogrify to flip the raw image was
                # extremely slow)
                invertion_map[scan_file_name(num)] = (num - scan_start_index) % 2 > 0
        for num in range(scan_start_index, end_scan_index + 1):
            scans.append(scan_file_name(num))
            if customizations.first_value('skip_alternate') == 'forward':
                index_map[scan_file_name(num)] = output_start_index + (num - scan_start_index) * 2
            elif customizations.first_value('skip_alternate') == 'backward':
                index_map[scan_file_name(num)] = output_start_index + (end_scan_index - num) * 2
            else:
                index_map[scan_file_name(num)] = output_start_index + (num - scan_start_index)

    elif mode == 'double':
        print("Load the document front side of first sheet up")
        start_index_front = scan_start_index
        try:
            batch_scan_image(command, start_index_front, debug=debug)
        except ScanError as err:
            print("Caught scan error during scan, continuing to process remaining images")
            error = err
            error.message += " (during front side scan)"
        end_index_front = largest_filename_in_dir(SCAN_PATH, SCAN_NAME + "%.tif")
        num_sheets = end_index_front - start_index_front + 1
        for num in range(start_index_front, end_index_front + 1):
            scans.append(scan_file_name(num))
            index_map[scan_file_name(num)] = output_start_index + (num - start_index_front) * 2

        if error is None:
            input('Load the document back side of last page up then press enter')
            start_index_back = end_index_front + 1
            try:
                batch_scan_image(command, start_index_back, debug=debug)
            except ScanError as err:
                print("Caught scan error during scan, continuing to process remaining images")
                error = err
                error.message += " (during back side scan)"
            end_index_back = largest_filename_in_dir(SCAN_PATH, SCAN_NAME + "%.tif")
            if (end_index_back - start_index_back + 1) != num_sheets:
                num_sheets = max(num_sheets, end_index_back - start_index_back + 1)
                if error is None:
                    error = ScanError("Number of front and back pages don't match")
            for num in range(start_index_back, end_index_back + 1):
                scans.append(scan_file_name(num))
                index_map[scan_file_name(num)] = ((output_start_index + (2 * num_sheets) - 1)
                                                  - ((num - start_index_back) * 2))

    elif mode == 'manual':
        num = scan_start_index
        out = output_start_index
        try:
            while True:
                scans.append(single_scan_image(command, num, debug))
                index_map[scan_file_name(num)] = out
                # Optionally could beep() here
                answer = input('Return to scan another or any other key to stop: ')
                if answer != '':
                    break
                num += 1
                out += 1
        except ScanError as err:
            print("Caught scan error during scan, stopping manual scan")

    else:
        scans.append(single_scan_image(command, scan_start_index))
        index_map[scan_file_name(scan_start_index)] = output_start_index

    return scans, invertion_map, index_map, error


def remove_killed_files(files, kill_indices, index_map):
    """Removes a set of files from a list of filenames, both deleting on disk and removing from
    the list. Files to remove are specified as list indices."""
    kill_indices.sort()
    kill_indices.reverse()
    for kill in kill_indices:
        if kill <= len(files):
            kill_file = files[kill-1]
            kill_output = index_map[kill_file]
            os.remove(kill_file)
            files.remove(kill_file)
            # TODO: renumbering based on index map not yet tested
            del index_map[kill_file]
            for f in index_map:
                if index_map[f] > kill_output:
                    index_map[f] = index_map[f] - 1
        else:
            print(f"WARNING: Page {kill} was not created so could not be killed")
    return files


def answer_question_interactively(question):
    """Returns True or False for t yes/no question to the user"""
    while True:
        answer = input(question + '? [Y or N]: ')
        if answer.lower() == 'y':
            return True
        if answer.lower() == 'n':
            return False


def remove_unwanted_files(files, index_map):
    """Removes a set of files from a list of filenames, where the set is selected
    interactively by presenting the user with thumbnails of the file contents"""
    # TODO: The output indices map also needs to be renumbered to account for the deletions
    kill_indices = []
    for i, f in zip(range(len(files)), files):
        subprocess.call(f"display -resize 25% '{f}'", shell=True)
        if not answer_question_interactively('Keep ' + f):
            kill_indices.append(i)
    return remove_killed_files(files, kill_indices, index_map)


def output_format_string(dest, num_digits, extention):
    """Returns an output file formatting string."""
    return f"{dest} p{{:0{num_digits}d}}.{extention}"


def renumber_existing_files(dest, num_digits, extention, start_page):
    """Renames existing files so all use the specified num of digits"""
    unnumbered_format = f'{dest}.{extention}'
    output_format = output_format_string(dest, num_digits, extention)
    lesser_formats = [output_format_string(dest, d, extention) for d in range(1, num_digits)]

    # Do the had-no-num case first
    if os.path.isfile(unnumbered_format) and not os.path.isfile(output_format.format(1)):
        os.rename(unnumbered_format, output_format.format(1))
    # Then all smaller formats
    for num, fmt in itertools.product(range(start_page), lesser_formats):
        if (os.path.isfile(fmt.format(num)) and not os.path.isfile(output_format.format(num))):
            os.rename(fmt.format(num), output_format.format(num))


def convert_scans(scans, invertion_map, index_map, customizations, dest, extention, num_digits,
                  debug=False):
    """Convert a set of raw scans into the desired output format and filename."""
    outputs = []
    for scan_file in scans:
        if not dest:
            new_file = scan_file.replace("tif", extention)
        elif len(scans) == 1 and index_map[scans[0]] == 1:
            new_file = f"{dest}.{extention}"
        else:
            new_file = output_format_string(
                dest, num_digits, extention).format(index_map[scan_file])

        is_color = (customizations.first_value('first_col') if scan_file == scans[0]
                    else customizations.first_value('other_col'))
        command = "{} '{}' {} {} '{}'".format(
            BASE_CONVERT_COMMAND,
            scan_file,
            "-rotate 180" if invertion_map[scan_file] else "",
            " ".join(customizations.convert_flags(is_color)),
            new_file)

        if debug:
            print('RUNNING: ' + command)
        ret_val = subprocess.call(command, shell=True)
        if ret_val != 0 and not os.path.exists(new_file):
            print(f'WARNING: Could not convert {scan_file} (error code: {ret_val})')
        else:
            if ret_val != 0:
                print(f'Converted {scan_file} to {new_file}'
                      + f' (but convertion returned error code {ret_val})')
            else:
                print(f'Converted {scan_file} to {new_file}')
            os.remove(scan_file)
            outputs.append(new_file)
    return outputs


def scan_and_convert(dest, customizations, view, check, kills, debug):
    """Do the bulk of the work to execute scans and convert"""
    file_type = customizations.first_value("file_type")
    output_start_page = get_start_output_page(dest, file_type)
    scan_start_index = get_start_scan_index(dest, file_type)

    # Summarize what we're going to do
    print(customizations.summary("   "))
    print("   Dest       " + (dest if dest else SCAN_PATH))
    print("   InitialNum " + str(scan_start_index))
    print("   InitialOutput p" + str(output_start_page))

    # Do the scanning and remove unwanted pages
    scans, invertion_map, index_map, error = acquire_scans(
        customizations, scan_start_index, output_start_page, debug=debug)
    scans = remove_killed_files(scans, kills, index_map)
    if check:
        scans = remove_unwanted_files(scans, index_map)
    if not scans:
        die("ERROR: Could not find any remaining scans to process")

    # Calculate the file output formats and renumber existing files if required
    output_max_page = max(index_map.values())
    num_digits = int(math.log(float(output_max_page), 10)) + 1
    renumber_existing_files(dest, num_digits, file_type, output_start_page)

    # Do the conversion
    outputs = convert_scans(
        scans, invertion_map, index_map, customizations, dest, file_type, num_digits, debug=debug)

    # Display a warning if an error occured
    if error is not None:
        print("WARNING: ERROR DURING SCANNING, OUTPUT MAY BE INCOMPLETE " + error.message)

    #Finally show the user what we've created, if they are interested
    if view:
        for output in outputs:
            subprocess.call(f"display -resize 25% '{output}' &", shell=True)


def perform_scan(dest, source, paper, scale, color, kills=[], view=False, check=False, debug=False):
    """Executes a scan using the supplied user inputs.

    dest - The destination file prefix.
    source - One of the paper source enumerations.
    paper - One of the paper size enumerations.
    scale - One of the output scale enumerations.
    color - One of the output color enumerations.
    kills - List out scan indexes to delete without saving.
    view - True to display the output files in addition to saving.
    check - True to ask whether to keep each scan before saving.
    debug - True to display command line invokations.
    """
    # Parse each customization from the supplied string
    customizations = CustomizationSet()
    customizations.append(Customization("Source", find_option_or_die(SOURCES, source)))
    customizations.append(Customization("Paper", find_option_or_die(PAPERS, paper)))
    customizations.append(Customization("Scale", find_option_or_die(SCALES, scale)))
    customizations.append(Customization("Color", find_option_or_die(COLORS, color)))
    # Call the function
    scan_and_convert(dest, customizations, kills=kills, view=view, check=check, debug=debug)
