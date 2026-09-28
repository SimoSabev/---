"""Собствени реализации на структурите от данни стек (Stack) и опашка (Queue).

И двете са изградени върху свързани възли (linked nodes), така че основните
операции са O(1) и не зависят от броя на елементите.
"""

from __future__ import annotations

from typing import Any, Callable, Iterator, List, Optional


class _Node:
    __slots__ = ("value", "next")

    def __init__(self, value: Any, next_node: Optional["_Node"] = None) -> None:
        self.value = value
        self.next = next_node


class Stack:
    """Стек (LIFO – последният влязъл излиза пръв).

    Използва се за приключените задачи: най-отгоре винаги е последно
    приключената задача, което позволява операция "отмени последното
    приключване" (undo) за O(1).

    push / pop / peek – O(1); обхождане – O(n).
    """

    def __init__(self, items: Optional[List[Any]] = None) -> None:
        self._top: Optional[_Node] = None
        self._size = 0
        for item in items or []:
            self.push(item)

    def push(self, value: Any) -> None:
        self._top = _Node(value, self._top)
        self._size += 1

    def pop(self) -> Any:
        if self._top is None:
            raise IndexError("Стекът е празен")
        node = self._top
        self._top = node.next
        self._size -= 1
        return node.value

    def peek(self) -> Any:
        if self._top is None:
            raise IndexError("Стекът е празен")
        return self._top.value

    def is_empty(self) -> bool:
        return self._top is None

    def clear(self) -> None:
        self._top = None
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[Any]:
        """Обхожда от върха към дъното (от най-новия към най-стария)."""
        node = self._top
        while node is not None:
            yield node.value
            node = node.next

    def to_list(self) -> List[Any]:
        """Връща елементите от дъното към върха (реда, в който са добавени)."""
        items = list(self)
        items.reverse()
        return items

    def remove_if(self, predicate: Callable[[Any], bool]) -> List[Any]:
        """Премахва всички елементи, за които predicate е True. O(n).

        Запазва относителния ред на останалите елементи.
        """
        kept, removed = [], []
        for item in self.to_list():
            (removed if predicate(item) else kept).append(item)
        self.clear()
        for item in kept:
            self.push(item)
        return removed

    def __repr__(self) -> str:
        return f"Stack({self.to_list()!r})"


class Queue:
    """Опашка (FIFO – първият влязъл излиза пръв).

    Използва се за чакащите задачи: новите задачи се добавят в края,
    а изпълнителите поемат задачата от началото на опашката.

    enqueue / dequeue / peek – O(1); обхождане – O(n).
    """

    def __init__(self, items: Optional[List[Any]] = None) -> None:
        self._head: Optional[_Node] = None
        self._tail: Optional[_Node] = None
        self._size = 0
        for item in items or []:
            self.enqueue(item)

    def enqueue(self, value: Any) -> None:
        node = _Node(value)
        if self._tail is None:
            self._head = self._tail = node
        else:
            self._tail.next = node
            self._tail = node
        self._size += 1

    def dequeue(self) -> Any:
        if self._head is None:
            raise IndexError("Опашката е празна")
        node = self._head
        self._head = node.next
        if self._head is None:
            self._tail = None
        self._size -= 1
        return node.value

    def peek(self) -> Any:
        if self._head is None:
            raise IndexError("Опашката е празна")
        return self._head.value

    def is_empty(self) -> bool:
        return self._head is None

    def clear(self) -> None:
        self._head = self._tail = None
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[Any]:
        """Обхожда от началото към края на опашката."""
        node = self._head
        while node is not None:
            yield node.value
            node = node.next

    def to_list(self) -> List[Any]:
        return list(self)

    def remove_if(self, predicate: Callable[[Any], bool]) -> List[Any]:
        """Премахва всички елементи, за които predicate е True. O(n).

        Пренасочва връзките между възлите, без да създава нова опашка.
        """
        removed = []
        prev: Optional[_Node] = None
        node = self._head
        while node is not None:
            if predicate(node.value):
                removed.append(node.value)
                if prev is None:
                    self._head = node.next
                else:
                    prev.next = node.next
                if node is self._tail:
                    self._tail = prev
                self._size -= 1
            else:
                prev = node
            node = node.next
        return removed

    def __repr__(self) -> str:
        return f"Queue({self.to_list()!r})"
