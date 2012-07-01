# Encoding: UTF-8

"""Czech conjugation
"""

from __future__ import print_function, unicode_literals

import six

from forrin.template import Formatter, BaseWord, parse_bool


class Word(BaseWord):
    @classmethod
    def guess_type(cls, word, **props):
        if word.endswith('í'):
            return SoftAdjective
        elif word.endswith('ý'):
            return HardAdjective
        else:
            return Word


class Adjective(Word):
    def __init__(self, word):
        self.root = word

    _interesting_categories = 'gender number case'.split()

    gender = 'm'
    case = 1
    number = 'sg'

    def inflect(self, **props):
        gender = props.get('gender', self.gender)
        case = int(props.get('case', self.case))
        number = props.get('number', self.number)
        case_no = (case - 1) + (7 if (number == 'pl') else 0)
        if gender == 'm':
            if parse_bool(props.get('animate', True)):
                return self.root + self.endings_ma[case_no]
            else:
                return self.root + self.endings_mi[case_no]
        elif gender == 'f':
            return self.root + self.endings_f[case_no]
        else:
            return self.root + self.endings_n[case_no]


class SoftAdjective(Adjective):
    def __init__(self, word):
        if word.endswith('í'):
            self.root = word[:-1]
        else:
            self.root = word

    endings_ma = 'í,ího,ímu,ího,í,ím,ím,í,ích,ím,í,í,ích,ími'.split(',')
    endings_mi = 'í,ího,ímu,í,í,ím,ím,í,ích,ím,í,í,ích,ími'.split(',')
    endings_f = 'í,í,í,í,í,í,í,í,ích,ím,í,í,ích,ími'.split(',')
    endings_n = 'í,ího,ímu,í,í,ím,ím,í,ích,ím,í,í,ích,ími'.split(',')


class HardAdjective(Adjective):
    def __init__(self, word):
        if any(word.endswith(x) for x in 'ýáé'):
            self.root = word[:-1]
        else:
            self.root = word

    endings_ma = 'ý,ého,ému,ého,ý,ém,ým,í,ých,ým,é,í,ých,ými'.split(',')
    endings_mi = 'ý,ého,ému,ý,ý,ém,ým,é,ých,ým,é,é,ých,ými'.split(',')
    endings_f = 'á,é,é,ou,á,é,ou,é,ých,ým,é,é,ých,ými'.split(',')
    endings_n = 'é,ého,ému,é,é,ém,ým,á,ých,ým,á,á,ých,ými'.split(',')

formatter = Formatter('cs', Word)


class Template(six.text_type):
    def format(self, *args, **kwargs):
        return formatter.format(self, *args, **kwargs)
