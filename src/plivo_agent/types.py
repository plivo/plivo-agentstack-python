"""Shared types and base models."""

from __future__ import annotations

from typing import Any


class ApiResponse(dict):
    """Thin wrapper around API response dicts for attribute access."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"No attribute '{name}'") from None
