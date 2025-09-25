__author__ = 'Mihail Mihaylov'


class Bitmap:
    def __init__(self, filename):
        self.filename = filename
        print(f'Loading image from {filename}')

    def draw(self):
        print(f'Drawing image {self.filename}')


class LazyBitmap:
    def __init__(self, filename):
        self.filename = filename
        self.bitmap = None

    def draw(self):
        if not self.bitmap:
            self.bitmap = Bitmap(self.filename)
        self.bitmap.draw()


def draw_image(image):
    print('About to draw image')
    image.draw()
    print('Done drawing image')


class Person:
    def __init__(self, age):
        self.age = age

    def drink(self):
        return 'drinking'

    def drive(self):
        return 'driving'

    def drink_and_drive(self):
        return 'driving while drunk'


class ResponsiblePerson:
    def __init__(self, person):
        self.person = person

    @property
    def age(self):
        return self.person.age

    @age.setter
    def age(self, value):
        self.person.age = value

    def drink(self):
        if self.age < 18:
            return 'too young'
        else:
            return self.person.drink()

    def drive(self):
        if self.age < 16:
            return 'too young'
        else:
            return self.person.drive()

    def drink_and_drive(self):
        return 'dead'


if __name__ == '__main__':
    bmp = LazyBitmap('facepalm.jpg')  # Bitmap
    draw_image(bmp)
