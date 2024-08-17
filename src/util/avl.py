from __future__ import annotations
from typing import Any, TypeVar, Generic
T = TypeVar('T')

def height(x: AVLTree.Node | None):
    return x.height if x is not None else 0

def update_height(x: AVLTree.Node):
    x.height = 1 + max(height(x.left), height(x.right))
    x.num_element = 1 + (x.left.num_element if x.left is not None else 0) + (x.right.num_element if x.right is not None else 0)

def weight(x: AVLTree.Node | None):
    return height(x.left) - height(x.right) if x is not None else 0

def fix_left_left(node):
    y = node.left
    node.left = node.left.right
    y.right = node
    update_height(y.right)
    update_height(y)
    return y

def fix_right_right(node):
    y = node.right
    node.right = node.right.left
    y.left = node
    update_height(y.left)
    update_height(y)
    return y

def fix_left_right(node):
    x = node.left.right
    y = node.left
    node.left.right = x.left
    node.left = x.right
    x.left = y
    x.right = node
    update_height(x.left)
    update_height(x.right)
    update_height(x)
    return x

def fix_right_left(node):
    x = node.right.left
    y = node.right
    node.right.left = x.right
    node.right = x.left
    x.right = y
    x.left = node
    update_height(x.left)
    update_height(x.right)
    update_height(x)
    return x

def insert(node, key):
    if node is None:
        return AVLTree.Node(key)

    if key < node.key:
        node.left = insert(node.left, key)
    elif key > node.key:
        node.right = insert(node.right, key)
    else:
        return node

    update_height(node)
    w = weight(node)
    if w > 1 and key < node.left.key:
        return fix_left_left(node)

    if w < -1 and key > node.right.key:
        return fix_right_right(node)

    if w > 1 and key > node.left.key:
        return fix_left_right(node)

    if w < -1 and key < node.right.key:
        return fix_right_left(node)
    return node

def delete(node, key):
    if node is None:
        return node

    if key < node.key:
        node.left = delete(node.left, key)
    elif key > node.key:
        node.right = delete(node.right, key)
    elif node.left is None and node.right is None:
        return None
    elif node.left is None:
        node = node.right
    elif node.right is None:
        node = node.left
    else:
        minkey = node.right.min_key()
        node.key = minkey
        node.right = delete(node.right, minkey)

    if node is None:
        return node

    update_height(node)
    w = weight(node)

    if w > 1 and weight(node.left) >= 0:
        return fix_left_left(node)

    if w > 1 and weight(node.left) < 0:
        return fix_left_right(node)

    if w < -1 and weight(node.right) <= 0:
        return fix_right_right(node)

    if w < -1 and weight(node.right) > 0:
        return fix_right_left(node)

    return node

class AVLTree(Generic[T]):
    class Node:
        def __init__(self, key: T):
            self.key = key
            self.left: AVLTree.Node | None = None
            self.right: AVLTree.Node | None = None
            self.height = 1
            self.num_element = 1

        def min_key(self):
            x = self
            while x.left is not None:
                x = x.left
            return x.key

        def flatten(self) -> list[T]:
            elements = []
            if self.left is not None:
                elements += self.left.flatten()
            elements.append(self.key)
            if self.right is not None:
                elements += self.right.flatten()
            return elements

    def __init__(self):
        self.key = None

    def insert(self, key: T):
        self.key = insert(self.key, key)

    def delete(self, key: T):
        self.key = delete(self.key, key)

    def flatten(self) -> list[T]:
        if self.key is None:
            return []
        return self.key.flatten()

    def __contains__(self, x: T):
        def contains(node: AVLTree.Node | None):
            if node is None:
                return False
            if x < node.key:
                return contains(node.left)
            elif x > node.key:
                return contains(node.right)
            return True
        return contains(self.key)

    def empty(self):
        return self.key is None

    def __len__(self):
        return self.key.num_element if self.key is not None else 0

    def __getitem__(self, idx: int) -> T:
        def num_element(node: AVLTree.Node | None):
            return node.num_element if node is not None else 0
        def getitem(node: AVLTree.Node | None, idx: int):
            if node is None:
                raise IndexError
            left_elem = num_element(node.left)
            if idx < left_elem:
                return getitem(node.left, idx)
            if idx == left_elem:
                return node.key
            return getitem(node.right, idx - left_elem - 1)
        if idx < 0 or idx >= len(self):
            raise IndexError
        return getitem(self.key, idx)
