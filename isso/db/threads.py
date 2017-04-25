# -*- encoding: utf-8 -*-


def Thread(id, uri, title):
    return {
        "id": id,
        "uri": uri,
        "title": title
    }


class Threads(object):

    def __init__(self, db):

        self.db = db
        self.db.execute([
            'CREATE TABLE IF NOT EXISTS threads (',
            '    `id` INTEGER(11) UNSIGNED AUTO_INCREMENT,',
            ' `uri` VARCHAR(128) UNIQUE, title VARCHAR(256),'
            ' PRIMARY KEY(`id`)',
            ');'
            ])

    def __contains__(self, uri):
        print (self.db.execute("SELECT title FROM threads WHERE uri=%s", (uri, )) \
                      .fetchone() is not None)
        return self.db.execute("SELECT title FROM threads WHERE uri=%s", (uri, )) \
                      .fetchone() is not None

    def __getitem__(self, uri):
        print(self.db.execute("SELECT * FROM threads WHERE uri=%s", (uri, )).fetchone())
        return Thread(*self.db.execute("SELECT * FROM threads WHERE uri=%s", (uri, )).fetchone())

    def new(self, uri, title):
        self.db.execute("INSERT INTO threads (uri, title) VALUES (%s, %s)", (uri, title))
        return self[uri]
