#  Copyright (C) 2021-2023 Roderik Ploszek
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from os import stat, listdir
import os
from stat import *
import json
import sys
from .db import DatabaseCreator


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


def _walktree(top: str, parent: int, db: DatabaseCreator):
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


def walktree(root: str, db: DatabaseCreator):
    data, isdir, isreg = get_dentry(
        os.path.basename(os.path.normpath(root)), root
    )
    parent = db.insert_dentry(None, *data)
    if isdir:
        _walktree(root, parent, db)
