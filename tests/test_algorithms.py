"""Тестове за структурите от данни и алгоритмите."""

import random
import unittest

from task_manager.searching import binary_search, linear_search, linear_search_first
from task_manager.sorting import merge_sort, quick_sort
from task_manager.structures import Queue, Stack


class StackTests(unittest.TestCase):
    def test_lifo_order(self):
        s = Stack()
        for x in (1, 2, 3):
            s.push(x)
        self.assertEqual(len(s), 3)
        self.assertEqual(s.peek(), 3)
        self.assertEqual([s.pop(), s.pop(), s.pop()], [3, 2, 1])
        self.assertTrue(s.is_empty())

    def test_empty_errors(self):
        with self.assertRaises(IndexError):
            Stack().pop()
        with self.assertRaises(IndexError):
            Stack().peek()

    def test_iteration_and_to_list(self):
        s = Stack([1, 2, 3])
        self.assertEqual(list(s), [3, 2, 1])      # от върха
        self.assertEqual(s.to_list(), [1, 2, 3])  # от дъното

    def test_remove_if_keeps_order(self):
        s = Stack([1, 2, 3, 4, 5])
        removed = s.remove_if(lambda x: x % 2 == 0)
        self.assertEqual(removed, [2, 4])
        self.assertEqual(s.to_list(), [1, 3, 5])
        self.assertEqual(len(s), 3)


class QueueTests(unittest.TestCase):
    def test_fifo_order(self):
        q = Queue()
        for x in "abc":
            q.enqueue(x)
        self.assertEqual(q.peek(), "a")
        self.assertEqual([q.dequeue(), q.dequeue(), q.dequeue()], ["a", "b", "c"])
        self.assertTrue(q.is_empty())

    def test_empty_errors(self):
        with self.assertRaises(IndexError):
            Queue().dequeue()
        with self.assertRaises(IndexError):
            Queue().peek()

    def test_reuse_after_empty(self):
        q = Queue([1])
        q.dequeue()
        q.enqueue(2)
        q.enqueue(3)
        self.assertEqual(q.to_list(), [2, 3])

    def test_remove_if_head_middle_tail(self):
        q = Queue([1, 2, 3, 4, 5])
        self.assertEqual(q.remove_if(lambda x: x in (1, 3, 5)), [1, 3, 5])
        self.assertEqual(q.to_list(), [2, 4])
        self.assertEqual(len(q), 2)
        q.enqueue(6)  # опашката (tail) трябва да е коректна след премахването
        self.assertEqual(q.to_list(), [2, 4, 6])

    def test_remove_all(self):
        q = Queue([1, 2])
        q.remove_if(lambda x: True)
        self.assertTrue(q.is_empty())
        q.enqueue(9)
        self.assertEqual(q.to_list(), [9])


class SortingTests(unittest.TestCase):
    CASES = [
        [],
        [1],
        [2, 1],
        [5, 3, 8, 1, 9, 2, 7],
        list(range(100)),
        list(range(100, 0, -1)),
        [3] * 50,
        [random.Random(i).randint(1, 4) for i in range(300)],
        [random.Random(7).random() for _ in range(500)],
    ]

    def test_matches_builtin(self):
        for fn in (quick_sort, merge_sort):
            for data in self.CASES:
                with self.subTest(fn=fn.__name__, n=len(data)):
                    self.assertEqual(fn(data), sorted(data))
                    self.assertEqual(fn(data, reverse=True), sorted(data, reverse=True))

    def test_does_not_modify_input(self):
        data = [3, 1, 2]
        quick_sort(data)
        merge_sort(data)
        self.assertEqual(data, [3, 1, 2])

    def test_key_function(self):
        words = ["банан", "Ябълка", "круша", "арбуз"]
        for fn in (quick_sort, merge_sort):
            self.assertEqual(fn(words, key=str.casefold), sorted(words, key=str.casefold))

    def test_merge_sort_is_stable(self):
        pairs = [(2, "a"), (1, "b"), (2, "c"), (1, "d"), (2, "e")]
        self.assertEqual(merge_sort(pairs, key=lambda p: p[0]),
                         [(1, "b"), (1, "d"), (2, "a"), (2, "c"), (2, "e")])
        self.assertEqual(merge_sort(pairs, key=lambda p: p[0], reverse=True),
                         [(2, "a"), (2, "c"), (2, "e"), (1, "b"), (1, "d")])

    def test_counts_comparisons(self):
        stats = {"comparisons": 0}
        merge_sort(list(range(64, 0, -1)), stats=stats)
        self.assertGreater(stats["comparisons"], 0)
        self.assertLessEqual(stats["comparisons"], 64 * 6)  # n*log2(n)

    def test_quick_sort_large_sorted_input_no_recursion_error(self):
        data = list(range(20000))
        self.assertEqual(quick_sort(data), data)
        self.assertEqual(quick_sort([1] * 20000), [1] * 20000)


class SearchingTests(unittest.TestCase):
    def test_linear_search(self):
        data = [5, 3, 8, 3, 1]
        self.assertEqual(linear_search(data, lambda x: x == 3), [3, 3])
        self.assertEqual(linear_search(data, lambda x: x > 100), [])
        self.assertEqual(linear_search_first(data, lambda x: x == 8), 2)
        self.assertEqual(linear_search_first(data, lambda x: x == 42), -1)

    def test_binary_search_every_element(self):
        data = list(range(0, 200, 2))
        for i, value in enumerate(data):
            self.assertEqual(binary_search(data, value), i)
        for missing in (-1, 1, 199, 500):
            self.assertEqual(binary_search(data, missing), -1)
        self.assertEqual(binary_search([], 1), -1)

    def test_binary_search_with_key_and_log_steps(self):
        records = [{"id": i} for i in range(1, 1025)]
        stats = {"comparisons": 0}
        index = binary_search(records, 777, key=lambda r: r["id"], stats=stats)
        self.assertEqual(records[index]["id"], 777)
        self.assertLessEqual(stats["comparisons"], 11)  # log2(1024) + 1


if __name__ == "__main__":
    unittest.main()
