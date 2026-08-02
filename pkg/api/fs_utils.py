import os
import shutil
import sys


def _ignore_vanished(func, path, exc):
    # A sidecar removed from under us is expected (see rmtree). Anything else --
    # permissions, I/O errors -- must keep propagating so a failed delete is not
    # mistaken for a successful one.
    if not isinstance(exc, FileNotFoundError):
        raise exc


def rmtree(path):
    """shutil.rmtree() that tolerates entries disappearing during the walk.

    Lunii and Flam storage is FAT, which has no native extended attributes, so
    macOS keeps them in AppleDouble sidecar files named "._<name>" beside each
    entry. Deleting an entry also deletes its sidecar, but rmtree() enumerated
    both up front, so it then tries to unlink a sidecar that is already gone:

        FileNotFoundError: [Errno 2] No such file or directory: '._000'
          File "shutil.py", line 672, in _rmtree_safe_fd

    That aborted every story removal on macOS, reported as "Failed to remove".

    The tree must exist: a missing path raises, so a wrong mount point cannot be
    mistaken for a story that was successfully deleted.
    """
    os.lstat(path)  # raises FileNotFoundError / NotADirectoryError on a bad path
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_ignore_vanished)
    else:
        shutil.rmtree(
            path,
            onerror=lambda func, p, exc_info: _ignore_vanished(func, p, exc_info[1]),
        )


def rmtree_if_exists(path):
    """Remove a directory tree when present. Returns True if it is gone afterwards."""
    if os.path.isdir(path):
        rmtree(path)
    return not os.path.exists(path)
