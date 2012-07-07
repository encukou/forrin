# Encoding: UTF-8

"""Tools to manage translation files

To use, create a ForrinTools object and pass it a Translator class.
Then, call the run method.
"""

from __future__ import print_function, unicode_literals, division

import os
import argparse
import textwrap

import six
import pkg_resources
import polib

import forrin.extract
from forrin.message import POTFile


def yield_messages(source_dir, printer=lambda *a, **ka: None):
    """Yield messages from all Python sources in the source_dir tree

    Feel free to use this as an example
    """
    for dirpath, dirnames, filenames in os.walk(source_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                filepath = os.path.join(dirpath, filename)
                printer('Extracting from %s' % filepath)
                for message in forrin.extract.extract_python(filepath):
                    yield message


class ForrinTools(object):
    """A set of tools suite for managing translations
    """
    def __init__(self, translator_class, source_dir=None):
        self.translator_class = translator_class
        translator = self.translator = translator_class()
        self.i18n_dir = translator.i18n_directory
        self.domain = translator.domain
        self.pot_name = os.path.join(self.i18n_dir, '%s.pot' % self.domain)

        if not source_dir:
            source_dir = pkg_resources.resource_filename(
                self.translator.package, '')
        self.source_dir = source_dir

    def yield_messages(self, printer=lambda *a, **ka: None):
        """Yield all messages for this domain"""
        return yield_messages(self.source_dir, printer)

    def extract(self, args):
        """Extract messages to a .pot file, then merge to languages

        Returns the POTFile created
        """
        args.printer('Extracting source messages')
        pot = POTFile(project_name=self.domain)
        for message in yield_messages(self.source_dir, args.printer):
            pot.add(message)
        return pot

    def get_pot(self, args):
        if args.cached_pot:
            args.printer('Reading translations from %s' % self.pot_name)
            return polib.pofile(self.pot_name)
        else:
            return self.extract(args)

    def get_langs(self, args):
        if args.langs is None:
            return list(self.translator.available_languages())
        else:
            return [l for l in args.langs.split(',') if l]

    def merge(self, args):
        """Merge the source pot file with individual language files
        """
        pot = self.get_pot(args)
        for lang in self.get_langs(args):
            po_path = os.path.join(self.i18n_dir, '%s.po' % lang)
            if os.path.exists(po_path):
                args.printer('Merging translations to %s' % po_path)
                po = polib.pofile(po_path)
                po.merge(pot)
            else:
                args.printer('Creating new translation file %s' % po_path)
                po = polib.POFile()
                po.merge(pot)
            yield po, lang, po_path

    def strip(self, args):
        """Strip the per-language .po files to remove extraneous data

        The resulting files are suitable for version control systems.
        """
        pos_with_info = self.merge(args)
        for po, lang, po_path in pos_with_info:
            args.printer('Stripping translations in %s' % po_path)
            po[:] = [m for m in po if m.msgstr]
            for message in po:
                message.occurrences = []
                message.flags = []
                message.comment = message.tcomment = ''
            yield po, lang, po_path

    def save_pos(self, pos_with_info, args):
        for po, lang, po_path in pos_with_info:
            args.printer('Saving %s' % po_path)
            po.save(po_path)

    def print_stats(self, pos_with_info, args):
        bar_len = 50
        template = '{lang:5} {bar} {percent:3} {transl:{num_width}}/{all:{num_width}} {path}'
        pos_with_info = list(pos_with_info)
        results = []
        for po, lang, po_path in pos_with_info:
            n_translated = len(po.translated_entries())
            n_all = len(po)
            num_width = len(str(n_all))
            try:
                completion = n_translated / n_all
                percent = '{0:2d}%'.format(int(round(100 * completion)))
                if n_translated == n_all:
                    percent = 'ALL'
                bar_full = int(round(bar_len * completion))
                bar = '[{0:{1}}]'.format('=' * bar_full, bar_len)
            except ZeroDivisionError:
                completion = 0
                percent = 'N/A'
                bar = '[{0}]'.format(' ' * bar_len)
            results.append(dict(
                lang=lang, bar=bar, percent=percent, transl=n_translated,
                all=n_all, num_width=num_width, path=po_path))
        results.sort(key=lambda d: (-d['transl'], lang))
        for result in results:
            print(template.format(**result))

    def run(self, argv):
        """Run as a command-line program

        :param argv: sys.argv
        """
        parser = argparse.ArgumentParser(prog=os.path.basename(argv[0]),
            description='Manage translations for %s' % self.domain,
            formatter_class=argparse.RawTextHelpFormatter,
            add_help=False)
        parser.add_argument('action', metavar='ACTION',
            help=textwrap.dedent("""
                The action to take:

                update
                    Update .po files to be ready for translation.
                    To create a new rse.po file, give a new
                    language code to the --langs option.

                strip
                    Remove unnecessary information from .po
                    files, making them suitable for committing to
                    a version control system.
                    Use `update` to "expand" the files again.

                extract
                    Extract source messages to a .pot file.
                    That file can be used with translation tools,
                    or to speed up the update later.
                    Use --existing-pot with other actions to use
                    an existing pot file.

                stats
                    Print stats about available translations
                """).strip(),
            default='help', nargs='?', type=six.text_type)
        parser.add_argument('-h', '--help', dest='action',
            action='store_const', const='help',
            help=textwrap.dedent("""
                Show this help message and exit.
                """).strip())
        parser.add_argument('-l', '--langs', metavar='LANGS',
            help=textwrap.dedent("""
                Identifiers of languages to use, comma-separated.
                Examples: `-l en`, `-l en,cs,de`
                Default: all currently available
                """).strip(),
            type=six.text_type)
        parser.add_argument('--existing-pot',
            help=textwrap.dedent("""
                Use an existing pot file.
                By default, fresh messages are extracted from the
                source code each time they're used. With this flag,
                they are read from an existing pot file.
                """).strip(),
            dest='cached_pot', action='store_const', const=True, default=False)
        parser.add_argument('-n', '--dry-run',
            help=textwrap.dedent("""
                Do not write any files, just show what would be done
                """).strip(),
            dest='write', action='store_const', const=False, default=True)
        parser.add_argument('-q', '--quiet',
            help=textwrap.dedent("""
                Don't print out progress messages.
                """).strip(),
            dest='printer', action='store_const',
            const=lambda *a, **ka: None, default=print)

        args = parser.parse_args(argv[1:])

        action = args.action
        if action == 'help':
            parser.print_help()
            exit(1)
        elif action == 'extract':
            pot = self.extract(args)
            if args.write:
                args.printer('Saving pot file %s' % self.pot_name)
                pot.save(self.pot_name)
        elif action == 'update':
            self.save_pos(self.merge(args), args)
        elif action == 'strip':
            self.save_pos(self.strip(args), args)
        elif action == 'stats':
            args.printer = lambda *a, **ka: None
            self.print_stats(self.merge(args), args)
        else:
            parser.error('Unknown action')

