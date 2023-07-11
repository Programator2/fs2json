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
from .db import Database
from .fs2sql import walktree
import sys


if __name__ == '__main__':
    db = Database('fs.db')
    # db.insert_unix_database()
    # walktree(sys.argv[1], db)
    db.insert_selinux_accesses(
        'postgresql1',
        'system_u:system_r:postgresql_t:s0',
        [
            'postgresql_db_t',
            'posthresql_etc_t',
            'postgresql_initrc_exec_t',
            'postgresql_exec_t',
            'postgresql_log_t',
            'postgresql_var_run_t',
        ],
        verbose=True,
    )
    db.close()
