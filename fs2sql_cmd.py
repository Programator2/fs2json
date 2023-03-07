#!/usr/bin/env python3
from db import Database
from fs2sql import walktree
import sys


if __name__ == '__main__':
    db = Database('fs.db', drop=True)
    db.insert_unix_database()
    walktree(sys.argv[1], db)
    db.close()
