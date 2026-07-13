"""Structured errors for the semantic layer.

The copilot must never leak a stack trace or raw SQL to a user. Every contract
violation (unknown metric, window not valid for a metric) is a `SemanticError`
carrying a machine-readable `code` and a human message, so callers can return a clean
structured error instead of a 500.
"""
from __future__ import annotations


class SemanticError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)

    def as_dict(self) -> dict:
        return {"error": {"code": self.code, "message": self.message}}
