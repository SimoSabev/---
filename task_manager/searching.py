"""Алгоритми за търсене: линейно (Linear Search) и двоично (Binary Search)."""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Sequence

KeyFunc = Optional[Callable[[Any], Any]]


def _count(stats: Optional[dict]) -> None:
    if stats is not None:
        stats["comparisons"] = stats.get("comparisons", 0) + 1


def linear_search(items: Sequence[Any], predicate: Callable[[Any], bool],
                  stats: Optional[dict] = None) -> List[Any]:
    """Линейно търсене – проверява всеки елемент последователно.

    Връща ВСИЧКИ елементи, отговарящи на условието.
    Работи с несортирани данни и произволни условия (напр. част от текст).
    Сложност: O(n).
    """
    result = []
    for item in items:
        _count(stats)
        if predicate(item):
            result.append(item)
    return result


def linear_search_first(items: Sequence[Any], predicate: Callable[[Any], bool],
                        stats: Optional[dict] = None) -> int:
    """Линейно търсене на първото съвпадение. Връща индекса или -1. O(n)."""
    for index, item in enumerate(items):
        _count(stats)
        if predicate(item):
            return index
    return -1


def binary_search(sorted_items: Sequence[Any], target: Any, key: KeyFunc = None,
                  stats: Optional[dict] = None) -> int:
    """Двоично търсене в списък, сортиран във възходящ ред по ``key``.

    На всяка стъпка сравнява търсената стойност със средния елемент и
    отхвърля половината от оставащите елементи.
    Връща индекса на намерения елемент или -1.
    Сложност: O(log n). Изисква сортирани данни.
    """
    lo, hi = 0, len(sorted_items) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        value = sorted_items[mid] if key is None else key(sorted_items[mid])
        _count(stats)
        if value == target:
            return mid
        if value < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
