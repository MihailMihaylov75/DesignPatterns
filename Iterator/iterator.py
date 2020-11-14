__author__ = 'Mihail Mihaylov'

from unittest import *


class Node:
    def __init__(self, value, left=None, right=None):
        self.right = right
        self.left = left
        self.value = value

        self.parent = None

        if left:
            self.left.parent = self
        if right:
            self.right.parent = self

    def traverse_preorder(self):
        yield self.value
        if self.left:
            yield from self.left.traverse_preorder()
        if self.right:
            yield from self.right.traverse_preorder()


class Evaluate(TestCase):
    def test_exercise(self):
        node = Node('a',
                    Node('b',
                         Node('c'),
                         Node('d')),
                    Node('e'))
        self.assertEqual(
            'abcde',
            ''.join([x for x in node.traverse_preorder()])
        )
