#========================================================
# git_validation.py
#========================================================
# PublicPermissions: True
#========================================================
# Simple class to test whether a git working repository
# is up to date with a supplied remote.
#========================================================

import os
import subprocess
from subprocess import DEVNULL

def _local_head(path):
    """Returns a tuple containing the hash of a local repo's head and an error string,
    exactly one of which will be None."""
    try:
        output = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=path)
    except subprocess.CalledProcessError as ex:
        return (None, 'Failed to get hash of local repo, return code: {}'.format(ex.returncode))
    return (output.decode().strip(), None)


def _remote_head(url):
    """Returns a tuple containing the hash of a remote repo's head and an error string,
    exactly one of which will be None."""
    try:
        output = subprocess.check_output(['git', 'ls-remote', url, 'HEAD'], cwd='/')
    except subprocess.CalledProcessError as ex:
        return (None, 'Failed to get hash of remote url, return code: {}'.format(ex.returncode))
    return (output.decode().split()[0], None)


def _has_untracked_files(path):
    """Returns True iff the git repository at path contains untracked files."""
    try:
        output = subprocess.check_output(['git', 'ls-files', '--exclude-standard',
                                          '--others'], cwd=path)
    except subprocess.CalledProcessError:
        return True
    return len(output.decode().strip()) > 0


def _has_dirty_files(path):
    """Returns True iff the git repository at path contains dirty files."""
    return subprocess.call(['git', 'diff-files', '--quiet'],
                           cwd=path, stdout=DEVNULL, stderr=DEVNULL) != 0


def _has_staged_files(path):
    """Returns True iff the git repository at path contains staged files."""
    return subprocess.call(['git', 'diff-index', '--quiet', '--cached', 'HEAD'],
                           cwd=path, stdout=DEVNULL, stderr=DEVNULL) != 0


def check_repo(local_path, remote_url):
    """Determines if local_path is a valid git repo in sync with remote_url.

    Returns a dict containing the following values:
    * is_valid - True iff local_path is a git repository
    * is_synchronized - True iff local_path has no modified files or staged
                        changes and the HEAD hash matches that of remote_url.
    * problem - If is_valid or is_synchronized is false, a string explaining why.
    * local_hash - The HEAD of local_path, if known.
    * remote_hash - The HEAD of remote_url, if known."""

    # Start with an easy to return failure state.
    ret = {
        'is_valid': False,
        'is_synchronized': False,
        'problem': None,
        'local_hash': None,
        'remote_hash': None,
    }

    # Check the local_path is a valid git repo and store its HEAD.
    if not os.path.isdir(local_path):
        ret['problem'] = '{} is not a valid directory'.format(local_path)
        return ret
    (ret['local_hash'], ret['problem']) = _local_head(local_path)
    if ret['local_hash'] is None:
        return ret
    ret['is_valid'] = True

    # Get the HEAD of the remote.
    (ret['remote_hash'], ret['problem']) = _remote_head(remote_url)
    if ret['remote_hash'] is None:
        return ret

    # Search for various forms of dirtyness on the local repo.
    if _has_untracked_files(local_path):
        ret['problem'] = 'Repository contains untracked files.'
    elif _has_dirty_files(local_path):
        ret['problem'] = 'Repository contains modified files.'
    elif _has_staged_files(local_path):
        ret['problem'] = 'Repository contains staged files.'
    elif ret['local_hash'] != ret['remote_hash']:
        ret['problem'] = 'Repository HEAD does not match remote url.'
    else:
        ret['is_synchronized'] = True
    return ret
