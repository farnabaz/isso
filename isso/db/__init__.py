# -*- encoding: utf-8 -*-

import sqlite3
import logging
import operator
import os.path

from collections import defaultdict

logger = logging.getLogger("isso")

from isso.compat import buffer

from isso.db.comments import Comments
from isso.db.threads import Threads
from isso.db.spam import Guard
from isso.db.preferences import Preferences


import MySQLdb


class SQLite3:
    """DB-dependend wrapper around SQLite3.

    Runs migration if `user_version` is older than `MAX_VERSION` and register
    a trigger for automated orphan removal.
    """

    MAX_VERSION = 3

    def __init__(self, path, conf):

        self.path = os.path.expanduser(path)
        self.conf = conf
        self.host = conf.get('mysql', 'host')
        self.user = conf.get('mysql', 'user')
        self.passwd = conf.get('mysql', 'passwd')
        self.db = conf.get('mysql', 'db')

        rv = None

        self.preferences = Preferences(self)
        self.threads = Threads(self)
        self.comments = Comments(self)
        self.guard = Guard(self)


    def execute(self, sql, args=()):

        if isinstance(sql, (list, tuple)):
            sql = ' '.join(sql)

        with MySQLdb.connect(host=self.host, user=self.user, passwd=self.passwd,
                             db=self.db, charset='utf8') as cur:
            cur.execute(sql, args)
            return cur;

    @property
    def version(self):
        return self.execute("PRAGMA user_version").fetchone()[0]

    def migrate(self, to):

        if self.version >= to:
            return

        logger.info("migrate database from version %i to %i", self.version, to)

        # re-initialize voters blob due a bug in the bloomfilter signature
        # which added older commenter's ip addresses to the current voters blob
        if self.version == 0:

            from isso.utils import Bloomfilter
            bf = buffer(Bloomfilter(iterable=["127.0.0.0"]).array)

            with sqlite3.connect(self.path) as con:
                con.execute('UPDATE comments SET voters=?', (bf, ))
                con.execute('PRAGMA user_version = 1')
                logger.info("%i rows changed", con.total_changes)

        # move [general] session-key to database
        if self.version == 1:

            with sqlite3.connect(self.path) as con:
                if self.conf.has_option("general", "session-key"):
                    con.execute('UPDATE preferences SET value=? WHERE key=?', (
                        self.conf.get("general", "session-key"), "session-key"))

                con.execute('PRAGMA user_version = 2')
                logger.info("%i rows changed", con.total_changes)

        # limit max. nesting level to 1
        if self.version == 2:

            first = lambda rv: list(map(operator.itemgetter(0), rv))

            with sqlite3.connect(self.path) as con:
                top = first(con.execute("SELECT id FROM comments WHERE parent IS NULL").fetchall())
                flattened = defaultdict(set)

                for id in top:

                    ids = [id, ]

                    while ids:
                        rv = first(con.execute("SELECT id FROM comments WHERE parent=?", (ids.pop(), )))
                        ids.extend(rv)
                        flattened[id].update(set(rv))

                for id in flattened.keys():
                    for n in flattened[id]:
                        con.execute("UPDATE comments SET parent=? WHERE id=?", (id, n))

                con.execute('PRAGMA user_version = 3')
                logger.info("%i rows changed", con.total_changes)
