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

ID type rules (matches Supabase schema):
  - folders.id   → serial  → Python int
  - images.id    → serial  → Python int
  - folder_id    → integer → Python int
  - user_id      → uuid    → Python str (Supabase handles casting)

Delete order rule:
  - Storage objects are always deleted BEFORE the corresponding DB row.
    If the DB row is removed first and the storage delete fails, the object
    becomes an untracked orphan. The reverse order keeps cleanup possible.
"""

import time
from typing import Any, Optional

import httpx
from supabase import create_client, Client

from api.token_storage import load_tokens, save_tokens, clear_tokens
from api.translator_client import TranslatorClient, _TokenExpired
from api.exceptions import AuthenticationError
from config import SUPABASE_URL, SUPABASE_ANON_KEY

# Name of the storage bucket used for user images
_IMAGE_BUCKET = "images"

# Sentinel to distinguish between "not provided" and "set to None"
_UNSET = object()


class SupabaseAPIClient:
    """Direct Supabase client for auth, folder, and image operations."""

    # ------------------------------------------------------------------
    # Initialisation & session restore
    # ------------------------------------------------------------------

    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise EnvironmentError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in the environment "
                "or .env file. See .env.example for the required variables."
            )
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        self.user = None
        self._translator = TranslatorClient()
        self._restore_session()

    def _restore_session(self) -> None:
        """On app startup, reload persisted tokens from the OS keychain."""
        tokens = load_tokens()
        if tokens:
            try:
                res = self.client.auth.set_session(
                    tokens["access_token"],
                    tokens["refresh_token"],
                )
                if res and res.user:
                    self.user = res.user
            except Exception:
                # Tokens invalid or expired past their refresh window
                clear_tokens()
                self.user = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def access_token(self) -> Optional[str]:
        """Always read the token from the live Supabase session, never a cached copy."""
        session = self.client.auth.get_session()
        return session.access_token if session else None

    @property
    def refresh_token(self) -> Optional[str]:
        """Always read the token from the live Supabase session, never a cached copy."""
        session = self.client.auth.get_session()
        return session.refresh_token if session else None

    @property
    def is_authenticated(self) -> bool:
        """True when there is an active authenticated session."""
        return self.user is not None

    def _ok(self, data: Any = None) -> dict:
        return {"success": True, "data": data, "error": None}

    def _err(self, error) -> dict:
        return {"success": False, "data": None, "error": str(error)}

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def register(self, email: str, password: str) -> dict:
        """Register a new user account.

        Note: Supabase may require email confirmation depending on project
        settings. If res.session is None the user must confirm their email
        before tokens can be stored.
        """
        try:
            res = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "email_redirect_to": "https://snipshot.space/welcome/new-user"
                }
            })
            if res.session:
                save_tokens(res.session.access_token, res.session.refresh_token)
            self.user = res.user
            return self._ok(res.user)
        except Exception as e:
            self.user = None
            return self._err(e)

    def login(self, email: str, password: str) -> dict:
        """Sign in with email and password."""
        try:
            res = self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            save_tokens(res.session.access_token, res.session.refresh_token)
            self.user = res.user
            return self._ok(res.user)
        except Exception as e:
            self.user = None
            return self._err(e)

    def logout(self) -> dict:
        """Sign out and clear persisted tokens."""
        try:
            self.client.auth.sign_out()
        except Exception:
            pass  # Always clear local state even if remote sign-out fails
        finally:
            clear_tokens()
            self.user = None
        return self._ok()

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
        try:
            # Fetch folders with a count of related images via Supabase foreign key join
            res = (
                self.client.table("folders")
                .select("*, images(id)")
                .execute()
            )

            # Compute image_count from the joined images list
            folders = []
            for folder in res.data:
                images = folder.pop("images", []) or []
                folder["image_count"] = len(images)
                folders.append(folder)

            return self._ok(folders)
        except Exception as e:
            return self._err(e)

    def create_folder(self, name: str, description: str = "", parent_folder_id: int = None) -> dict:
        """Create a new folder for the current user."""
        try:
            insert_data = {
                "name": name,
                "description": description,
                "user_id": self.user.id,
            }
            if parent_folder_id is not None:
                insert_data["parent_folder_id"] = parent_folder_id

            res = (
                self.client.table("folders")
                .insert(insert_data)
                .execute()
            )
            return self._ok(res.data[0] if res.data else None)
        except Exception as e:
            return self._err(e)

    def get_folder(self, folder_id: int) -> dict:
        """Fetch a single folder by ID."""
        try:
            res = (
                self.client.table("folders")
                .select("*")
                .eq("id", folder_id)
                .single()
                .execute()
            )
            return self._ok(res.data)
        except Exception as e:
            return self._err(e)

    def update_folder(
        self, folder_id: int, name: str = None, description: str = None, parent_folder_id: Any = _UNSET
    ) -> dict:
        """Update the name and/or description/parent of an existing folder."""
        try:
            updates = {}
            if name is not None:
                updates["name"] = name
            if description is not None:
                updates["description"] = description
            if parent_folder_id is not _UNSET:
                updates["parent_folder_id"] = parent_folder_id
                
            if not updates:
                return self._err("Nothing to update")
            res = (
                self.client.table("folders")
                .update(updates)
                .eq("id", folder_id)
                .execute()
            )
            return self._ok(res.data[0] if res.data else None)
        except Exception as e:
            return self._err(e)

    def delete_folder(self, folder_id: int, delete_images: bool = False) -> dict:
        """Delete a folder.

        If delete_images=True, all images inside the folder are removed
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
    # Signed URL Helpers
    # ------------------------------------------------------------------

    def _get_signed_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """Fetch a single signed URL from Supabase storage."""
        try:
            res = self.client.storage.from_(_IMAGE_BUCKET).create_signed_url(
                path, expires_in=expires_in
            )
            return res.get("signedURL") or res.get("signedUrl")
        except Exception as e:
            print(f"Error generating signed URL for path {path}: {e}")
            return None

    def _get_signed_urls(self, paths: list[str], expires_in: int = 3600) -> dict[str, str]:
        """Fetch signed URLs in batch from Supabase storage.

        Returns a dict mapping path -> signed URL.
        """
        if not paths:
            return {}
        try:
            res = self.client.storage.from_(_IMAGE_BUCKET).create_signed_urls(
                paths, expires_in=expires_in
            )
            url_map = {}
            for item in res:
                if item and not item.get("error"):
                    path = item.get("path")
                    signed_url = item.get("signedURL") or item.get("signedUrl")
                    if path and signed_url:
                        url_map[path] = signed_url
                elif item and item.get("error"):
                    print(f"Error in batch signed URL for {item.get('path')}: {item.get('error')}")
            return url_map
        except Exception as e:
            print(f"Error in batch signed URL generation: {e}")
            return {}

    def _sign_single_image_url(self, img: dict, expires_in: int = 3600) -> dict:
        """Populate the public_url field in a single image dictionary."""
        if not img:
            return img
        path = img.get("storage_path")
        if path:
            img["public_url"] = self._get_signed_url(path, expires_in=expires_in) or ""
            img["_signed_at"] = time.time()
        else:
            img["public_url"] = ""
            img["_signed_at"] = 0
        return img

    def _sign_image_urls(self, images: list[dict], expires_in: int = 3600) -> list[dict]:
        """Populate the public_url field in a list of image dictionaries."""
        if not images:
            return images
        paths = [img["storage_path"] for img in images if img.get("storage_path")]
        url_map = self._get_signed_urls(paths, expires_in=expires_in)
        now = time.time()
        for img in images:
            path = img.get("storage_path")
            if path and path in url_map:
                img["public_url"] = url_map[path]
                img["_signed_at"] = now
            else:
                img["public_url"] = ""
                img["_signed_at"] = 0
        return images

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    def get_images(
        self, folder_id: int = None, page: int = 1, per_page: int = 50, unfiled_only: bool = False
    ) -> dict:
        """Fetch a paginated list of images.

        If folder_id is None, returns all images for the current user
        (RLS enforces user scoping automatically).
        If folder_id is provided, filters to that folder only.
        """
        try:
            offset = (page - 1) * per_page
            query = self.client.table("images").select("*")

            if unfiled_only:
                query = query.is_("folder_id", "null")
            elif folder_id is not None:
                query = query.eq("folder_id", folder_id)

            res = (
                query
                .order("created_at", desc=True)
                .range(offset, offset + per_page - 1)
                .execute()
            )

            # Fetch total count for pagination
            count_query = self.client.table("images").select("id", count="exact")
            if folder_id is not None:
                count_query = count_query.eq("folder_id", folder_id)
            count_res = count_query.execute()
            total = count_res.count if hasattr(count_res, "count") else len(res.data)

            return self._ok({
                "images": self._sign_image_urls(res.data),
                "total": total,
                "page": page,
                "per_page": per_page,
            })
        except Exception as e:
            return self._err(e)

    def get_image(self, image_id: int) -> dict:
        """Fetch a single image record by ID."""
        try:
            res = (
                self.client.table("images")
                .select("*")
                .eq("id", image_id)
                .single()
                .execute()
            )
            return self._ok(self._sign_single_image_url(res.data))
        except Exception as e:
            return self._err(e)

    def get_recent_images(self, page: int = 1, per_page: int = 20) -> dict:
        """Fetch the most recently created images across all folders."""
        try:
            offset = (page - 1) * per_page
            res = (
                self.client.table("images")
                .select("*")
                .order("created_at", desc=True)
                .range(offset, offset + per_page - 1)
                .execute()
            )
            return self._ok(self._sign_image_urls(res.data))
        except Exception as e:
            return self._err(e)

    def upload_image(
        self,
        file_path: str,
        original_filename: str,
        source_language: str,
        target_language: str,
        folder_id: int = None,
    ) -> dict:
        """Upload an image file to Supabase Storage and record it in the DB.

        Storage path format: {user_id}/{timestamp}_{original_filename}
        This keeps files scoped under the owner's prefix, which aligns with
        the recommended storage RLS policy.
        """
        try:
            user_id = self.user.id
            timestamp = int(time.time())
            storage_path = f"{user_id}/{timestamp}_{original_filename}"

            with open(file_path, "rb") as f:
                file_content = f.read()

            self.client.storage.from_(_IMAGE_BUCKET).upload(
                storage_path, file_content
            )
            file_size = len(file_content)

            res = (
                self.client.table("images")
                .insert(
                    {
                        "folder_id": folder_id,
                        "user_id": user_id,
                        "storage_path": storage_path,
                        "filename": original_filename,
                        "original_filename": original_filename,
                        "source_language": source_language,
                        "target_language": target_language,
                        "file_size": file_size,
                    }
                )
                .execute()
            )
            return self._ok(self._sign_single_image_url(res.data[0]) if res.data else None)
        except Exception as e:
            return self._err(e)

    def upload_image_bytes(
        self,
        image_bytes: bytes,
        original_filename: str,
        source_language: str,
        target_language: str,
        folder_id: int = None,
    ) -> dict:
        """Upload raw image bytes to Supabase Storage and record in the DB.

        Mirrors upload_image but accepts bytes instead of a file path,
        which is useful when the image comes directly from the translator API.
        """
        try:
            user_id = self.user.id
            timestamp = int(time.time())
            storage_path = f"{user_id}/{timestamp}_{original_filename}"

            self.client.storage.from_(_IMAGE_BUCKET).upload(
                storage_path,
                image_bytes,
                file_options={"content-type": "image/png"},
            )
            file_size = len(image_bytes)

            res = (
                self.client.table("images")
                .insert(
                    {
                        "folder_id": folder_id,
                        "user_id": user_id,
                        "storage_path": storage_path,
                        "filename": original_filename,
                        "original_filename": original_filename,
                        "source_language": source_language,
                        "target_language": target_language,
                        "file_size": file_size,
                    }
                )
                .execute()
            )
            return self._ok(self._sign_single_image_url(res.data[0]) if res.data else None)
        except Exception as e:
            return self._err(e)

    def save_image_from_bytes(
        self,
        image_bytes: bytes,
        filename: str,
        folder_id: int = None,
        source_language: str = None,
        target_language: str = None,
    ) -> dict:
        """Convenience wrapper matching the translation workflow call-site."""
        return self.upload_image_bytes(
            image_bytes=image_bytes,
            original_filename=filename,
            source_language=source_language or "",
            target_language=target_language or "",
            folder_id=folder_id,
        )

    def move_image_to_folder(
        self, image_id: int, filename: str = None, folder_id: int = None
    ) -> dict:
        try:
            updates = {}
            if folder_id is not None:
                updates["folder_id"] = folder_id if folder_id != 0 else None
            if filename is not None:
                updates["filename"] = filename           # what the UI displays
                updates["original_filename"] = filename  # keep both in sync
            if not updates:
                return self._err("Nothing to update")

            res = (
                self.client.table("images")
                .update(updates)
                .eq("id", image_id)
                .execute()
            )

            # Empty res.data means RLS silently blocked the update
            if not res.data:
                return self._err("Update failed — no rows affected. Check RLS policies.")

            return self._ok(self._sign_single_image_url(res.data[0]))
        except Exception as e:
            return self._err(e)
    
    def update_image(self, image_id: int, filename: str = None, folder_id: int = None) -> dict:
        """Update image filename and/or folder. Alias for move_image_to_folder."""
        return self.move_image_to_folder(image_id, filename=filename, folder_id=folder_id)

    def delete_image(self, image_id: int) -> dict:
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
            return self._ok(self._sign_image_urls(res.data))
        except Exception as e:
            return self._err(e)

    # ------------------------------------------------------------------
    # Translation (delegated to TranslatorClient)
    # ------------------------------------------------------------------

    def translate_image(self, image_bytes: bytes, config: dict = None) -> dict:
        """Delegate image translation to the dedicated TranslatorClient."""
        try:
            return self._translator.translate_image(
                image_bytes, config, token=self.access_token
            )
        except _TokenExpired:
            # Refresh the Supabase session and retry once
            self.client.auth.refresh_session()
            new_token = self.access_token
            if new_token is None:
                raise AuthenticationError("Session could not be refreshed. Please log in again.")
            try:
                return self._translator.translate_image(
                    image_bytes, config, token=new_token, _retry=False
                )
            except (_TokenExpired, httpx.HTTPStatusError):
                raise AuthenticationError("Session expired. Please log in again.")