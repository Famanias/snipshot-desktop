"""
SnipShot Desktop - Supabase API Client

Direct Supabase connection — no local database_api server required.
All public methods return a consistent response envelope:

    {"success": bool, "data": Any, "error": Optional[str]}

Security rules enforced here:
  - SUPABASE_SERVICE_KEY is NEVER used anywhere in this file.
  - All data access relies on RLS policies enforced by Supabase with the
    anon key + a valid user JWT.
  - Tokens are persisted via the OS keychain (see api/token_storage.py).

Delete order rule:
  - Storage objects are always deleted BEFORE the corresponding DB row.
    If the DB row is removed first and the storage delete fails, the object
    becomes an untracked orphan.  The reverse order keeps cleanup possible.
"""

import time
from typing import Any, Optional

from supabase import create_client, Client

from api.token_storage import load_tokens, save_tokens, clear_tokens
from config import SUPABASE_URL, SUPABASE_ANON_KEY

# Name of the storage bucket used for user images
_IMAGE_BUCKET = "images"


class SupabaseAPIClient:
    """Direct Supabase client for auth, folder, and image operations."""

    # ------------------------------------------------------------------
    # Initialisation & session restore
    # ------------------------------------------------------------------

    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise EnvironmentError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in the environment "
                "or .env file.  See .env.example for the required variables."
            )
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        self._restore_session()

    def _restore_session(self) -> None:
        """On app startup, reload persisted tokens from the OS keychain."""
        tokens = load_tokens()
        if tokens:
            try:
                self.client.auth.set_session(
                    tokens["access_token"],
                    tokens["refresh_token"],
                )
            except Exception:
                # Tokens invalid or expired past their refresh window.
                clear_tokens()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def is_authenticated(self) -> bool:
        """True when there is an active authenticated session."""
        try:
            user = self.client.auth.get_user()
            return user is not None and user.user is not None
        except Exception:
            return False

    def _ok(self, data: Any = None) -> dict:
        return {"success": True, "data": data, "error": None}

    def _err(self, error: Exception | str) -> dict:
        return {"success": False, "data": None, "error": str(error)}

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def register(self, email: str, password: str) -> dict:
        """Register a new user account.

        Returns the Supabase User object on success.
        Note: Supabase may require email confirmation depending on project
        settings.  If ``res.session`` is None the user must confirm their
        email before tokens can be stored.
        """
        try:
            res = self.client.auth.sign_up({"email": email, "password": password})
            if res.session:
                save_tokens(res.session.access_token, res.session.refresh_token)
            return self._ok(res.user)
        except Exception as e:
            return self._err(e)

    def login(self, email: str, password: str) -> dict:
        """Sign in with email and password."""
        try:
            res = self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            save_tokens(res.session.access_token, res.session.refresh_token)
            return self._ok(res.user)
        except Exception as e:
            return self._err(e)

    def logout(self) -> dict:
        """Sign out and clear persisted tokens."""
        try:
            self.client.auth.sign_out()
            clear_tokens()
            return self._ok()
        except Exception as e:
            # Even if sign_out fails remotely, clear local tokens so the user
            # isn't stuck in a broken authenticated state.
            clear_tokens()
            return self._err(e)

    def get_profile(self) -> dict:
        """Return the currently authenticated user object."""
        try:
            user = self.client.auth.get_user()
            return self._ok(user)
        except Exception as e:
            return self._err(e)

    # ------------------------------------------------------------------
    # Folders
    # ------------------------------------------------------------------

    def get_folders(self) -> dict:
        """Fetch all folders belonging to the current user.

        RLS on the ``folders`` table ensures only the user's own rows are
        returned — no ``user_id`` filter is needed here.
        """
        try:
            res = self.client.table("folders").select("*").execute()
            return self._ok(res.data)
        except Exception as e:
            return self._err(e)

    def create_folder(self, name: str, description: str = "") -> dict:
        """Create a new folder for the current user."""
        try:
            user = self.client.auth.get_user()
            res = (
                self.client.table("folders")
                .insert(
                    {
                        "name": name,
                        "description": description,
                        "user_id": user.user.id,
                    }
                )
                .execute()
            )
            return self._ok(res.data)
        except Exception as e:
            return self._err(e)

    def update_folder(
        self, folder_id: str, name: str, description: str = ""
    ) -> dict:
        """Update the name and/or description of an existing folder."""
        try:
            res = (
                self.client.table("folders")
                .update({"name": name, "description": description})
                .eq("id", folder_id)
                .execute()
            )
            return self._ok(res.data)
        except Exception as e:
            return self._err(e)

    def delete_folder(self, folder_id: str, delete_images: bool = False) -> dict:
        """Delete a folder.

        If ``delete_images=True``, all images inside the folder are removed
        from Supabase Storage first (to avoid orphaned objects), then their
        DB records are deleted, and finally the folder itself is deleted.

        Storage objects are always deleted BEFORE their DB rows.
        """
        try:
            if delete_images:
                # 1. Fetch all images in this folder
                img_res = (
                    self.client.table("images")
                    .select("id, storage_path")
                    .eq("folder_id", folder_id)
                    .execute()
                )

                for img in img_res.data:
                    storage_path = img.get("storage_path")
                    if storage_path:
                        # 2. Delete from storage first (orphan prevention)
                        try:
                            self.client.storage.from_(_IMAGE_BUCKET).remove(
                                [storage_path]
                            )
                        except Exception:
                            pass  # Log in production; don't block folder delete

                    # 3. Delete the DB record
                    (
                        self.client.table("images")
                        .delete()
                        .eq("id", img["id"])
                        .execute()
                    )

            # 4. Delete the folder row
            self.client.table("folders").delete().eq("id", folder_id).execute()
            return self._ok()
        except Exception as e:
            return self._err(e)

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    def get_images(
        self, folder_id: str, page: int = 1, per_page: int = 20
    ) -> dict:
        """Fetch a paginated list of images in a folder."""
        try:
            offset = (page - 1) * per_page
            res = (
                self.client.table("images")
                .select("*")
                .eq("folder_id", folder_id)
                .range(offset, offset + per_page - 1)
                .execute()
            )
            return self._ok(res.data)
        except Exception as e:
            return self._err(e)

    def upload_image(
        self,
        file_path: str,
        original_filename: str,
        source_lang: str,
        target_lang: str,
        folder_id: str,
    ) -> dict:
        """Upload an image file to Supabase Storage and record it in the DB.

        Storage path format: ``{user_id}/{timestamp}_{original_filename}``
        This keeps files scoped under the owner's prefix, which aligns with
        the recommended storage RLS policy.
        """
        try:
            user = self.client.auth.get_user()
            user_id = user.user.id
            timestamp = int(time.time())
            storage_path = f"{user_id}/{timestamp}_{original_filename}"

            with open(file_path, "rb") as f:
                self.client.storage.from_(_IMAGE_BUCKET).upload(storage_path, f)

            public_url = self.client.storage.from_(_IMAGE_BUCKET).get_public_url(
                storage_path
            )

            res = (
                self.client.table("images")
                .insert(
                    {
                        "folder_id": folder_id,
                        "user_id": user_id,
                        "storage_path": storage_path,
                        "public_url": public_url,
                        "original_filename": original_filename,
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                    }
                )
                .execute()
            )

            return self._ok(res.data[0] if res.data else None)
        except Exception as e:
            return self._err(e)

    def upload_image_bytes(
        self,
        image_bytes: bytes,
        original_filename: str,
        source_lang: str,
        target_lang: str,
        folder_id: str,
    ) -> dict:
        """Upload raw image bytes to Supabase Storage and record in the DB.

        Mirrors ``upload_image`` but accepts ``bytes`` instead of a file path,
        which is useful when the image comes directly from the translator API.
        """
        try:
            user = self.client.auth.get_user()
            user_id = user.user.id
            timestamp = int(time.time())
            storage_path = f"{user_id}/{timestamp}_{original_filename}"

            self.client.storage.from_(_IMAGE_BUCKET).upload(
                storage_path,
                image_bytes,
                file_options={"content-type": "image/png"},
            )

            public_url = self.client.storage.from_(_IMAGE_BUCKET).get_public_url(
                storage_path
            )

            res = (
                self.client.table("images")
                .insert(
                    {
                        "folder_id": folder_id,
                        "user_id": user_id,
                        "storage_path": storage_path,
                        "public_url": public_url,
                        "original_filename": original_filename,
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                    }
                )
                .execute()
            )

            return self._ok(res.data[0] if res.data else None)
        except Exception as e:
            return self._err(e)

    def delete_image(self, image_id: str) -> dict:
        """Delete an image from Storage first, then remove the DB record.

        The order is intentional: storage objects must be removed before the
        DB row so they can always be looked up if a partial failure occurs.
        """
        try:
            # 1. Fetch storage path before touching anything
            res = (
                self.client.table("images")
                .select("storage_path")
                .eq("id", image_id)
                .single()
                .execute()
            )
            storage_path = res.data["storage_path"]

            # 2. Delete from storage first
            self.client.storage.from_(_IMAGE_BUCKET).remove([storage_path])

            # 3. Remove the DB row
            self.client.table("images").delete().eq("id", image_id).execute()
            return self._ok()
        except Exception as e:
            return self._err(e)

    def search_images(self, query: str) -> dict:
        """Search images by filename (case-insensitive, substring match).

        RLS ensures only the current user's images are searched.
        """
        try:
            res = (
                self.client.table("images")
                .select("*")
                .ilike("original_filename", f"%{query}%")
                .execute()
            )
            return self._ok(res.data)
        except Exception as e:
            return self._err(e)

    # ------------------------------------------------------------------
    # Translation (pass-through — kept for interface compatibility)
    # ------------------------------------------------------------------

    def translate_image(self, image_bytes: bytes, config: dict = None) -> dict:
        """Delegate to the external translator API.

        The Supabase client does not talk to the translator directly; the
        actual HTTP call is still handled by the underlying ``APIClient``.
        This stub raises ``NotImplementedError`` so callers know to use the
        original HTTP client's ``translate_image`` method.

        Rationale: translation is a separate service; mixing it here would
        violate single-responsibility.  The ``_ClientProxy`` in
        ``api/__init__.py`` can be used to route translation calls to a
        dedicated client while Supabase handles auth/data.
        """
        raise NotImplementedError(
            "translate_image is not handled by SupabaseAPIClient.  "
            "Route translation calls to the HTTPAPIClient or a dedicated "
            "TranslatorClient via the _ClientProxy.set_impl() mechanism."
        )
