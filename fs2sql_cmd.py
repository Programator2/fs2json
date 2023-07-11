#!/usr/bin/env python3
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

from fs2json.db import DatabaseCreator
from fs2json.fs2sql import walktree
import sys


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} dir output_path')
    db = DatabaseCreator(sys.argv[2], drop=True)
    db.insert_unix_database()
    walktree(sys.argv[1], db)
    db.close()
