"""Answer cache (C3.3 / L4) — repeats never re-spend the model budget.

A bounded LRU keyed on the normalized question, so casing/whitespace variants of the
same question share one entry. In-memory per process (resets on cold start), which is
the right trade for a scale-to-zero demo.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Any


class AnswerCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self._store: OrderedDict[str, Any] = OrderedDict()

    @staticmethod
    def _key(question: str) -> str:
        return " ".join(question.lower().split())

    def get(self, question: str) -> Any | None:
        key = self._key(question)
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        return self._store[key]

    def set(self, question: str, value: Any) -> None:
        key = self._key(question)
        self._store[key] = value
        self._store.move_to_end(key)
        while len(self._store) > self.capacity:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()
