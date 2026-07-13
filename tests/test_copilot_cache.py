"""Unit tests for the answer cache (C3.3 / L4).

Repeated identical questions should never re-spend the model budget. Keys are normalized
so trivial variations (case, whitespace) hit the same entry, and the cache is bounded so
it can't grow without limit.
"""
from copilot.cache import AnswerCache


def test_miss_then_hit():
    c = AnswerCache(capacity=8)
    assert c.get("default rate?") is None
    c.set("default rate?", {"answer": "12%"})
    assert c.get("default rate?") == {"answer": "12%"}


def test_key_is_normalized_for_case_and_whitespace():
    c = AnswerCache(capacity=8)
    c.set("Default   Rate?", {"answer": "x"})
    assert c.get("default rate?") == {"answer": "x"}


def test_capacity_evicts_least_recently_used():
    c = AnswerCache(capacity=2)
    c.set("a", 1)
    c.set("b", 2)
    assert c.get("a") == 1        # touch 'a' so 'b' is now LRU
    c.set("c", 3)                 # evicts 'b'
    assert c.get("b") is None
    assert c.get("a") == 1
    assert c.get("c") == 3


def test_clear_empties_the_cache():
    c = AnswerCache(capacity=8)
    c.set("a", 1)
    c.clear()
    assert c.get("a") is None
