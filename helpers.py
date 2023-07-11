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

"""Helper functions."""
try:
    from selinux import (
        selinux_check_access as check_access,
        selabel_lookup,
        selabel_open,
        SELABEL_CTX_FILE,
        selinux_opt,
        selabel_close,
        context_free,
        getfilecon
    )
except ImportError:
    pass
import sys


def construct_selinux_context(
    selinux_user: str,
    selinux_role: str,
    selinux_type: str,
    selinux_sensitivity: str,
    selinux_category: str,
) -> str:
    """Return SELinux context as string from its parts."""
    context = [selinux_user, selinux_role, selinux_type, selinux_sensitivity]
    if selinux_category is not None:
        context.append(selinux_category)
    return ':'.join(context)


def selinux_check_access(scon, tcon, tclass, perm):
    code = {0: 1}
    try:
        ret = check_access(scon, tcon, tclass, perm)
    except PermissionError:
        return 0
    except TypeError:
        print('error:', scon, tcon, tclass, perm)
        sys.exit(-1)
    return code.get(ret, 0)


def selinux_label_lookup(path: str, mode: int) -> str | None:
    """
    :param path: Path of the file which to look up.
    :param mode: mode of `path as returned by lstat.
    `"""
    handle = selabel_open(SELABEL_CTX_FILE, None, 0)
    # context is a list
    try:
        context = selabel_lookup(handle, path, mode)
    except FileNotFoundError:
        # This is weird. Happens for paths such as `/proc/meminfo`. Let's try
        # again, this time getting the information right from the filesystem
        #
        # `context` is a list [return value, actual context]
        try:
            context = getfilecon(path)
        except FileNotFoundError:
            print(f"Can't get context for {path}.", file=sys.stderr)
            return None
        selabel_close(handle)
        return context[1]
    selabel_close(handle)
    return context[1]
