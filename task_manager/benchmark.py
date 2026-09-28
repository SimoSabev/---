"""Експериментално сравнение на алгоритмите за сортиране и търсене."""

from __future__ import annotations

import math
import random
import time
from typing import Callable, Dict, List

from .searching import binary_search, linear_search_first
from .sorting import merge_sort, quick_sort


def _measure(fn: Callable, *args, **kwargs):
    stats = {"comparisons": 0}
    start = time.perf_counter()
    result = fn(*args, stats=stats, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return result, stats["comparisons"], elapsed_ms


def compare_sorting(n: int, seed: int = 42) -> List[Dict]:
    """Сравнява Quick Sort и Merge Sort върху три вида входни данни.

    Данните наподобяват задачи: (приоритет 1..4, оценка в часове).
    """
    rng = random.Random(seed)
    base = [(rng.randint(1, 4), rng.randint(1, 40)) for _ in range(n)]
    datasets = {
        "случайни": base,
        "вече сортирани": sorted(base),
        "обратно сортирани": sorted(base, reverse=True),
    }
    rows = []
    for name, data in datasets.items():
        expected = sorted(data)
        for label, fn in (("Quick Sort", quick_sort), ("Merge Sort", merge_sort)):
            result, comparisons, ms = _measure(fn, data)
            rows.append({
                "data": name,
                "algorithm": label,
                "comparisons": comparisons,
                "time_ms": ms,
                "correct": result == expected,
            })
    return rows


def compare_searching(n: int, queries: int = 200, seed: int = 42) -> Dict[str, float]:
    """Средният брой сравнения при линейно и двоично търсене по ID."""
    rng = random.Random(seed)
    ids = list(range(1, n + 1))  # сортирани ID-та, както в системата
    targets = [rng.randint(1, n) for _ in range(queries)]
    linear_total = binary_total = 0
    linear_ms = binary_ms = 0.0
    for target in targets:
        index, comparisons, ms = _measure(linear_search_first, ids, lambda x, t=target: x == t)
        assert ids[index] == target
        linear_total += comparisons
        linear_ms += ms
        index, comparisons, ms = _measure(binary_search, ids, target)
        assert ids[index] == target
        binary_total += comparisons
        binary_ms += ms
    return {
        "linear_avg": linear_total / queries,
        "binary_avg": binary_total / queries,
        "linear_ms": linear_ms,
        "binary_ms": binary_ms,
        "log2n": math.log2(n) if n > 0 else 0.0,
    }
