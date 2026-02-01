from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ImageMetadata(BaseModel):
    id: str
    filename: str
    upload_url: Optional[str] = None # Presigned URL for upload (optional in response)
    download_url: Optional[str] = None
    size: int
    content_type: str
    created_at: str
    tags: List[str] = []
    description: Optional[str] = None

class ImageCreate(BaseModel):
    tags: List[str] = []
    description: Optional[str] = None

class ImageFilter(BaseModel):
    filename: Optional[str] = None
    tag: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
