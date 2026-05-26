"""
SnipShot Desktop - Local API Client

Mirrors the interface of api/client.py but stores everything locally
using SQLite for metadata and the filesystem for image files.
"""

import math
import json
import time

import httpx
from typing import Optional, Dict, Any

from config import LOCAL_TRANSLATOR_URL, DEFAULT_TRANSLATION_CONFIG
from . import database as db
from . import storage


class LocalAPIClient:
    """API client that stores everything locally (SQLite + filesystem)."""

    def __init__(self, translator_url: Optional[str] = None):
        self.access_token = "local"
        self.refresh_token = None
        self.user = {"email": "Local User", "id": "local"}
        self.translator_url = translator_url or LOCAL_TRANSLATOR_URL
        db.init_db()
        storage.init_storage()

    @property
    def is_authenticated(self) -> bool:
        return True

    # ==================== Auth (no-ops) ====================

    def register(self, email: str, password: str) -> Dict[str, Any]:
        return {"success": True, "data": {}}

    def login(self, email: str, password: str) -> Dict[str, Any]:
        return {"success": True, "data": {}}

    def logout(self):
        pass

    def get_profile(self) -> Dict[str, Any]:
        return {"success": True, "data": {"email": "Local User", "id": "local"}}

    # ==================== Folders ====================

    def get_folders(self) -> Dict[str, Any]:
        conn = db.get_connection()
        try:
            rows = conn.execute(
                """
                SELECT f.*, COUNT(i.id) as image_count
                FROM folders f
                LEFT JOIN images i ON i.folder_id = f.id
                GROUP BY f.id
                ORDER BY f.created_at DESC
                """
            ).fetchall()
            folders = [dict(r) for r in rows]
            return {"success": True, "data": folders}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def create_folder(self, name: str, description: str = "") -> Dict[str, Any]:
        conn = db.get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO folders (name, description) VALUES (?, ?)",
                (name, description),
            )
            conn.commit()
            row = conn.execute(
                "SELECT *, 0 as image_count FROM folders WHERE id = ?",
                (cur.lastrowid,),
            ).fetchone()
            return {"success": True, "data": dict(row)}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def get_folder(self, folder_id: int) -> Dict[str, Any]:
        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM folders WHERE id = ?", (folder_id,)
            ).fetchone()
            if row:
                return {"success": True, "data": dict(row)}
            return {"success": False, "error": "Folder not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def update_folder(
        self, folder_id: int, name: str = None, description: str = None
    ) -> Dict[str, Any]:
        conn = db.get_connection()
        try:
            updates = []
            params = []
            if name:
                updates.append("name = ?")
                params.append(name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if not updates:
                return {"success": True, "data": {}}
            params.append(folder_id)
            conn.execute(
                f"UPDATE folders SET {', '.join(updates)} WHERE id = ?", params
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM folders WHERE id = ?", (folder_id,)
            ).fetchone()
            return {"success": True, "data": dict(row) if row else {}}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def delete_folder(
        self, folder_id: int, delete_images: bool = False
    ) -> Dict[str, Any]:
        conn = db.get_connection()
        try:
            if delete_images:
                images = conn.execute(
                    "SELECT storage_path FROM images WHERE folder_id = ?",
                    (folder_id,),
                ).fetchall()
                for img in images:
                    storage.delete_file(img["storage_path"])
                conn.execute(
                    "DELETE FROM images WHERE folder_id = ?", (folder_id,)
                )
            conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
            conn.commit()
            return {"success": True, "data": {}}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    # ==================== Images ====================

    def get_images(
        self, folder_id: int = None, page: int = 1, per_page: int = 50, unfiled_only: bool = False
    ) -> Dict[str, Any]:
        conn = db.get_connection()
        try:
            if unfiled_only:
                where = "WHERE folder_id IS NULL"
                params: list = []
            elif folder_id == 0:
                where = "WHERE folder_id IS NULL"
                params: list = []
            elif folder_id is not None:
                where = "WHERE folder_id = ?"
                params = [folder_id]
            else:
                where = ""
                params = []

            total = conn.execute(
                f"SELECT COUNT(*) FROM images {where}", params
            ).fetchone()[0]

            offset = (page - 1) * per_page
            rows = conn.execute(
                f"SELECT * FROM images {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                params + [per_page, offset],
            ).fetchall()

            images = [dict(r) for r in rows]
            pages = math.ceil(total / per_page) if per_page > 0 else 1

            return {
                "success": True,
                "data": {
                    "images": images,
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "pages": pages,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def get_image(self, image_id: int) -> Dict[str, Any]:
        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM images WHERE id = ?", (image_id,)
            ).fetchone()
            if row:
                return {"success": True, "data": dict(row)}
            return {"success": False, "error": "Image not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def get_recent_images(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Fetch the most recently created images across all folders."""
        conn = db.get_connection()
        try:
            offset = (page - 1) * per_page
            rows = conn.execute(
                "SELECT * FROM images ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (per_page, offset),
            ).fetchall()
            images = [dict(r) for r in rows]
            return {"success": True, "data": images}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def save_image_from_url(
        self,
        image_url: str,
        filename: str,
        folder_id: int = None,
        source_language: str = None,
        target_language: str = None,
    ) -> Dict[str, Any]:
        """Download image from URL and save locally."""
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                response = client.get(image_url)
                response.raise_for_status()
                image_data = response.content

            file_path = storage.save_file(image_data, filename)
            file_size = len(image_data)

            conn = db.get_connection()
            try:
                cur = conn.execute(
                    """INSERT INTO images
                       (folder_id, storage_path, public_url, filename,
                        original_filename, source_language, target_language, file_size)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        folder_id if folder_id else None,
                        file_path,
                        file_path,  # public_url = local path
                        filename,
                        filename,
                        source_language or "",
                        target_language or "",
                        file_size,
                    ),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM images WHERE id = ?", (cur.lastrowid,)
                ).fetchone()
                return {"success": True, "data": dict(row)}
            finally:
                conn.close()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_image_from_bytes(
        self,
        image_bytes: bytes,
        filename: str,
        folder_id: int = None,
        source_language: str = None,
        target_language: str = None,
    ) -> Dict[str, Any]:
        """Save image bytes directly to local storage."""
        try:
            file_path = storage.save_file(image_bytes, filename)
            file_size = len(image_bytes)

            conn = db.get_connection()
            try:
                cur = conn.execute(
                    """INSERT INTO images
                       (folder_id, storage_path, public_url, filename,
                        original_filename, source_language, target_language, file_size)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        folder_id if folder_id else None,
                        file_path,
                        file_path,  # public_url = local path
                        filename,
                        filename,
                        source_language or "",
                        target_language or "",
                        file_size,
                    ),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM images WHERE id = ?", (cur.lastrowid,)
                ).fetchone()
                return {"success": True, "data": dict(row)}
            finally:
                conn.close()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_image(
        self, image_id: int, filename: str = None, folder_id: int = None
    ) -> Dict[str, Any]:
        conn = db.get_connection()
        try:
            updates = []
            params = []
            if filename:
                updates.append("original_filename = ?")
                params.append(filename)
                updates.append("filename = ?")
                params.append(filename)
            if folder_id is not None:
                updates.append("folder_id = ?")
                params.append(folder_id if folder_id != 0 else None)
            if not updates:
                return {"success": True, "data": {}}
            params.append(image_id)
            conn.execute(
                f"UPDATE images SET {', '.join(updates)} WHERE id = ?", params
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM images WHERE id = ?", (image_id,)
            ).fetchone()
            return {"success": True, "data": dict(row) if row else {}}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def delete_image(self, image_id: int) -> Dict[str, Any]:
        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT storage_path FROM images WHERE id = ?", (image_id,)
            ).fetchone()
            if row:
                storage.delete_file(row["storage_path"])
            conn.execute("DELETE FROM images WHERE id = ?", (image_id,))
            conn.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    # ==================== Translation ====================

    def translate_image(
        self, image_bytes: bytes, config: Dict = None
    ) -> Dict[str, Any]:
        """Send image to translator API (same as online mode)."""
        if config is None:
            config = DEFAULT_TRANSLATION_CONFIG

        with httpx.Client(timeout=180.0) as client:
            files = {"image": ("snip.png", image_bytes, "image/png")}
            data = {"config": json.dumps(config)}
            translate_url = f"{self.translator_url}/translate/raw"

            try:
                response = client.post(translate_url, files=files, data=data)
            except httpx.RequestError as e:
                return {
                    "success": False,
                    "error": (
                        f"Could not reach Translator API at {self.translator_url}. "
                        f"Details: {str(e)}"
                    ),
                }

            if response.status_code == 200:
                # New backend returns raw image bytes directly
                return {"success": True, "data": {"image_bytes": response.content}}

            if response.status_code == 404:
                return {
                    "success": False,
                    "error": f"Translator endpoint not found at {translate_url}.",
                }

            return {
                "success": False,
                "error": f"Translation failed ({response.status_code}): {response.text}",
            }
