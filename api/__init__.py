"""
SnipShot Desktop - API Module

Architecture:
  - SupabaseAPIClient: Authentication, database, and storage (Supabase)
  - TranslatorClient: Image translation and OCR (Azure translator backend)
  - LocalAPIClient: Offline/local mode (optional)

Default client: SupabaseAPIClient with embedded TranslatorClient.

The _ClientProxy allows runtime swapping of the entire implementation without
touching UI code:

    # Switch to local mode
    from local_api.client import LocalAPIClient
    api_client.set_impl(LocalAPIClient())

    # Restore Supabase
    api_client.reset()

Rollback to the old HTTP client is also supported:
    from api.client import APIClient
    api_client.set_impl(APIClient())
"""

from .supabase_client import SupabaseAPIClient
from .translator_client import TranslatorClient
from .client import APIClient  # kept for rollback / local dev
from local_api.client import LocalAPIClient

# Attempt to initialize SupabaseAPIClient, but fall back to LocalAPIClient if
# Supabase credentials are not configured or if there's an initialization error.
# This allows the app to start even when SUPABASE_URL / SUPABASE_ANON_KEY are not set,
# or if there are compatibility issues, and users can click "Use Local Mode" on the
# login screen to proceed.
try:
    _default_client = SupabaseAPIClient()
except Exception:
    # Supabase initialization failed (missing credentials or other error)—use local mode
    _default_client = LocalAPIClient()


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
        """Restore the default Supabase client."""
        self._impl = _default_client


api_client = _ClientProxy(_default_client)

__all__ = ["api_client", "SupabaseAPIClient", "TranslatorClient", "APIClient"]
