"""Алгоритми за сортиране: бързо сортиране (Quick Sort) и сортиране чрез сливане (Merge Sort).

И двете функции:
  * връщат НОВ сортиран списък (входният не се променя);
  * приемат ``key`` – функция, която дава ключа за сравнение (както ``sorted``);
  * приемат ``reverse`` – сортиране в низходящ ред;
  * по желание броят сравненията в речника ``stats["comparisons"]``.

Ключът се изчислява само веднъж за всеки елемент (decorate-sort-undecorate).
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Sequence, Tuple

KeyFunc = Optional[Callable[[Any], Any]]
_Pair = Tuple[Any, Any]  # (ключ, елемент)


def _compare(a: Any, b: Any, reverse: bool, stats: Optional[dict]) -> int:
    """Връща -1, 0 или 1 според наредбата на ключовете a и b."""
    if stats is not None:
        stats["comparisons"] = stats.get("comparisons", 0) + 1
    if a < b:
        result = -1
    elif b < a:
        result = 1
    else:
        result = 0
    return -result if reverse else result


def _decorate(items: Sequence[Any], key: KeyFunc) -> List[_Pair]:
    if key is None:
        return [(item, item) for item in items]
    return [(key(item), item) for item in items]


# ---------------------------------------------------------------------------
# Quick Sort
# ---------------------------------------------------------------------------
def quick_sort(items: Sequence[Any], key: KeyFunc = None, reverse: bool = False,
               stats: Optional[dict] = None) -> List[Any]:
    """Бързо сортиране (Quick Sort).

    Подобрения спрямо класическия вариант:
      * опорният елемент (pivot) е медианата на първия, средния и последния
        елемент – предпазва от O(n^2) при вече сортирани данни;
      * тристранно разделяне (< pivot | = pivot | > pivot) – ефективно при
        много повтарящи се ключове (напр. приоритети 1..4);
      * рекурсия само върху по-малката част – дълбочина на стека O(log n).

    Сложност: средно O(n log n), най-лошо O(n^2); памет O(log n).
    Не е стабилно сортиране.
    """
    data = _decorate(items, key)
    _quick_sort(data, 0, len(data) - 1, reverse, stats)
    return [item for _, item in data]


def _median_of_three(data: List[_Pair], lo: int, hi: int, reverse: bool) -> Any:
    mid = (lo + hi) // 2
    a, b, c = data[lo][0], data[mid][0], data[hi][0]
    if _compare(a, b, reverse, None) > 0:
        a, b = b, a
    if _compare(b, c, reverse, None) > 0:
        b, c = c, b
        if _compare(a, b, reverse, None) > 0:
            a, b = b, a
    return b


def _quick_sort(data: List[_Pair], lo: int, hi: int, reverse: bool,
                stats: Optional[dict]) -> None:
    while lo < hi:
        pivot = _median_of_three(data, lo, hi, reverse)
        # Тристранно разделяне (алгоритъм на Дейкстра – "холандското знаме"):
        # data[lo:lt] < pivot, data[lt:i] == pivot, data[gt+1:hi+1] > pivot
        lt, i, gt = lo, lo, hi
        while i <= gt:
            cmp = _compare(data[i][0], pivot, reverse, stats)
            if cmp < 0:
                data[lt], data[i] = data[i], data[lt]
                lt += 1
                i += 1
            elif cmp > 0:
                data[i], data[gt] = data[gt], data[i]
                gt -= 1
            else:
                i += 1
        # Рекурсия върху по-малката част, цикъл върху по-голямата.
        if lt - lo < hi - gt:
            _quick_sort(data, lo, lt - 1, reverse, stats)
            lo = gt + 1
        else:
            _quick_sort(data, gt + 1, hi, reverse, stats)
            hi = lt - 1


# ---------------------------------------------------------------------------
# Merge Sort
# ---------------------------------------------------------------------------
def merge_sort(items: Sequence[Any], key: KeyFunc = None, reverse: bool = False,
               stats: Optional[dict] = None) -> List[Any]:
    """Сортиране чрез сливане (Merge Sort).

    Разделя списъка на две половини, сортира ги рекурсивно и ги слива.
    Сложност: винаги O(n log n); допълнителна памет O(n).
    Стабилно сортиране – елементи с равни ключове запазват реда си
    (важно при сортиране по няколко критерия едно след друго).
    """
    data = _decorate(items, key)
    return [item for _, item in _merge_sort(data, reverse, stats)]


def _merge_sort(data: List[_Pair], reverse: bool, stats: Optional[dict]) -> List[_Pair]:
    if len(data) <= 1:
        return data[:]
    mid = len(data) // 2
    left = _merge_sort(data[:mid], reverse, stats)
    right = _merge_sort(data[mid:], reverse, stats)
    return _merge(left, right, reverse, stats)


def _merge(left: List[_Pair], right: List[_Pair], reverse: bool,
           stats: Optional[dict]) -> List[_Pair]:
    result: List[_Pair] = []
    i = j = 0
    while i < len(left) and j < len(right):
        # При равенство взимаме от лявата част -> стабилност.
        if _compare(right[j][0], left[i][0], reverse, stats) < 0:
            result.append(right[j])
            j += 1
        else:
            result.append(left[i])
            i += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result


ALGORITHMS = {
    "quick": ("Quick Sort (бързо сортиране)", quick_sort),
    "merge": ("Merge Sort (сортиране чрез сливане)", merge_sort),
}
