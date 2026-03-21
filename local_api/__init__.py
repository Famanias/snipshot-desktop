"""
SnipShot Desktop - Local API Module

Provides a local-only API client that stores data in SQLite + local filesystem.
"""

from .client import LocalAPIClient

__all__ = ["LocalAPIClient"]
