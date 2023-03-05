#!/usr/bin/python3
from os import stat, listdir
import os
from stat import *
import json
import sys
from fs2json.db import Database


def get_dentry(filename, path):
    s = stat(path, follow_symlinks=False)
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
    )
    return (data, bool(S_ISDIR(s.st_mode)), bool(S_ISREG(s.st_mode)))


def _walktree(top: str, parent: int):
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
            _walktree(pathname, new_parent)


def walktree(root: str, db: Database):
    data, isdir, isreg = get_dentry(
        os.path.basename(os.path.normpath(root)), root
    )
    parent = db.insert_dentry(None, *data)
    if isdir:
        _walktree(root, parent)


db = Database('fs.db')
walktree(sys.argv[1], db)
db.close()
