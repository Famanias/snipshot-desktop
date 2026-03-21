"""
SnipShot Desktop - API Module
"""

from .client import api_client as _default_client, APIClient


class _ClientProxy:
    """Transparent proxy that delegates to whichever client is currently active.

    All existing code that does ``from api import api_client`` keeps working
    unchanged — method / attribute access is forwarded to the underlying
    implementation, which can be swapped at runtime via ``set_impl``.
    """

    def __init__(self, impl):
        self._impl = impl

    def __getattr__(self, name):
        return getattr(self._impl, name)

    def set_impl(self, client):
        """Replace the active client implementation."""
        self._impl = client

    def reset(self):
        """Restore the default (online) API client."""
        self._impl = _default_client


api_client = _ClientProxy(_default_client)

__all__ = ["api_client", "APIClient"]
