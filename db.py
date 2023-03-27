"""Filesystem database in sqlite format.

Doesn't support updating, database has to be recreated everytime.
"""
import sqlite3
from collections import namedtuple
import os
import stat
from collections.abc import Iterable
from .helpers import construct_selinux_context, selinux_check_access

if os.name == 'posix':
    import pwd
    import grp
from itertools import chain
from pprint import pprint


Inode = namedtuple(
    'Inode',
    [
        'parent',
        'name',
        'ino',
        'dev',
        'nlink',
        'uid',
        'gid',
        'size',
        'atime',
        'mtime',
        'ctime',
        'type',
        'mode',
        'selinux_user',
        'selinux_role',
        'selinux_type',
        'selinux_sensitivity',
        'selinux_category',
    ],
)


class DatabaseCommon:
    def get_paths_by_selinux_type(self, types: Iterable[str]):
        """Return list of paths that match types listed in `_types`."""
        expr = (f'selinux_type == "{t}"' for t in types)
        select = f'''WITH RECURSIVE child AS
(
  SELECT rowid AS original, rowid, parent, name, type, selinux_user, selinux_role, selinux_type, selinux_sensitivity, selinux_category
  FROM fs
  WHERE ({" OR ".join(expr)})

  UNION ALL

  SELECT original, fs.rowid, fs.parent, fs.name || '/' || child.name, child.type, child.selinux_user, child.selinux_role, child.selinux_type, child.selinux_sensitivity, child.selinux_category
  FROM fs, child
  WHERE child.parent = fs.rowid
)
SELECT original, name, type, selinux_user, selinux_role, selinux_type, selinux_sensitivity, selinux_category
From child
WHERE rowid = 1'''
        res = self.cur.execute(select)
        return res.fetchall()
        return list(chain.from_iterable(res.fetchall()))

    def get_case_id(self, case: str) -> int:
        res = self.cur.execute(
            'SELECT rowid FROM cases WHERE name = ?',
            (case,),
        )
        row = res.fetchone()
        # TODO: Handle row being `None`
        return row[0]

    def get_context_id(self, context: str) -> int:
        res = self.cur.execute(
            'SELECT rowid FROM contexts WHERE name = ?',
            (context,),
        )
        row = res.fetchone()
        # TODO: Handle row being `None`
        return row[0]

    def get_operations_id(self, operations: Iterable[str]) -> list[int]:
        ret = []
        for operation in operations:
            res = self.cur.execute(
                'SELECT rowid FROM operations WHERE operation = ?',
                (operation,),
            )
            row = res.fetchone()
            ret.append(row[0])
        # TODO: Handle row being `None`
        return ret

    def get_access(self, case_id: int, subject_cid: int, path_rowid: int) -> int | None:
            res = self.cur.execute(
                '''SELECT rowid FROM accesses WHERE
                case_id = ? AND
                subject_cid = ? AND
                node_rowid = ?''',
                (
                    case_id,
                    subject_cid,
                    path_rowid,
                ),
            )
            row = res.fetchone()
            if row is None:
                return None
            return row[0]

    def get_children(self, parent_rowid: int) -> list[tuple[int, str]]:
        res = self.cur.execute(
            'SELECT rowid, name FROM fs WHERE parent = ?',
            (parent_rowid,),
        )
        return res.fetchall()


class DatabaseWriter(DatabaseCommon):
    """Database with read-write support."""

    def __init__(self, path: str):
        self.con = sqlite3.connect(path, isolation_level=None)
        self.cur = self.con.cursor()

    def insert_access(self, case_id: int, subject_cid: int, path_rowid: int) -> int:
            self.cur.execute(
                'INSERT INTO accesses VALUES(?, ?, ?)',
                (
                    case_id,
                    subject_cid,
                    path_rowid,
                ),
            )
            return self.cur.lastrowid

    def insert_or_select_access(self, case_id: int, subject_cid: int, path_rowid: int) -> int:
        if (rowid := self.get_access(case_id, subject_cid, path_rowid)) is None:
            return self.insert_access(case_id, subject_cid, path_rowid)
        return rowid

    def close(self):
        self.con.commit()
        self.cur.close()
        self.con.close()


class DatabaseCreator(DatabaseWriter):
    """Creation of the database."""

    def __init__(self, path: str, drop: bool = False):
        super().__init__(path)
        if drop:
            self.drop_db()
        self.create_db()
        self.cur.execute('PRAGMA synchronous = OFF')
        self.cur.execute('PRAGMA journal_mode = MEMORY')
        self.cur.execute('BEGIN TRANSACTION')

    def drop_db(self):
        self.cur.executescript(
            """DROP TABLE IF EXISTS fs;
            DROP TABLE IF EXISTS users;
            DROP TABLE IF EXISTS groups;
            DROP TABLE IF EXISTS membership;
            """
        )

    def create_db(self):
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS fs(parent INTEGER, name TEXT, ino INTEGER, dev INTEGER, nlink INTEGER, uid INTEGER, gid INTEGER, size INTEGER, atime INTEGER, mtime INTEGER, ctime INTEGER, type INTEGER, mode INTEGER, selinux_user TEXT, selinux_role TEXT, selinux_type TEXT, selinux_sensitivity TEXT, selinux_category TEXT)"
        )
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS users(name TEXT, uid INTEGER PRIMARY KEY, gid INTEGER)"
        )
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS groups(name TEXT, gid INTEGER PRIMARY KEY)"
        )
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS membership(uid INTEGER, gid INTEGER)"
        )

    def insert_dentry(
        self,
        parent,
        name,
        ino,
        dev,
        nlink,
        uid,
        gid,
        size,
        atime,
        mtime,
        ctime,
        _type,
        mode,
        selinux_user,
        selinux_role,
        selinux_type,
        selinux_sensitivity,
        selinux_category,
    ):
        """Execute INSERT statement for a dentry.

        :returns: rowid of inserted row
        """
        self.cur.execute(
            'INSERT INTO fs VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                parent,
                name,
                ino,
                dev,
                nlink,
                uid,
                gid,
                size,
                atime,
                mtime,
                ctime,
                _type,
                mode,
                selinux_user,
                selinux_role,
                selinux_type,
                selinux_sensitivity,
                selinux_category,
            ),
        )
        return self.cur.lastrowid

    def insert_unix_database(self):
        """Insert unix users and group information into the database.

        This should be called just once. The method doesn't check this.
        """
        users = pwd.getpwall()
        for u in users:
            self.cur.execute(
                'INSERT INTO users VALUES(?, ?, ?)',
                (u.pw_name, u.pw_uid, u.pw_gid),
            )
        groups = grp.getgrall()
        for g in groups:
            self.cur.execute(
                'INSERT INTO groups VALUES(?, ?)', (g.gr_name, g.gr_gid)
            )
            for username in g.gr_mem:
                self.cur.execute(
                    f"INSERT INTO membership SELECT uid, '{g.gr_gid}' FROM users WHERE name = ?",
                    (username,),
                )

    def _prepare_accesses(self):
        self.cur.execute(
            """CREATE TABLE IF NOT EXISTS accesses (
            case_id INTEGER,
            subject_cid INTEGER,
            node_rowid INTEGER,
            UNIQUE (case_id, subject_cid, node_rowid) ON CONFLICT IGNORE
            )"""
        )
        self.cur.execute(
            """CREATE TABLE IF NOT EXISTS results (
            access_id INTEGER,
            operation_id INTEGER,
            reference_result INTEGER,
            medusa_result INTEGER,
            PRIMARY KEY (access_id, operation_id)
            )"""
        )
        self.cur.execute(
            'CREATE INDEX IF NOT EXISTS case_index ON accesses (case_id)'
        )
        self.cur.execute(
            'CREATE INDEX IF NOT EXISTS access_index ON results (access_id)'
        )
        self.cur.execute("CREATE TABLE IF NOT EXISTS cases(name TEXT UNIQUE)")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS contexts(name TEXT UNIQUE)"
        )
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS operations(operation TEXT UNIQUE)"
        )
        self.cur.executemany(
            'INSERT INTO operations VALUES(?) ON CONFLICT DO NOTHING',
            (('read',), ('write',)),
        )
        self.cur.execute(
            """CREATE VIEW IF NOT EXISTS translated_accesses AS
WITH RECURSIVE child AS
(
SELECT 	accesses.case_id, accesses.node_rowid, accesses.subject_cid,
		cases.name AS case_name, contexts.name AS subject_context,
		fs.rowid, fs.parent, fs.name, operation,
		results.reference_result, results.medusa_result FROM accesses
JOIN cases ON case_id = cases.rowid
JOIN contexts ON subject_cid = contexts.rowid
JOIN fs ON node_rowid = fs.rowid
JOIN results ON accesses.ROWID = results.access_id
JOIN operations ON results.operation_id = operations.rowid

UNION ALL

SELECT case_id, node_rowid, subject_cid, case_name, subject_context, fs.rowid, fs.parent, fs.name || '/' || child.name, operation, reference_result, medusa_result
FROM fs, child
WHERE child.parent = fs.rowid
)
SELECT case_id, case_name, subject_cid, subject_context, node_rowid, name AS path, operation, reference_result, medusa_result
From child
WHERE rowid = 1"""
        )

    def insert_selinux_accesses(
        self,
        case_name: str,
        subject_context: str,
        object_types: Iterable[str],
        verbose: bool = False,
    ):
        """Fill accesses table in the database.

        Fill a table with SELinux accesses from `subject_context` to all files
        with types from `selinux_types`.

        :param case_name: Name of the service that is examined. This will be
        used as a unique value in the database.
        :param subject_context: SELinux context of the subject.
        :param object_types:SELinux types that will be searched in the database
        and found files will be examined for read and write permissions from the
        subject.
        :param verbose: Turns on verbose output.
        """
        self._prepare_accesses()
        self.cur.execute(
            'INSERT INTO cases VALUES(?) ON CONFLICT DO NOTHING',
            (case_name,),
        )
        case_id = self.get_case_id(case_name)
        self.cur.execute(
            'INSERT INTO contexts VALUES(?) ON CONFLICT DO NOTHING',
            (subject_context,),
        )
        subject_cid = self.get_context_id(subject_context)
        files = self.get_paths_by_selinux_type(object_types)
        perms = ('read', 'write')
        perms_id = self.get_operations_id(perms)
        for (
            rowid,
            path,
            _type,
            selinux_user,
            selinux_role,
            selinux_type,
            selinux_sensitivity,
            selinux_category,
        ) in files:
            context = construct_selinux_context(
                selinux_user,
                selinux_role,
                selinux_type,
                selinux_sensitivity,
                selinux_category,
            )
            is_dir = stat.S_ISDIR(_type)
            _class = 'dir' if is_dir else 'file'

            results = [
                selinux_check_access(subject_context, context, _class, perm)
                for perm in perms
            ]
            if verbose:
                for perm, result in zip(perms, results):
                    print(
                        f'{subject_context}=>{context} {path} ({_class}:{perm})={result}'
                    )
            self.cur.execute(
                'INSERT INTO accesses VALUES(?, ?, ?)',
                (
                    case_id,
                    subject_cid,
                    rowid,
                ),
            )

            access_id = self.cur.lastrowid

            for perm_id, result in zip(perms_id, results):
                self.cur.execute(
                    'INSERT INTO results VALUES(?, ?, ?, null)',
                    (
                        access_id,
                        perm_id,
                        result,
                    ),
                )

    def close(self):
        self.cur.execute('END TRANSACTION')
        self.cur.execute(
            'CREATE INDEX IF NOT EXISTS parent_index ON fs (parent)'
        )
        self.cur.execute(
            'CREATE INDEX IF NOT EXISTS selinux_type_index ON fs (selinux_type)'
        )
        super().close()


class DatabaseRead(DatabaseCommon):
    """Reading support from the database."""

    def __init__(self, path):
        self.con = sqlite3.connect(path)
        self.cur = self.con.cursor()

    @staticmethod
    def _create_path(path: str):
        """Create necessary nodes in the tree to represent a path.

        :param path: string in the form of `/this/is/a/path`. It has to start
        with a `/` and optionally end with a `/`.
        """
        return filter(lambda x: bool(x), path.split('/'))

    def search_path(
        self, path: str, children: bool = False, number: bool = False
    ) -> tuple | Inode | list[Inode] | int:
        """Return inode metadata from the database if it exists.

        :param path: Return inode metadata of object at this path.
        :param children: If `True`, return children items of `path`.
        """
        entries = tuple(self._create_path(path))

        # Root should be stored under rowid 1 in the database
        current_folder = 1

        for i, e in enumerate(entries):
            if i == len(entries) - 1:
                # Final path component
                if not children:
                    # Just return inode metadata about the last component
                    res = self.cur.execute(
                        'SELECT * FROM fs WHERE parent = ? AND name = ?',
                        (current_folder, e),
                    )
                    row = res.fetchone()
                    if row is None:
                        # path doesn't exist
                        return tuple()
                    return Inode(*row)
                # Get ID of the last component
                res = self.cur.execute(
                    'SELECT rowid FROM fs WHERE parent = ? AND name = ?',
                    (current_folder, e),
                )
                row = res.fetchone()
                if row is None:
                    # path doesn't exist
                    return tuple()
                current_folder = row[0]
                if number:
                    # Get just the number of items
                    res = self.cur.execute(
                        'SELECT COUNT(*) FROM fs WHERE parent = ?',
                        (current_folder,),
                    )
                    row = res.fetchone()
                    return row[0]
                # Continue with contents of this directory
                res = self.cur.execute(
                    'SELECT * FROM fs WHERE parent = ?',
                    (current_folder,),
                )
                rows = res.fetchall()
                return [Inode(*x) for x in rows]

            res = self.cur.execute(
                'SELECT rowid FROM fs WHERE parent = ? AND name = ?',
                (current_folder, e),
            )
            if (row := res.fetchone()) is None:
                # Directory does not exist
                return tuple()
            current_folder = row[0]

        return tuple()

    def get_owner(self, path: str) -> int:
        """Return owner UID of a file located at `path`."""
        info = self.search_path(path)
        return info.uid

    def is_directory(self, path: str) -> bool:
        """Return `True` if `path` points to a directory. If the `path` doesn't
        exist, return `False`."""
        info = self.search_path(path)
        if not info:
            return False
        return stat.S_ISDIR(info.type)

    def get_children(self, path: str) -> list[Inode]:
        """Return a list of `Inode` data contained in a directory at `path`."""
        return self.search_path(path, children=True)

    def get_num_children(self, path: str) -> int:
        """Return number of items in folder at `path`."""
        return self.search_path(path, children=True, number=True)

    def _get_membership(self, uid: int) -> list[int]:
        """Return a list of group IDs for user with a give `uid`.

        This includes user's main group and also supplementary groups.
        """
        groups = []
        res = self.cur.execute(
            'SELECT gid FROM users WHERE uid = ?',
            (uid,),
        )
        gid = res.fetchall()
        res = self.cur.execute(
            'SELECT gid FROM membership WHERE uid = ?',
            (uid,),
        )
        supplementary = res.fetchall()
        return list(chain(*gid, *supplementary))

    def _has_permission(
        self, inode: Inode, uid: int, owner: int, group: int, others: int
    ) -> bool:
        """Check if `inode` has permissions for user with `uid`.

        :param owner: permission from `stat` module compared when user is owner
        of the file.
        :param group: permission from `stat` module compared when user is member
        of the file group.
        :param others: permission from `stat` module compared otherwise.
        """
        if inode.uid == uid:
            return bool(inode.mode & owner)
        elif inode.gid in self._get_membership(uid):
            return bool(inode.mode & group)
        else:
            return bool(inode.mode & others)

    def can_read(self, ino: Inode, uid: int) -> bool:
        """Check if `ino` can be read by user with `uid`."""
        return self._has_permission(
            ino, uid, stat.S_IRUSR, stat.S_IRGRP, stat.S_IROTH
        )

    def can_write(self, ino: Inode, uid: int) -> bool:
        """Check if `ino` can be written by user with `uid`."""
        return self._has_permission(
            ino, uid, stat.S_IWUSR, stat.S_IWGRP, stat.S_IWOTH
        )

    def get_reference_accesses(self, case: str, contexts: Iterable[str]):
        """
        :param case: Name of the case from which to retrieve accesses.
        :param contexts: Names of subject contexts which will be used to compare
        accesses.
        """
        case_id = self.get_case_id(case)
        context_ids = [self.get_context_id(c) for c in contexts]
        expr = (f'subject_cid == "{c}"' for c in context_ids)
        ret = self.cur.execute(
            f"""WITH RECURSIVE child AS
(
SELECT accesses.case_id, accesses.node_rowid, accesses.subject_cid, accesses.read, accesses.write, cases.name AS case_name, contexts.name AS subject_context, fs.rowid, fs.parent, fs.name FROM accesses
JOIN cases ON case_id = cases.rowid
JOIN contexts ON subject_cid = contexts.rowid
JOIN fs ON node_rowid = fs.rowid
WHERE case_id = ? AND ({" OR ".join(expr)})

UNION ALL

SELECT case_id, node_rowid, subject_cid, read, write, case_name, subject_context, fs.rowid, fs.parent, fs.name || '/' || child.name
FROM fs, child
WHERE child.parent = fs.rowid
)
SELECT name AS path, read, write
From child
WHERE rowid = 1""",
            (case_id,),
        )
        return ret.fetchall()

    def close(self):
        self.cur.close()
        self.con.close()
