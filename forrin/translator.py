# Encoding: UTF-8

import os.path
import warnings

import gettext
import pkg_resources

import forrin.template

class TranslatableString(object):
    """Encapsulates a string and its translation information.

    Aliased to _, this class can serve to mark strings for later translation,
    in cases when the Translator is not available yet, or when a single string
    is to be used with multiple translators.
    For this purpose, TranslatableString is exported as forrin.translator._

    Call a translator on a TranslatableString s you would on a regular string,
    but without any extra arguments.
    """
    def __init__(self, message, plural=None, n=None, context=None, comment=None):
        # Converting things to unicode strings makes this fail on instantiation
        # if they're not convertible (e.g. non-ASCII byte strings), rather than
        # waiting until the string is used.
        self.message = unicode(message)
        self.args = (
                None if plural is None else unicode(plural),
                None if n is None else int(n),
                None if context is None else unicode(context),
                None if comment is None else unicode(comment),
            )

    def __str__(self):
        return str(self.message)

    def __unicode__(self):
        return unicode(self.message)

    def __repr__(self):
        return '<TranslatableString %r at 0x%08x>' % (self.message, id(self))

_ = TranslatableString

class BaseTranslator(object):
    """The translator. A callable object indended to be subclassed and used as _.

    Use
    ---

    Instead of using gettext's ugettext and ungettext, this object is all
    that's needed, thanks to Python's keyword arguments:
    _('text') => "text"
    (_('%s house', '%s houses', n=num) % num) => "1 house" or "2 houses", etc.
    _(u'file', context='verb') => u"file", but will be translated as
        “to file something” as opposed to “named chunk of data” in languages
        where the distinction matters

    Instantiation
    -------------

    Each module is expected to subclass BaseTranslator and set some of
    the following class attributtes:
    - package: the package in which to look for i18n. If not set explicitly,
        the class's __module__ is used.
    - dir: the locale directory within `package`. Defaults to "i18n".
    - domain: the gettext domain used. By default, same as the `package`

    Constructor parameters are 
    - lang: the language identifier
    - translations: override the underlying gettext translations class
        entirely. (Used mainly in testing.)
    - directory: can be used to override the po-file directory. Divined from
        the package & dir class attributes if missing.

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

    Unicode (u*gettext) is used everywhere.
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
        i18n_dir = self.i18n_directory
        if default:
            yield default
        for root, dirs, files in os.walk(i18n_dir):
            components = root.split(os.sep)
            if components[-1] == 'LC_MESSAGES':
                if self.package + '.po' in files:
                    lang = components[-2]
                    if lang != default:
                        yield components[-2]

    def __init__(self,
            languages=None,
            translations=None,
            directory=None,
            package=None,
            context=None,
        ):
        self.context = context
        self.package = package or getattr(self, 'package', self.__module__)
        if translations is None:
            if languages is None:
                self.translation = gettext.NullTranslations()
                self.language = None
            else:
                if directory is None:
                    directory = self.i18n_directory
                gettext.bindtextdomain(self.package, directory)
                try:
                    self.translation = gettext.translation(
                            domain=getattr(self, 'domain', self.package),
                            localedir=directory,
                            languages=languages,
                        )
                    self.language = languages[0]
                except IOError:
                    self.translation = gettext.NullTranslations()
                    self.language = None
                    warnings.warn(RuntimeWarning(
                            '%s translations for %s not found in %s'
                                % (languages, self.package, directory)
                        ))
        else:
            self.translation = translations
            self.language = None

    def __call__(self, message, plural=None, n=None, context=None, comment=None):
        if isinstance(message, TranslatableString):
            assert plural == n == context == comment == None, (
                    "Translatable strings don't need extra information"
                )
            return self(message.message, *message.args)
        if context:
            prefix = context + u'|'
        else:
            prefix = u''
        if n is None:
            translated = self.translation.ugettext(prefix + message)
        else:
            translated = self.translation.ungettext(
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
            except (ImportError, AttributeError), e:
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
