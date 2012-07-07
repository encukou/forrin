# Encoding: UTF-8
from __future__ import print_function, unicode_literals

import sys
import os.path
import warnings
import operator
from collections import namedtuple

import six
import pkg_resources

import forrin.template
import forrin.backend


_Base = namedtuple('_base', 'message plural n context comment')


class TranslatableString(_Base):
    """Encapsulates a string and its translation information.

    Aliased to _, this class can serve to mark strings for later translation,
    in cases when the Translator is not available yet, or when a single string
    is to be used with multiple translators.
    For this purpose, TranslatableString is exported as forrin.translator._

    Call a translator on a TranslatableString s you would on a regular string,
    but without any extra arguments.
    """
    def __new__(cls, message, plural=None, n=None, context=None, comment=None):
        # Converting things to unicode strings makes this fail on instantiation
        # if they're not convertible (e.g. non-ASCII byte strings), rather than
        # waiting until the string is used.
        return _Base.__new__(cls,
                six.text_type(message),
                None if plural is None else six.text_type(plural),
                None if n is None else int(n),
                None if context is None else six.text_type(context),
                None if comment is None else six.text_type(comment),
            )

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return unicode(self.message)

    def __repr__(self):
        return '<TranslatableString %r at 0x%08x>' % (self.message, id(self))

_ = TranslatableString


class BaseTranslator(object):
    """A callable object indended to be subclassed and used as _.

    Use
    ---

    thanks to Python's keyword arguments, this object is all that's needed to
    mark translatable strings:
    _('text') => "text"
    (_('%s house', '%s houses', n=num) % num) => "1 house" or "2 houses", etc.
    _(u'file', context='verb') => u"file", but can be translated as
        “to file something” as opposed to “named chunk of data” in languages
        where the distinction matters

    Instantiation
    -------------

    Each module is expected to subclass BaseTranslator and set some of
    the following class attributtes:
    - package: the package in which to look for i18n. If not set explicitly,
        the class's __module__ is used.
    - dir: the locale directory within `package`. Defaults to "i18n".
    - domain: the domain (aka project identifier) used. By default, same as
        the `package`

    Constructor parameters are
    - languages: a list of language identifiers; first is the one we want to
        use, followed fallbacks in order of preference
    - translations: override the underlying gettext translations class
        entirely. The given object must support `gettext` and `ngettext`
        methods, with API defined by the Python gettext module. (For Python 2,
        these should use Unicode, i.e. gettext's ugettext & ungettext.)
    - directory: can be used to override the po-file directory. Divined from
        the package & dir class attributes if missing.
    - package: override the class-level package attribute

    Notes
    -----

    Translations with contexts are marked with '|' in translation files, for
    example _(u'file', context='verb') looks for the text "verb|file"
    in the .mo file. This is apparently how it's done in GTK and probably other
    gettext-using projects, so there might be tools that expect it.
    The prefix is stripped if it survives the translation (that is, context was
    used and the '|' is still there after translation); care must be taken in
    the unlikely case that the translation contains '|' that should be there.

    Forrin's message extractors must be used to extract messages, naturally.

    Unicode is used everywhere.
    """
    dir = 'i18n'

    @property
    def i18n_directory(self):
        """Return the directory where translations are stored"""
        return pkg_resources.resource_filename(
                self.package,
                self.dir
            )

    def available_languages(self, default='en'):
        """Yield the available languages (not including the default)

        default: The language used in code, for untranslated messages. Set to
            None to disable a default.
        """
        yielded = set()
        i18n_dir = self.i18n_directory
        if default:
            yield default
            yielded.add(default)
        for filename in os.listdir(i18n_dir):
            # PO files directly in i18n directory
            if filename.endswith('.po'):
                lang = filename[:-3]
                if lang not in yielded:
                    yield lang
                    yielded.add(lang)

    def __init__(self,
            languages=None,
            translations=None,
            directory=None,
            package=None,
        ):
        self.package = package or getattr(self, 'package', self.__module__)
        self.domain = getattr(self, 'domain', self.package)
        if translations is None:
            if languages is None:
                self.translation = NullTranslations()
                self.language = None
            else:
                if directory is None:
                    directory = self.i18n_directory
                self.translation = forrin.backend.SQLiteBackend(
                    self.package, directory, languages)
                self.language = languages[0]
        else:
            self.translation = translations
            self.language = None

    def __call__(self, message, plural=None, n=None,
            context=None, comment=None):
        if isinstance(message, TranslatableString):
            assert plural is n is context is comment is None, (
                    "Translatable strings don't need extra information"
                )
            return self(*message)
        if context:
            prefix = context + '|'
        else:
            prefix = ''
        if n is None:
            translated = self.translation.gettext(prefix + message)
        else:
            translated = self.translation.ngettext(
                    prefix + message,
                    prefix + plural,
                    n
                )
        if context:
            prefix, sep, translated = translated.partition('|')
            if not sep:
                translated = prefix
        return handle_template(translated, self.language)


def handle_template(message, language='en'):
    if message and message[0] == '@':
        if language:
            try:
                mod = __import__('forrin.' + language, fromlist='Template')
                Template = mod.Template
            except (ImportError, AttributeError) as e:
                Template = forrin.template.Template
        else:
            Template = forrin.template.Template
        return Template(message[1:])
    return message


class NullTranslator(object):
    """Looks like a Translator, quacks like a Translator, but doesn't actually
    translate
    """
    def __init__(*stuff, **more_stuff):
        pass

    def __call__(self, message, *stuff, **more_stuff):
        return handle_template(message)

class NullTranslations(object):
    def gettext(self, msgid):
        return msgid

    def ngettext(self, singular, plural, n):
        if n == 1:
            return singular
        else:
            return plural
