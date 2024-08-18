import pytest
import random
from src.util.avl import AVLTree
from tqdm.auto import trange

def height(node):
    if node is None:
        return 0
    return 1 + max(height(node.left), height(node.right))

def check_node(node):
    if node is None:
        return
    assert node.num_element == len(node.flatten())
    assert node.height == height(node)
    assert abs(height(node.left) - height(node.right)) <= 1
    check_node(node.left)
    check_node(node.right)

def check_tree(tree):
    check_node(tree.key)

def test_avl():
    for _ in range(1000):
        seq = []
        tree = AVLTree()
        for _ in range(random.randint(100, 1000)):
            action = random.choice(["insert", "delete", "get"])
            if not tree.empty() and action == "delete":
                x = random.choice(tree.flatten())
                tree.delete(x)
                seq.append(f"delete({x})")

            if action == "insert":
                x = random.randint(0, 100)
                tree.insert(x)
                seq.append(f"insert({x})")

            if not tree.empty() and action == "get":
                x = random.randint(0, len(tree) - 1)
                assert tree[x] == tree.flatten()[x]
                seq.append(f"get({x})")
            check_tree(tree)
        assert tree.flatten() == sorted(tree.flatten()), seq
