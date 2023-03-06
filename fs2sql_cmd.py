#!/usr/bin/env python3
from db import Database


if __name__ == '__main__':
    db = Database('unix.db')
    db.insert_unix_database()
    #walktree(sys.argv[1], db)
    db.close()
