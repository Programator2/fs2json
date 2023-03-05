#!/usr/bin/python3
from os import stat, listdir
import os
from stat import *
import json
import sys


def get_json(filename, path):
    s = stat(path, follow_symlinks=False)
    r = {
        'name': filename,
        'ino': s.st_ino,
        'dev': s.st_dev,
        'nlink': s.st_nlink,
        'uid': s.st_uid,
        'gid': s.st_gid,
        'size': s.st_size,
        'atime': s.st_atime,
        'mtime': s.st_mtime,
        'ctime': s.st_ctime,
        'ifsock': int(bool(S_ISSOCK(s.st_mode))),
        'iflnk': int(bool(S_ISLNK(s.st_mode))),
        'ifblk': int(bool(S_ISBLK(s.st_mode))),
        'isreg': int(bool(S_ISREG(s.st_mode))),
        'ifdir': int(bool(S_ISDIR(s.st_mode))),
        'ifchr': int(bool(S_ISCHR(s.st_mode))),
        'ififo': int(bool(S_ISFIFO(s.st_mode))),
        'isuid': int(bool(s.st_mode & S_ISUID)),
        'isgid': int(bool(s.st_mode & S_ISGID)),
        'isvtx': int(bool(s.st_mode & S_ISVTX)),
        'irusr': int(bool(s.st_mode & S_IRUSR)),
        'iwusr': int(bool(s.st_mode & S_IWUSR)),
        'ixusr': int(bool(s.st_mode & S_IXUSR)),
        'irgrp': int(bool(s.st_mode & S_IRGRP)),
        'iwgrp': int(bool(s.st_mode & S_IWGRP)),
        'ixgrp': int(bool(s.st_mode & S_IXGRP)),
        'iroth': int(bool(s.st_mode & S_IROTH)),
        'iwoth': int(bool(s.st_mode & S_IWOTH)),
        'ixoth': int(bool(s.st_mode & S_IXOTH)),
        }
    return (json.dumps(r),
            bool(S_ISDIR(s.st_mode)),
            bool(S_ISREG(s.st_mode)))


def _walktree(top):
    '''recursively descend the directory tree rooted at top,
       calling the callback function for each regular file'''

    i = 0
    for f in os.listdir(top):
        pathname = os.path.join(top, f)
        try:
            info, isdir, isreg = get_json(f, pathname)
        except (FileNotFoundError, PermissionError):
            continue

        # Continuing output in children list needs a comma
        if i != 0:
            info = ', ' + info

        if isdir:
            # It's a directory, recurse into it
            # create children in json
            info = info[:-1] + ', "children": ['
            print(info, end='')
            _walktree(pathname)
            # close children in json
            print(']}', end='')
        else:
            print(info, end='')
        i += 1


def walktree(root):
    info, isdir, isreg = get_json(os.path.basename(os.path.normpath(root)), root)
    if isdir:
        # It's a directory, recurse into it
        # create children in json
        info = info[:-1] + ', "children": ['
        print(info, end='')
        _walktree(root)
        # close children in json
        print(']}', end='')
    else:
        print(info, end='')
    print()


if __name__ == '__main__':
    walktree(sys.argv[1])
