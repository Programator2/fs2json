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
