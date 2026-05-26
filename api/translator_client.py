"""
SnipShot Desktop - Translator Client

Dedicated client for image translation and OCR operations.
Uses the translator backend hosted on Microsoft Azure.

This client is intentionally decoupled from Supabase authentication
and storage to maintain a clean separation of concerns.
"""

import httpx
import json
from typing import Any, Optional, Dict

from config import TRANSLATOR_URL, DEFAULT_TRANSLATION_CONFIG


class _TokenExpired(Exception):
    """Sentinel raised when the backend returns 401, triggering a refresh-and-retry."""


class TranslatorClient:
    """Dedicated client for translation, OCR, and image inference operations.
    
    This client handles:
    - Image translation (text detection, translation, inpainting)
    - OCR (Optical Character Recognition)
    - Manga translation
    - General image inference/processing
    
    All requests are sent to the translator backend (Microsoft Azure).
    """

    def __init__(self, translator_url: str = None):
        """Initialize the translator client.
        
        Args:
            translator_url: Base URL for the translator API. 
                          Defaults to TRANSLATOR_URL from config.
        """
        self.translator_url = translator_url or TRANSLATOR_URL

    def translate_image(
        self, 
        image_bytes: bytes, 
        config: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
        _retry: bool = True
    ) -> dict:
        """Translate text in an image.
        
        Sends the image to the translator backend for:
        1. Text detection
        2. Text translation
        3. Inpainting (optional background restoration)
        
        Args:
            image_bytes: Raw image bytes (PNG, JPG, etc.)
            config: Translation config dict with optional keys:
                   - detector: Detection settings (detection_size, box_threshold)
                   - translator: Translation settings (target_lang)
                   - inpainter: Inpainting settings (inpainter, inpainting_size)
            token: Supabase JWT access token
            _retry: Whether to retry once on 401
        
        Returns:
            Response dict with keys:
            - success: bool
            - data: dict with "image_bytes" key containing translated image
            - error: Optional error message if success=False
        """
        if config is None:
            config = DEFAULT_TRANSLATION_CONFIG

        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

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
                    data=data,
                    headers=headers
                )
                if response.status_code == 401 and _retry:
                    raise _TokenExpired()
            except _TokenExpired:
                raise
            except httpx.RequestError as e:
                return {
                    "success": False,
                    "error": (
                        f"Could not reach Translator API at {self.translator_url}. "
                        f"Details: {str(e)}"
                    )
                }

            if response.status_code == 200:
                # Translator backend returns raw image bytes directly
                return {"success": True, "data": {"image_bytes": response.content}}

            if response.status_code == 404:
                return {
                    "success": False,
                    "error": (
                        f"Translator endpoint not found at {translate_url}. "
                        "Check that the backend URL is correct."
                    )
                }

            return {
                "success": False,
                "error": f"Translation failed ({response.status_code}): {response.text}"
            }

    def ocr_image(
        self,
        image_bytes: bytes,
        language: str = "auto"
    ) -> dict:
        """Perform OCR (Optical Character Recognition) on an image.
        
        Args:
            image_bytes: Raw image bytes
            language: Language for OCR (default: auto-detect)
        
        Returns:
            Response dict with extracted text and bounding boxes
        """
        with httpx.Client(timeout=60.0) as client:
            files = {
                "image": ("snip.png", image_bytes, "image/png"),
            }
            data = {
                "language": language
            }

            ocr_url = f"{self.translator_url}/ocr"

            try:
                response = client.post(
                    ocr_url,
                    files=files,
                    data=data
                )
            except httpx.RequestError as e:
                return {
                    "success": False,
                    "error": f"Could not reach Translator API: {str(e)}"
                }

            if response.status_code == 200:
                return {"success": True, "data": response.json()}

            return {
                "success": False,
                "error": f"OCR failed ({response.status_code}): {response.text}"
            }

    def manga_translate(
        self,
        image_bytes: bytes,
        target_lang: str = "ENG"
    ) -> dict:
        """Translate manga (Japanese comics) text in an image.
        
        Specialized translation for manga with optimized detection
        and inpainting for speech bubbles.
        
        Args:
            image_bytes: Raw image bytes
            target_lang: Target language code (default: ENG)
        
        Returns:
            Response dict with translated image
        """
        with httpx.Client(timeout=180.0) as client:
            files = {
                "image": ("manga.png", image_bytes, "image/png"),
            }
            data = {
                "target_lang": target_lang
            }

            manga_url = f"{self.translator_url}/translate/manga"

            try:
                response = client.post(
                    manga_url,
                    files=files,
                    data=data
                )
            except httpx.RequestError as e:
                return {
                    "success": False,
                    "error": f"Could not reach Translator API: {str(e)}"
                }

            if response.status_code == 200:
                return {"success": True, "data": {"image_bytes": response.content}}

            return {
                "success": False,
                "error": f"Manga translation failed ({response.status_code}): {response.text}"
            }
