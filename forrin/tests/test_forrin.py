# Encoding: UTF-8

from __future__ import unicode_literals

import gettext

import pytest
import six
from six import StringIO

from forrin import extract
from forrin import translator
import forrin.en
import forrin.cs


class TestTranslations(object):
    """gettext-like Translations class. Reports what gets called instead of
    actually translating"""
    def ugettext(self, message):
        return '|ugettext(%s)' % message
    gettext = ugettext

    def ungettext(self, message, plural, n):
        return '|ungettext(%s, %s, %s)' % (message, plural, n)
    ngettext = ungettext


class ConstTranslations(object):
    """gettext-like Translations class. Always returns the same string"""
    def __init__(self, string):
        self._string = string

    def ugettext(self, message):
        return self._string
    gettext = ugettext

    def ungettext(self, message, plural, n):
        return self._string
    ngettext = ungettext

translation_inputs = [
        (('text',), dict()),
        (('one', 'two'), dict(n=1)),
        (('one', 'two'), dict(n=3)),
        (('a|b|c',), dict()),
        (('a|b|c', 'd|e|f'), dict(n=1)),
        (('a|b|c', 'd|e|f'), dict(n=3)),
        (('text',), dict(context='ctx')),
        (('one', 'two'), dict(n=1, context='ctx')),
        (('one', 'two'), dict(n=3, context='ctx')),
        (('a|b|c',), dict(context='ctx')),
        (('a|b|c', 'd|e|f'), dict(n=1, context='ctx')),
        (('a|b|c', 'd|e|f'), dict(n=3, context='ctx')),
    ]

outputs_test = [
        '|ugettext(text)',
        '|ungettext(one, two, 1)',
        '|ungettext(one, two, 3)',
        '|ugettext(a|b|c)',
        '|ungettext(a|b|c, d|e|f, 1)',
        '|ungettext(a|b|c, d|e|f, 3)',
        'ugettext(ctx|text)',
        'ungettext(ctx|one, ctx|two, 1)',
        'ungettext(ctx|one, ctx|two, 3)',
        'ugettext(ctx|a|b|c)',
        'ungettext(ctx|a|b|c, ctx|d|e|f, 1)',
        'ungettext(ctx|a|b|c, ctx|d|e|f, 3)',
    ]


def test_translation_calls():
    _ = translator.BaseTranslator(translations=TestTranslations())
    for (args, kwargs), out in zip(translation_inputs, outputs_test):
        print(args, kwargs, out)
        assert _(*args, **kwargs) == out


def test_translatable_string():
    _ = translator.BaseTranslator(translations=TestTranslations())
    for (args, kwargs), out in zip(translation_inputs, outputs_test):
        print(args, kwargs, out)
        assert _(translator.TranslatableString(*args, **kwargs)) == out


def test_null_translation():
    _ = translator.BaseTranslator(translations=gettext.NullTranslations())
    outputs = [
            'text',
            'one',
            'two',
            'a|b|c',
            'a|b|c',
            'd|e|f',
            'text',
            'one',
            'two',
            'a|b|c',
            'a|b|c',
            'd|e|f',
        ]
    for (args, kwargs), out in zip(translation_inputs, outputs):
        print(args, kwargs, out)
        assert _(*args, **kwargs) == out


def test_const_translation():
    _ = translator.BaseTranslator(translations=ConstTranslations(
        'pre|in|post'))
    outputs = [
            'pre|in|post',
            'pre|in|post',
            'pre|in|post',
            'pre|in|post',
            'pre|in|post',
            'pre|in|post',
            'in|post',
            'in|post',
            'in|post',
            'in|post',
            'in|post',
            'in|post',
        ]
    for (args, kwargs), out in zip(translation_inputs, outputs):
        print(args, kwargs, out)
        assert _(*args, **kwargs) == out


# Extraction tests #

def check_generator(function, args, output):
    actual_output = function(*args)
    actual_output = list(actual_output)
    output = list(output)
    print('Output is:', actual_output)
    print('Should be:', output)
    assert output == actual_output


def test_extraction_babel_python():
    func = extract.babel_python
    input = """if True:
        print(_('d'))
        print(_('d', n=6, plural='f'))
        print(_('d', context='some_ctx'))
        print(_('d', n=6, plural='f', context='some_ctx'))

        print(_('%s') % f)
        print(_('{s}').format(s=1))
    """.strip()
    output = [
            (2, 'ugettext', 'd', []),
            (3, 'ungettext', ('d', 'f'), []),
            (4, 'ugettext', 'some_ctx|d', []),
            (5, 'ungettext', ('some_ctx|d', 'f'), []),
            (7, 'ugettext', '%s', []),
            (8, 'ugettext', '{s}', []),
        ]
    args = (StringIO(input), ['_'], [], {})
    check_generator(func, args, output)


def test_extraction_babel_mako():
    try:
        import mako
    except ImportError:
        pytest.skip("Mako not installed")
    func = extract.babel_mako
    input = """<html>
        _('d') <!-- not caught -->
        ${_('text', context='abc')}
        % for char in _('horse', 'horses', n=1):
            <b>${char}</b>
        % endfor
        </html>
    """
    print(input)
    output = [
            (3, 'ugettext', 'abc|text', []),
            (4, 'ungettext', ('horse', 'horses'), []),
        ]
    args = (StringIO(input), ['_'], [], {})
    check_generator(func, args, output)


# Translation tests #

def test_en():
    for templ, args, kwargs, out in [
            ('{a:*w} {w}', [], dict(a='a', w='apple'), 'an apple'),
            ('{a:*0} {0}', ['apple'], dict(a='a'), 'an apple'),
            ('{1:*0} {0}', ['apple', 'a'], dict(), 'an apple'),
            ('{=a:*0} {0}', ['apple'], dict(), 'an apple'),
            ('{=a:*0} {0}', ['pear'], dict(), 'a pear'),
        ]:
        def test():
            assert forrin.en.Template(templ).format(*args, **kwargs) == out
        test.description = templ
        yield test


def test_cs():
    for templ, args, kwargs, out in [
            ('{0}', ['mladý'], dict(), 'mladý'),
            ('{0:case=2}', ['mladý'], dict(), 'mladého'),
            ('{0:case=3}', ['mladý'], dict(), 'mladému'),
            ('{0:number=pl}', ['mladý'], dict(), 'mladí'),
            ('{0:gender=f}', ['mladý'], dict(), 'mladá'),
            ('{0}', ['jarní'], dict(), 'jarní'),
            ('{0:case=2}', ['jarní'], dict(), 'jarního'),
            ('{0:gender=n,case=2,number=pl}', ['jarní'], dict(), 'jarních'),
            ('{0:case=2}', ['jarní a mladý'], dict(), 'jarního a mladého'),
        ]:
        def test():
            assert forrin.cs.Template(templ).format(*args, **kwargs) == out
        test.description = templ
        yield test
