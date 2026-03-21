"""
Image routes - Supabase Storage

Handles image upload, retrieval, and deletion using Supabase Storage.
Image metadata is stored in PostgreSQL via SQLAlchemy.
"""

import os
import time
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from config import get_supabase, STORAGE_BUCKET
from database import get_db, Image, Folder
from auth import get_current_user_id
from schemas import ImageResponse, ImageListResponse, ImageUploadResponse, MessageResponse, ImageUpdate

router = APIRouter(prefix="/images", tags=["images"])


@router.post("", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    original_filename: Optional[str] = Form(None),
    source_language: Optional[str] = Form(None),
    target_language: Optional[str] = Form(None),
    folder_id: Optional[int] = Form(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a translated image to Supabase Storage.
    
    This endpoint:
    1. Uploads image to Supabase Storage
    2. Saves metadata to PostgreSQL
    3. Returns the public URL
    """
    try:
        supabase = get_supabase()
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Generate unique path
        timestamp = int(time.time() * 1000)
        filename = original_filename or file.filename or f"image_{timestamp}.png"
        storage_path = f"{user_id}/{timestamp}_{filename}"
        
        # Upload to Supabase Storage
        result = supabase.storage.from_(STORAGE_BUCKET).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": file.content_type or "image/png"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)
        
        # Save metadata to database
        new_image = Image(
            user_id=user_id,
            storage_path=storage_path,
            public_url=public_url,
            filename=filename,
            original_filename=filename,
            source_language=source_language,
            target_language=target_language,
            file_size=file_size,
            folder_id=folder_id
        )
        db.add(new_image)
        await db.commit()
        await db.refresh(new_image)
        
        return ImageUploadResponse(
            id=new_image.id,
            storage_path=storage_path,
            public_url=public_url
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/from-url", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def save_image_from_url(
    image_url: str = Form(...),
    original_filename: Optional[str] = Form(None),
    source_language: Optional[str] = Form(None),
    target_language: Optional[str] = Form(None),
    folder_id: Optional[int] = Form(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Save an image from URL (e.g., from VM Translator API).
    
    Downloads the image and uploads to Supabase Storage.
    Use this after getting the translated image URL from the VM.
    """
    import httpx
    
    try:
        # Download image from URL
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Could not download image from URL")
            content = response.content
        
        file_size = len(content)
        
        supabase = get_supabase()
        
        # Generate unique path
        timestamp = int(time.time() * 1000)
        filename = original_filename or f"translated_{timestamp}.png"
        storage_path = f"{user_id}/{timestamp}_{filename}"
        
        # Upload to Supabase Storage
        supabase.storage.from_(STORAGE_BUCKET).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": "image/png"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)
        
        # Save metadata to database
        new_image = Image(
            user_id=user_id,
            storage_path=storage_path,
            public_url=public_url,
            filename=filename,
            original_filename=filename,
            source_language=source_language,
            target_language=target_language,
            file_size=file_size,
            folder_id=folder_id
        )
        db.add(new_image)
        await db.commit()
        await db.refresh(new_image)
        
        return ImageUploadResponse(
            id=new_image.id,
            storage_path=storage_path,
            public_url=public_url,
            message="Image saved from URL successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")


@router.get("", response_model=ImageListResponse)
async def list_images(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    folder_id: Optional[int] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """List all images for current user"""
    # Base query
    query = select(Image).where(Image.user_id == user_id)
    count_query = select(func.count(Image.id)).where(Image.user_id == user_id)
    
    if folder_id is not None:
        if folder_id == 0:
            # "Unfiled" - checking for NULL can be tricky depending on how requests are sent
            # Assuming 0 requests unfiled images
            query = query.where(Image.folder_id == None)
            count_query = count_query.where(Image.folder_id == None)
        else:
            query = query.where(Image.folder_id == folder_id)
            count_query = count_query.where(Image.folder_id == folder_id)
            
    # Count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Paginate
    offset = (page - 1) * per_page
    pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    # Get images
    result = await db.execute(
        query
        .order_by(Image.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    images = result.scalars().all()
    
    return ImageListResponse(
        images=[ImageResponse.model_validate(img) for img in images],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific image"""
    result = await db.execute(
        select(Image).where(Image.id == image_id, Image.user_id == user_id)
    )
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    return image


@router.put("/{image_id}", response_model=ImageResponse)
async def update_image(
    image_id: int,
    image_update: ImageUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update image metadata (e.g., move to folder)"""
    result = await db.execute(
        select(Image).where(Image.id == image_id, Image.user_id == user_id)
    )
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    if image_update.folder_id is not None:
        # Check if folder exists and belongs to user if folder_id != 0 (0 might mean unfiled in some logic but here we likely mean valid folder ID or None)
        # Assuming folder_id=0 means remove from folder (unfile)
        if image_update.folder_id == 0:
            image.folder_id = None
        else:
            # Verify folder exists
            folder_result = await db.execute(
                select(Folder).where(Folder.id == image_update.folder_id, Folder.user_id == user_id)
            )
            if not folder_result.scalar_one_or_none():
                raise HTTPException(status_code=404, detail="Folder not found")
            image.folder_id = image_update.folder_id
            
    if image_update.original_filename is not None:
        image.filename = image_update.original_filename
        image.original_filename = image_update.original_filename
        
    await db.commit()
    await db.refresh(image)
    return image


@router.delete("/{image_id}", response_model=MessageResponse)
async def delete_image(
    image_id: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete an image (from Supabase Storage and database)"""
    result = await db.execute(
        select(Image).where(Image.id == image_id, Image.user_id == user_id)
    )
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Delete from Supabase Storage
    try:
        supabase = get_supabase()
        supabase.storage.from_(STORAGE_BUCKET).remove([image.storage_path])
    except Exception as e:
        print(f"Warning: Could not delete from Supabase Storage: {e}")
    
    # Delete from database
    await db.delete(image)
    await db.commit()
    
    return MessageResponse(message="Image deleted successfully")


@router.delete("", response_model=MessageResponse)
async def delete_all_images(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete all images for current user"""
    result = await db.execute(
        select(Image).where(Image.user_id == user_id)
    )
    images = result.scalars().all()
    
    if not images:
        return MessageResponse(message="No images to delete")
    
    # Delete from Supabase Storage
    try:
        supabase = get_supabase()
        storage_paths = [img.storage_path for img in images]
        supabase.storage.from_(STORAGE_BUCKET).remove(storage_paths)
    except Exception as e:
        print(f"Warning: Could not delete from Supabase Storage: {e}")
    
    # Delete from database
    for image in images:
        await db.delete(image)
    await db.commit()
    
    return MessageResponse(message=f"Deleted {len(images)} images")
