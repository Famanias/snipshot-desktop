"""
Pydantic schemas for Supabase Edition

User authentication is handled by Supabase Auth directly.
These schemas are for image CRUD operations.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# Auth schemas (for Supabase Auth responses)
class AuthResponse(BaseModel):
    """Response from Supabase Auth"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user: Optional[dict] = None


class UserProfile(BaseModel):
    """User profile from Supabase"""
    id: str
    email: Optional[str] = None
    created_at: Optional[str] = None


# Folder schemas
class FolderCreate(BaseModel):
    """Schema for creating a folder"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class FolderResponse(BaseModel):
    """Folder response schema"""
    id: int
    user_id: str
    name: str
    description: Optional[str]
    image_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class FolderListResponse(BaseModel):
    """List of folders"""
    folders: List[FolderResponse]


# Image schemas
class ImageCreate(BaseModel):
    """Schema for saving an image (uploaded to Supabase Storage)"""
    original_filename: Optional[str] = None
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    folder_id: Optional[int] = None


class ImageUpdate(BaseModel):
    """Schema for updating image metadata"""
    original_filename: Optional[str] = None
    folder_id: Optional[int] = None
    description: Optional[str] = None


class ImageResponse(BaseModel):
    """Image metadata response"""
    id: int
    storage_path: str
    public_url: str
    filename: str
    original_filename: Optional[str]
    source_language: Optional[str]
    target_language: Optional[str]
    file_size: Optional[int]
    folder_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class ImageListResponse(BaseModel):
    """Paginated list of images"""
    images: List[ImageResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ImageUploadResponse(BaseModel):
    """Response after uploading an image"""
    id: int
    storage_path: str
    public_url: str
    message: str = "Image uploaded successfully"


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
