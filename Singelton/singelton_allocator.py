__author__ = 'Mihail Mihaylov'


class Database:
    initialized = False

    def __init__(self):
        pass

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Database, cls).__new__(cls, *args, **kwargs)

        return cls._instance
