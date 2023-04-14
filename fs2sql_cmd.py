#!/usr/bin/env python3
from fs2json.db import DatabaseCreator
from fs2json.fs2sql import walktree
import sys


if __name__ == '__main__':
    db = DatabaseCreator('fs.db', drop=True)
    db.insert_unix_database()
    walktree(sys.argv[1], db)
    db.close()
