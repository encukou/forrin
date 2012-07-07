import os
import sqlite3

import polib

from forrin.util import reify


class SQLiteBackend(object):
    def __init__(self, domain, directory, languages, _db=None):
        self.domain = domain
        self.directory = directory
        self.languages = languages
        if self.languages:
            self.lang = self.languages[0]
        else:
            self.gettext = self.gettext_source
            self.ngettext = self.ngettext_source
            return

        self.po_path = os.path.join(directory, '%s.po' % self.lang)
        if not os.path.exists(self.po_path):
            return self.__init__(domain, directory, languages[1:])

        if _db:
            self.db = _db
        else:
            db_filename = os.path.join(directory, '%s.forrin-db' % domain)
            try:
                self.db = sqlite3.connect(db_filename)
            except IOError:
                # Can't connect, use temporary DB
                self.db = sqlite3.connect(":memory:")

            self.db.execute('''CREATE TABLE IF NOT EXISTS source (
                    id INTEGER PRIMARY KEY,
                    text TEXT UNIQUE)
                ''')

            self.db.execute('''CREATE TABLE IF NOT EXISTS language (
                    lang TEXT PRIMARY KEY,
                    source_mtime INTEGER,
                    source_size INTEGER)
                ''')

            self.db.execute('''CREATE TABLE IF NOT EXISTS translation (
                    source_id INTEGER REFERENCES source(id),
                    lang TEXT REFERENCES language(lang),
                    plural_number INTEGER,
                    translation TEXT,
                    PRIMARY KEY (source_id, lang, plural_number))
                ''')

        stat = os.stat(self.po_path)

        must_recreate = True
        for mtime, size in self.db.execute('''
                SELECT source_mtime, source_size
                FROM language
                WHERE lang = ?
                ''', [self.lang]):
            if mtime == stat.st_mtime and size == stat.st_size:
                must_recreate = False

        if must_recreate:
            self.db.execute('''DELETE FROM translation
                    WHERE lang = ?''', [self.lang])
            self.db.execute('''DELETE FROM language
                    WHERE lang = ?''', [self.lang])

            messages = [m for m in polib.pofile(self.po_path) if
                m.msgstr and not (m.obsolete or 'fuzzy' in m.flags)]

            self.db.executemany('''INSERT OR IGNORE INTO source
                (text) VALUES (?)
                ''', ([m.msgid] for m in messages))

            self.db.executemany('''INSERT INTO translation
                (plural_number, source_id, lang, translation)
                VALUES (0, (SELECT id FROM SOURCE WHERE text=?), ?, ?)
                ''', ((m.msgid, self.lang, m.msgstr) for m in messages))

            self.db.execute('''INSERT INTO language
                (lang, source_mtime, source_size) VALUES (?, ?, ?)
                ''', (self.lang, stat.st_mtime, stat.st_size))

            self.db.commit()

    @reify
    def fallback(self):
        remaining_languages = self.languages[1:]
        return SQLiteBackend(self.domain, self.directory, remaining_languages,
            _db=self.db)

    def gettext_source(self, msgid):
        return msgid

    def ngettext_source(self, msgid, plural, n):
        if n == 1:
            return msgid
        else:
            return plural

    def gettext(self, msgid, _n=0):
        for [msgstr] in self.db.execute('''SELECT translation.translation
                FROM translation
                INNER JOIN source ON (source.id = translation.source_id)
                WHERE translation.lang=? AND source.text=? AND plural_number=?
                ''', (self.lang, msgid, _n)):
            return msgstr
        return self.fallback.gettext(msgid)

    def ngettext(self, msgid, plural, n):
        # XXX: implement
        return self.gettext(msgid)

    ugettext = gettext
    ungettext = ngettext
