from __future__ import print_function, unicode_literals

import ast
import itertools
import functools
from six import StringIO

import polib

_args = "message plural n context comment".split()

def babel_wrapper(func):
    @functools.wraps(func)
    def wrapped(fileobj, keywords, comment_tags, options):
        try:
            filename = fileobj.filename
        except AttributeError:
            filename = '<unknown>'
        for message in func(filename, fileobj, keywords):
            lineno = message.occurrences[0][1]
            if message.msgid_plural:
                funcname = 'ungettext'
                msgid = (message.msgid, message.msgid_plural)
            else:
                funcname = 'ugettext'
                msgid = message.msgid
            comments = getattr(message, 'tcomments', [])
            yield lineno, funcname, msgid, comments
    return wrapped

def extract_python(filename, fileobj=None, keywords=['_'], **kwargs):
    if fileobj is None:
        fileobj = open(filename)
    return extract_from_string(fileobj.read(), filename, keywords=['_'], **kwargs)

babel_python = babel_wrapper(extract_python)

def extract_from_string(string, filename, keywords=['_'], **kwargs):
    tree = compile(
            string,
            filename=filename,
            mode='exec',
            flags=ast.PyCF_ONLY_AST,
            dont_inherit=True,
        )
    return from_ast(tree, filename, keywords)

def from_ast(node, filename, keywords, flags=[]):
    if isinstance(node, ast.Call):
        funcname = get_funcname(node.func)
        if funcname in keywords:
            params = {}
            for name, param in itertools.chain(
                    zip(_args, node.args),
                    ((k.arg, k.value) for k in node.keywords),
                ):
                if isinstance(param, ast.Str):
                    params[name] = param
                else:
                    # not a literal string: we don't care about it,
                    # but still want to know if it's there
                    params[name] = None
            message = getstring(params.get('message'))
            context = getstring(params.get('context'))
            comment = getstring(params.get('comment'))
            if message:
                if context:
                    message = context + '|' + message
                message = polib.POEntry(
                        msgid=message,
                        occurrences=[(filename, node.lineno)],
                    )
                if 'plural' in params:
                    message.msgid_plural = getstring(params.get('plural'))
                if comment:
                    message.comment = comment
                message.flags = flags
                yield message
    child_flags = []
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        child_flags.append('python-format')
    if isinstance(node, ast.Attribute) and node.attr == 'format':
        child_flags.append('python3-format')
    for child in ast.iter_child_nodes(node):
        for result in from_ast(child, filename, keywords, child_flags):
            yield result

def get_funcname(node):
    if isinstance(node, ast.Name):
        # gettext(...)
        return node.id
    elif isinstance(node, ast.Attribute):
        # someobject.gettext(...)
        # We only care about the attribute name
        return node.attr
    else:
        # something like (lst[0])(...)
        return None

def getstring(maybenode):
    if maybenode is None:
        return None
    else:
        return maybenode.s

try:
    from mako.template import Template
except ImportError:
    pass
else:
    def extract_mako(filename, fileobj=None, keywords=['_'], **kwargs):
        if fileobj is None:
            fileobj = open(filename)
        template = Template(
                fileobj.read(),
                input_encoding='utf-8',
                output_encoding='utf-8',
            )
        # We need line numbers that correspond to the mako file.
        # Mako does this by including "# SOURCE LINE xxx" comments in the file;
        # use these to build a line number map
        linenomap = [0]
        lineno = 0
        for line in template.code.splitlines():
            emptystring, sep, number = line.strip().partition("# SOURCE LINE ")
            if not emptystring and sep:
                try:
                    lineno = int(number)
                except ValueError:
                    pass
            linenomap.append(lineno)
        # Finally, do the actual extracting
        fileobj = StringIO(template.code)
        messages = extract_python(filename, fileobj, keywords, **kwargs)
        for message in messages:
            message.occurrences = [(o[0], linenomap[o[1]]) for o in message.occurrences]
            yield message

    babel_mako = babel_wrapper(extract_mako)
