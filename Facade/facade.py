__author__ = 'Mihail Mihaylov'
from random import randint


class Buffer:
    def __init__(self, width=30, height=20):
        self.width = width
        self.height = height
        self.buffer = [' '] * (width * height)

    def __getitem__(self, item):
        return self.buffer.__getitem__(item)

    def write(self, text):
        self.buffer += text


class Viewport:
    def __init__(self, buffer=Buffer()):
        self.buffer = buffer
        self.offset = 0

    def get_char_at(self, index):
        return self.buffer[self.offset + index]

    def append(self, text):
        self.buffer += text


class Console:
    def __init__(self):
        b = Buffer()
        self.current_viewport = Viewport(b)
        self.buffers = [b]
        self.viewports = [self.current_viewport]

    # high-level
    def write(self, text):
        self.current_viewport.buffer.write(text)

    # low-level
    def get_char_at(self, index):
        return self.current_viewport.get_char_at(index)


class Generator:
    def generate(self, count):
        return [randint(1, 9) for x in range(count)]


class Splitter:
    def split(self, array):
        result = []

        row_count = len(array)
        col_count = len(array[0])

        for r in range(row_count):
            the_row = []
            for c in range(col_count):
                the_row.append(array[r][c])
            result.append(the_row)

        for c in range(col_count):
            the_col = []
            for r in range(row_count):
                the_col.append(array[r][c])
            result.append(the_col)

        diag1 = []
        diag2 = []

        for c in range(col_count):
            for r in range(row_count):
                if c == r:
                    diag1.append(array[r][c])
                r2 = row_count - r - 1
                if c == r2:
                    diag2.append(array[r][c])

        result.append(diag1)
        result.append(diag2)

        return result


class Verifier:
    @staticmethod
    def verify(self, arrays):
        first = sum(arrays[0])

        for i in range(1, len(arrays)):
            if sum(arrays[i]) != first:
                return False

        return True


class MagicSquareGenerator:
    @staticmethod
    def generate(self, size):
        g = Generator()
        s = Splitter()
        v = Verifier()

        while True:
            square = []
            for x in range(size):
                square.append(g.generate(size))

            if v.verify(s.split(square)):
                break

        return square


if __name__ == '__main__':
    c = Console()
    c.write('hello')
    ch = c.get_char_at(0)
