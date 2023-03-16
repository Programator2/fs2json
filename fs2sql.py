from os import stat, listdir
import os
from stat import *
import json
import sys
from db import Database


def get_dentry(filename, path):
    s = stat(path, follow_symlinks=False)
    try:
        selinux = os.getxattr(path, 'security.selinux').rstrip(b'\x00').decode('utf-8')
        selinux = selinux.split(':')
        if len(selinux) not in (4, 5):
            print('Assertion failed:', selinux)
            sys.exit(-1)
        if len(selinux) == 4:
            selinux.append(None)
    except OSError:
        # Operation not supported (/proc fs etc.)
        selinux = [None] * 5
    data = (
        filename,
        s.st_ino,
        s.st_dev,
        s.st_nlink,
        s.st_uid,
        s.st_gid,
        s.st_size,
        s.st_atime,
        s.st_mtime,
        s.st_ctime,
        S_IFMT(s.st_mode),
        S_IMODE(s.st_mode),
        *selinux
    )
    return (data, bool(S_ISDIR(s.st_mode)), bool(S_ISREG(s.st_mode)))


def _walktree(top: str, parent: int, db: Database):
    '''Recursively descend the directory tree rooted at top, inserting dentries
    into the database.
    '''

    for f in os.listdir(top):
        pathname = os.path.join(top, f)
        try:
            data, isdir, isreg = get_dentry(f, pathname)
        except (FileNotFoundError, PermissionError):
            continue

        # Insert into database
        new_parent = db.insert_dentry(parent, *data)

        if isdir:
            _walktree(pathname, new_parent, db)


def walktree(root: str, db: Database):
    data, isdir, isreg = get_dentry(
        os.path.basename(os.path.normpath(root)), root
    )
    parent = db.insert_dentry(None, *data)
    if isdir:
        _walktree(root, parent, db)
