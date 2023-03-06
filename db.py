#!/usr/bin/env python3
import sqlite3
from collections import namedtuple
import pwd
import grp


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
    ],
)


class Database:
    def __init__(self, path):
        self.con = sqlite3.connect(path, isolation_level=None)
        self.cur = self.con.cursor()
        self.create_db()
        self.cur.execute('PRAGMA synchronous = OFF')
        self.cur.execute('PRAGMA journal_mode = MEMORY')
        self.cur.execute('BEGIN TRANSACTION')

    def create_db(self):
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS fs(parent INTEGER, name TEXT, ino INTEGER, dev INTEGER, nlink INTEGER, uid INTEGER, gid INTEGER, size INTEGER, atime INTEGER, mtime INTEGER, ctime INTEGER, type INTEGER, mode INTEGER)"
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
    ):
        """Execute INSERT statement for a dentry.

        :returns: rowid of inserted row
        """
        self.cur.execute(
            'INSERT INTO fs VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
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

    def close(self):
        self.cur.execute('END TRANSACTION')
        self.cur.execute('CREATE INDEX parent_index ON fs (parent)')
        self.con.commit()
        self.cur.close()
        self.con.close()


class DatabaseRead:
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
        self, path: str, children=False
    ) -> tuple | Inode | list[Inode]:
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
                    return Inode(*row)
                # Get ID of the last component
                res = self.cur.execute(
                    'SELECT rowid FROM fs WHERE parent = ? AND name = ?',
                    (current_folder, e),
                )
                row = res.fetchone()
                current_folder = row[0]
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
        info = self.search_path(path)
        return info.uid

    def get_children(self, path: str) -> list[Inode]:
        return self.search_path(path, children=True)

    def close(self):
        self.cur.close()
        self.con.close()
