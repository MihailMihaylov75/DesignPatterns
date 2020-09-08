__author__ = 'Mihail Mihaylov'

import random
import string


class User:
    def __init__(self, name):
        self.name = name


class User2:
    strings = []

    def __init__(self, full_name):
        def get_or_add(s):
            if s in self.strings:
                return self.strings.index(s)
            else:
                self.strings.append(s)
                return len(self.strings)-1
        self.names = [get_or_add(x) for x in full_name.split(' ')]

    def __str__(self):
        return ' '.join([self.strings[x] for x in self.names])


def random_string():
    chars = string.ascii_lowercase
    return ''.join([random.choice(chars) for _ in range(8)])


class FormattedText:
    def __init__(self, plain_text):
        self.plain_text = plain_text
        self.caps = [False] * len(plain_text)

    def capitalize(self, start, end):
        for i in range(start, end):
            self.caps[i] = True

    def __str__(self):
        result = []
        for i in range(len(self.plain_text)):
            c = self.plain_text[i]
            result.append(c.upper() if self.caps[i] else c)
        return ''.join(result)


class BetterFormattedText:
    def __init__(self, plain_text):
        self.plain_text = plain_text
        self.formatting = []

    class TextRange:
        def __init__(self, start, end, capitalize=False, bold=False, italic=False):
            self.end = end
            self.bold = bold
            self.capitalize = capitalize
            self.italic = italic
            self.start = start

        def covers(self, position):
            return self.start <= position <= self.end

    def get_range(self, start, end):
        range = self.TextRange(start, end)
        self.formatting.append(range)
        return range

    def __str__(self):
        result = []
        for i in range(len(self.plain_text)):
            c = self.plain_text[i]
            for r in self.formatting:
                if r.covers(i) and r.capitalize:
                    c = c.upper()
            result.append(c)
        return ''.join(result)


if __name__ == '__main__':
    users = []

    first_names = [random_string() for x in range(100)]
    last_names = [random_string() for x in range(100)]

    for first in first_names:
        for last in last_names:
            users.append(User(f'{first} {last}'))

    u2 = User2('Jim Jones')
    u3 = User2('Frank Jones')
    print(u2.names)
    print(u3.names)
    print(User2.strings)

    users2 = []

    for first in first_names:
        for last in last_names:
            users2.append(User2(f'{first} {last}'))

    ft = FormattedText('This is a brave new world')
    ft.capitalize(10, 15)
    print(ft)

    bft = BetterFormattedText('This is a brave new world')
    bft.get_range(16, 19).capitalize = True
    print(bft)
