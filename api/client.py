"""
DEPRECIATTED - This file is no longer used in the current architecture. The API client logic has been moved to the backend service, and the desktop app now communicates with it directly for all operations.
SnipShot Desktop - API Client 

Handles all communication with the backend services:
- Database API (users, folders, images)
- Translator API (image translation)
"""

import httpx
import json
from typing import Optional, Dict, Any, List
from config import API_BASE_URL, TRANSLATOR_URL, DEFAULT_TRANSLATION_CONFIG


class APIClient:
    """HTTP client for SnipShot backend APIs"""
    
    def __init__(self):
        self.base_url = API_BASE_URL
        self.translator_url = TRANSLATOR_URL
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user: Optional[Dict] = None
        
    @property
    def headers(self) -> Dict[str, str]:
        """Get headers with auth token"""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is logged in"""
        return self.access_token is not None
    
    # ==================== Auth ====================
    
    def register(self, email: str, password: str) -> Dict[str, Any]:
        """Register a new user"""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url}/users/register",
                json={"email": email, "password": password}
            )
            
            if response.status_code == 201:
                data = response.json()
                if data.get("access_token"):
                    self._set_auth(data)
                return {"success": True, "data": data}
            else:
                return {"success": False, "error": response.json().get("detail", "Registration failed")}
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login user"""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url}/users/login",
                json={"email": email, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                self._set_auth(data)
                return {"success": True, "data": data}
            else:
                error = response.json().get("detail", "Login failed")
                return {"success": False, "error": error}
    
    def logout(self):
        """Logout user"""
        self.access_token = None
        self.refresh_token = None
        self.user = None
    
    def get_profile(self) -> Dict[str, Any]:
        """Get current user profile"""
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{self.base_url}/users/me",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": "Failed to get profile"}
    
    def _set_auth(self, data: Dict):
        """Set auth tokens from response"""
        self.access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token")
        self.user = data.get("user")
    
    # ==================== Folders ====================
    
    def get_folders(self) -> Dict[str, Any]:
        """Get all folders for current user"""
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{self.base_url}/folders",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"Failed to get folders: {response.status_code} - {response.text}"}
    
    def create_folder(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new folder"""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url}/folders",
                headers=self.headers,
                json={"name": name, "description": description}
            )
            
            if response.status_code == 201:
                return {"success": True, "data": response.json()}
            else:
                error = response.json().get("detail", "Failed to create folder")
                return {"success": False, "error": error}
    
    def get_folder(self, folder_id: int) -> Dict[str, Any]:
        """Get folder with images"""
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{self.base_url}/folders/{folder_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": "Folder not found"}
    
    def update_folder(self, folder_id: int, name: str = None, description: str = None) -> Dict[str, Any]:
        """Update folder"""
        data = {}
        if name:
            data["name"] = name
        if description is not None:
            data["description"] = description
            
        with httpx.Client(timeout=30.0) as client:
            response = client.put(
                f"{self.base_url}/folders/{folder_id}",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                error = response.json().get("detail", "Failed to update folder")
                return {"success": False, "error": error}
    
    def delete_folder(self, folder_id: int, delete_images: bool = False) -> Dict[str, Any]:
        """Delete folder"""
        with httpx.Client(timeout=30.0) as client:
            response = client.delete(
                f"{self.base_url}/folders/{folder_id}",
                headers=self.headers,
                params={"delete_images": delete_images}
            )
            
            if response.status_code in (200, 204):
                data = response.json() if response.content else {}
                return {"success": True, "data": data}
            else:
                return {"success": False, "error": "Failed to delete folder"}
    
    # ==================== Images ====================
    
    def get_images(self, folder_id: int = None, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Get images, optionally filtered by folder"""
        params = {"page": page, "per_page": per_page}
        if folder_id is not None:
            params["folder_id"] = folder_id
            
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{self.base_url}/images",
                headers=self.headers,
                params=params
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                 return {"success": False, "error": f"Failed to get images: {response.status_code} - {response.text}"}
    
    def get_image(self, image_id: int) -> Dict[str, Any]:
        """Get single image details"""
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{self.base_url}/images/{image_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": "Image not found"}
    
    def save_image_from_url(
        self, 
        image_url: str, 
        filename: str, 
        folder_id: int = None,
        source_language: str = None,
        target_language: str = None
    ) -> Dict[str, Any]:
        """Save translated image from URL to user's account"""
        data = {
            "image_url": image_url,
            "original_filename": filename
        }
        if folder_id is not None:
            data["folder_id"] = str(folder_id)
        if source_language:
            data["source_language"] = source_language
        if target_language:
            data["target_language"] = target_language
            
        with httpx.Client(timeout=60.0) as client:
            # Use form data, not JSON
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
                
            response = client.post(
                f"{self.base_url}/images/from-url",
                headers=headers,
                data=data  # form data
            )
            
            if response.status_code == 201:
                return {"success": True, "data": response.json()}
            else:
                error = response.json().get("detail", "Failed to save image")
                return {"success": False, "error": error}
    
    def save_image_from_bytes(
        self,
        image_bytes: bytes,
        filename: str,
        folder_id: int = None,
        source_language: str = None,
        target_language: str = None
    ) -> Dict[str, Any]:
        """Upload translated image bytes directly to user's account."""
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        files = {
            "image": (filename, image_bytes, "image/png"),
        }
        data = {}
        if folder_id is not None:
            data["folder_id"] = str(folder_id)
        if source_language:
            data["source_language"] = source_language
        if target_language:
            data["target_language"] = target_language

        with httpx.Client(timeout=60.0) as client:
            try:
                response = client.post(
                    f"{self.base_url}/images/upload",
                    headers=headers,
                    files=files,
                    data=data
                )
            except httpx.RequestError as e:
                return {"success": False, "error": f"Upload failed: {str(e)}"}

            if response.status_code == 201:
                return {"success": True, "data": response.json()}
            else:
                error = response.json().get("detail", "Failed to save image")
                return {"success": False, "error": error}
    
    def update_image(self, image_id: int, filename: str = None, folder_id: int = None) -> Dict[str, Any]:
        """Update image (rename or move)"""
        data = {}
        if filename:
            data["original_filename"] = filename
        if folder_id is not None:
            data["folder_id"] = folder_id
            
        with httpx.Client(timeout=30.0) as client:
            response = client.put(
                f"{self.base_url}/images/{image_id}",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": "Failed to update image"}
    
    def move_image_to_folder(self, image_id: int, filename: str = None, folder_id: int = None) -> Dict[str, Any]:
        """Update image folder and/or filename. Alias for update_image."""
        f_id = folder_id if folder_id != 0 else None
        return self.update_image(image_id, filename=filename, folder_id=f_id)

    def delete_image(self, image_id: int) -> Dict[str, Any]:
        """Delete image"""
        with httpx.Client(timeout=30.0) as client:
            response = client.delete(
                f"{self.base_url}/images/{image_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return {"success": True}
            else:
                return {"success": False, "error": "Failed to delete image"}
    
    # ==================== Translation ====================
    
    def translate_image(self, image_bytes: bytes, config: Dict = None) -> Dict[str, Any]:
        """
        Send image to translator API.
        Returns the translated image as raw bytes.
        """
        if config is None:
            config = DEFAULT_TRANSLATION_CONFIG

        with httpx.Client(timeout=180.0) as client:  # 3 min timeout for translation
            files = {
                "image": ("snip.png", image_bytes, "image/png"),
            }
            data = {
                "config": json.dumps(config)
            }

            translate_url = f"{self.translator_url}/translate/raw"

            try:
                response = client.post(
                    translate_url,
                    files=files,
                    data=data
                )
            except httpx.RequestError as e:
                return {
                    "success": False,
                    "error": (
                        f"Could not reach Translator API at {self.translator_url}. "
                        f"Details: {str(e)}"
                    )
                }

            if response.status_code == 200:
                # New backend returns raw image bytes directly
                return {"success": True, "data": {"image_bytes": response.content}}

            if response.status_code == 404:
                return {
                    "success": False,
                    "error": (
                        f"Translator endpoint not found at {translate_url}. "
                        "Check that the backend URL is correct."
                    )
                }

            return {"success": False, "error": f"Translation failed ({response.status_code}): {response.text}"}


# Global API client instance
api_client = APIClient()
