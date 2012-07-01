import sys

from setuptools import setup, find_packages

setup_args = dict(
    name='forrin',
    version='0.1-alpha',
    packages=find_packages(),

    description="""Localization helpers""",
    author='Petr Viktorin',
    author_email='encukou@gmail.com',
    install_requires=[
            'polib>=1.0',
            'six',
        ],

    entry_points = {
            'babel.extractors': [
                    'forrin = forrin.extract:babel_python',
                    'forrin-mako = forrin.extract:babel_mako',
                ]
        },
)

setup(**setup_args)
