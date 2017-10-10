"""
A simple script that backs a sqlite database up.

Properly locks the database while copying to prevent modifications.

TODO
* Support gzip?
"""

import os
import shutil
import sqlite3
import time


def sqlite3_backup(dbfile, backupdir):
    """Create timestamped database copy"""

    if not os.path.isdir(backupdir):
        raise Exception("Backup directory does not exist: {}".format(backupdir))

    backup_file = os.path.join(backupdir, os.path.basename(dbfile) +
                               time.strftime("-%Y%m%d-%H%M%S"))

    connection = sqlite3.connect(dbfile)
    cursor = connection.cursor()

    # Lock database before making a backup
    cursor.execute('begin immediate')
    # Make new backup file
    shutil.copyfile(dbfile, backup_file)
    print ("\nCreating {}...".format(backup_file))
    # Unlock database
    connection.rollback()


def clean_data(backup_dir, no_of_days=7):

    """Delete files older than NO_OF_DAYS days"""

    print ("\n------------------------------")
    print ("Cleaning up old backups")

    for filename in os.listdir(backup_dir):
        backup_file = os.path.join(backup_dir, filename)
        if os.stat(backup_file).st_ctime < (time.time() - no_of_days * 86400):
            if os.path.isfile(backup_file):
                os.remove(backup_file)
                print ("Deleting {}...".format(backup_file))


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description='Fix internal links in imported Elog entries.')

    parser.add_argument("elogy_database", metavar="DB", type=str, help="The elogy database file")
    parser.add_argument("-b", "--backup", metavar="DIR", default="backups",
                        help="Directory in which to store backups (defaults to './backups'")
    parser.add_argument("-k", "--keep", type=int, default=0, metavar="DAYS",
                        help="Number of days of backups to keep (defaults to infinite)")

    args = parser.parse_args()

    sqlite3_backup(args.elogy_database, args.backup)
    if args.keep > 0:
        clean_data(args.backup, args.keep)
