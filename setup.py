import sys

from setuptools import setup, find_packages

setup_args = dict(
    name='forrin',
    version='0.1.1-alpha',
    packages=find_packages(),

    url='https://github.com/encukou/forrin',

    description="""Localization helpers""",
    author='Petr Viktorin',
    author_email='encukou@gmail.com',
    install_requires=[
            'polib>=1.0',
            'six',
        ],

    entry_points={
            'babel.extractors': [
                    'forrin = forrin.extract:babel_python',
                    'forrin-mako = forrin.extract:babel_mako',
                ],
        },
)

if sys.version_info < (2, 7):
    setup_args.install_requires.append('argparse')

setup(**setup_args)
