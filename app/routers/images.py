from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from app.services import StorageService, DatabaseService
from app.models import ImageMetadata, ImageCreate, ImageFilter
from typing import List, Optional
import uuid
from datetime import datetime

router = APIRouter(prefix="/images", tags=["images"])

# Dependency Injection for services
async def get_storage_service():
    return StorageService()

async def get_db_service():
    return DatabaseService()

@router.post("/", response_model=ImageMetadata)
async def upload_image(
    file: UploadFile = File(...),
    tags: Optional[List[str]] = Query(default=[]),
    description: Optional[str] = Form(default=None),
    storage: StorageService = Depends(get_storage_service),
    db: DatabaseService = Depends(get_db_service)
):
    # Generate unique ID and filename
    image_id = str(uuid.uuid4())
    extension = file.filename.split(".")[-1]
    unique_filename = f"{image_id}.{extension}"
    
    # Upload to S3
    try:
        await storage.upload_file(file, unique_filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Create Metadata
    metadata = ImageMetadata(
        id=image_id,
        filename=unique_filename,
        size=file.size if file.size else 0, # Size might be 0 if streamed, but for this simple ex ok
        content_type=file.content_type,
        created_at=datetime.utcnow().isoformat(),
        tags=tags,
        description=description
    )
    
    # Save to DynamoDB
    await db.save_metadata(metadata)
    
    # Generate download URL for response
    metadata.download_url = await storage.generate_presigned_url(unique_filename)
    # Upload URL not really needed here, but can include if required.
    
    return metadata

@router.get("/", response_model=List[ImageMetadata])
async def list_images(
    filename: Optional[str] = Query(None, description="Filter by partial filename"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    db: DatabaseService = Depends(get_db_service),
    storage: StorageService = Depends(get_storage_service)
):
    valid_tag = tag if tag and tag.strip() else None
    valid_filename = filename if filename and filename.strip() else None
    
    filters = ImageFilter(filename=valid_filename, tag=valid_tag)
    images = await db.list_images(filters)
    
    # Populate download URLs for each image
    for img in images:
        img.download_url = await storage.generate_presigned_url(img.filename)
        
    return images

@router.get("/{image_id}", response_model=ImageMetadata)
async def get_image(
    image_id: str,
    db: DatabaseService = Depends(get_db_service),
    storage: StorageService = Depends(get_storage_service)
):
    image = await db.get_metadata(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
        
    image.download_url = await storage.generate_presigned_url(image.filename)
    return image

@router.delete("/{image_id}")
async def delete_image(
    image_id: str,
    db: DatabaseService = Depends(get_db_service),
    storage: StorageService = Depends(get_storage_service)
):
    image = await db.get_metadata(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
        
    # Delete from S3
    await storage.delete_file(image.filename)
    
    # Delete from DynamoDB
    await db.delete_metadata(image_id)
    
    return {"message": "Image deleted successfully"}
