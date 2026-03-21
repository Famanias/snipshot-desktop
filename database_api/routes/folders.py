"""
Folder management routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db, Folder, Image
from auth import get_current_user_id
from schemas import FolderCreate, FolderResponse, FolderListResponse, MessageResponse

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get("", response_model=FolderListResponse)
async def list_folders(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """List all folders for current user"""
    counts_subquery = (
        select(
            Image.folder_id.label("folder_id"),
            func.count(Image.id).label("image_count")
        )
        .where(
            Image.user_id == user_id,
            Image.folder_id.is_not(None)
        )
        .group_by(Image.folder_id)
        .subquery()
    )

    result = await db.execute(
        select(
            Folder,
            func.coalesce(counts_subquery.c.image_count, 0).label("image_count")
        )
        .outerjoin(counts_subquery, counts_subquery.c.folder_id == Folder.id)
        .where(Folder.user_id == user_id)
        .order_by(Folder.name)
    )
    folders = []
    for folder, image_count in result.all():
        folder_data = FolderResponse.model_validate(folder).model_dump()
        folder_data["image_count"] = int(image_count or 0)
        folders.append(FolderResponse(**folder_data))

    return FolderListResponse(
        folders=folders
    )


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder: FolderCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new folder.
    """
    new_folder = Folder(
        user_id=user_id,
        name=folder.name,
        description=folder.description
    )
    db.add(new_folder)
    await db.commit()
    await db.refresh(new_folder)
    
    return FolderResponse.model_validate(new_folder)


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(
    folder_id: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get single folder details"""
    result = await db.execute(
        select(Folder).where(
            Folder.id == folder_id,
            Folder.user_id == user_id
        )
    )
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
        
    return FolderResponse.model_validate(folder)


@router.put("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: int,
    update_data: FolderCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update folder"""
    result = await db.execute(
        select(Folder).where(
            Folder.id == folder_id,
            Folder.user_id == user_id
        )
    )
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
        
    folder.name = update_data.name
    folder.description = update_data.description
    
    await db.commit()
    await db.refresh(folder)
    
    return FolderResponse.model_validate(folder)


@router.delete("/{folder_id}", response_model=MessageResponse)
async def delete_folder(
    folder_id: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete folder"""
    result = await db.execute(
        select(Folder).where(
            Folder.id == folder_id,
            Folder.user_id == user_id
        )
    )
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
        
    await db.delete(folder)
    await db.commit()
    
    return MessageResponse(message="Folder deleted successfully")
