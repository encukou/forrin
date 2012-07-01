from __future__ import print_function, unicode_literals

from polib import POFile, POEntry, pofile
from datetime import datetime

import forrin


class POTFile(POFile):
    def __init__(self,
            fpath=None,
            wrapwidth=78,
            project_name=None,
            project_version=None,
            project_i18n_contact=None,
            **metadata
        ):
        super(POTFile, self).__init__(fpath, wrapwidth)
        self._msg_dict = dict()
        if project_name:
            if project_version:
                metadata.setdefault('Project-Id-Version',
                    "%s %s" % (project_name, project_version))
            else:
                metadata.setdefault('Project-Id', project_name)
        if project_i18n_contact:
            metadata.setdefault('Report-Msgid-Bugs-To', project_i18n_contact)
        metadata.setdefault('POT-Creation-Date', datetime.now().isoformat())
        metadata.setdefault('PO-Revision-Date', 'YEAR-MO-DA HO:MI+ZONE')
        metadata.setdefault('Last-Translator', 'FULL NAME <EMAIL@ADDRESS>')
        metadata.setdefault('Language-Team', 'LANGUAGE <LL@li.org>')
        metadata.setdefault('MIME-Version', '1.0')
        metadata.setdefault('Content-Type', 'text/plain; charset=utf-8')
        metadata.setdefault('Content-Transfer-Encoding', '8bit')
        metadata.setdefault('Generated-By', 'forrin %s' % forrin.__version__)
        self.metadata = metadata

    def add(self, message):
        merge_key = message.msgid, message.msgid_plural
        try:
            prev = self._msg_dict[merge_key]
        except KeyError:
            self.append(message)
            self._msg_dict[merge_key] = message
        else:
            prev.occurrences += message.occurrences
            if prev.comment and message.comment:
                prev.comment += '\n\n'
            prev.comment += message.comment

    def add_messages(self, messages):
        for message in messages:
            self.add(message)
