"""
Database models for SnipShot Database API (Supabase Edition)

User management is handled by Supabase Auth.
We only store image metadata here.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Folder(Base):
    """
    Folder model for organizing images.
    """
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    images = relationship("Image", back_populates="folder")


class Image(Base):
    """
    Image metadata model.
    
    user_id is the Supabase Auth user UUID (string, not integer).
    Actual image files are stored in Supabase Storage.
    """
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)  # Supabase UUID
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    
    # Supabase Storage info
    storage_path = Column(Text, nullable=False)  # Path in Supabase Storage
    public_url = Column(Text, nullable=False)    # Public URL for the image
    
    # Metadata
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    source_language = Column(String(10), nullable=True)
    target_language = Column(String(10), nullable=True)
    file_size = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    folder = relationship("Folder", back_populates="images")
