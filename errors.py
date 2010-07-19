# coding=utf8

class TooMuchWishesError(Exception):
    def __str__(self):
        return 'Слишком много обещаний.'

class TooMuchPromisesError(Exception):
    def __str__(self):
        return 'Слишком много обещаний.'