"""
SnipShot Desktop - Local File Storage

Manages image files on the local filesystem for local mode.
"""

import os
import time

from config import LOCAL_STORAGE_DIR

IMAGES_DIR = os.path.join(LOCAL_STORAGE_DIR, "images")


def init_storage():
    """Ensure the local images directory exists."""
    os.makedirs(IMAGES_DIR, exist_ok=True)


def save_file(data: bytes, filename: str) -> str:
    """Save image bytes to local storage. Returns the full file path."""
    init_storage()
    safe_name = f"{int(time.time())}_{filename}"
    path = os.path.join(IMAGES_DIR, safe_name)
    with open(path, "wb") as f:
        f.write(data)
    return path


def delete_file(path: str):
    """Delete a file from local storage."""
    if os.path.isfile(path):
        os.remove(path)


def get_file_size(path: str) -> int:
    """Return file size in bytes, or 0 if missing."""
    if os.path.isfile(path):
        return os.path.getsize(path)
    return 0
