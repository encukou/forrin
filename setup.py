
from setuptools import setup, find_packages

setup(
    name='forrin',
    version='0.1-alpha',
    packages=find_packages(),

    description=u"""Localization helpers""",
    author='Petr Viktorin',
    author_email='encukou@gmail.com',
    install_requires=[
            'polib>=1.0',
        ],

    entry_points = {
            'babel.extractors': [
                    'forrin = forrin.extract:babel_python',
                    'forrin-mako = forrin.extract:babel_mako',
                ]
        },
)
