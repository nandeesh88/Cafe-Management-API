import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path

from app.database import get_db
from app.models import InventoryItem
from app.schemas import InventoryItemOut, InventoryItemUpdate, AIScanResponse
from app.services.ai_vision import identify_item_from_image

router = APIRouter(prefix="/inventory", tags=["Inventory"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/scan", response_model=AIScanResponse, status_code=status.HTTP_201_CREATED)
async def scan_and_add_to_inventory(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type: {file.content_type}. Allowed: {', '.join(ALLOWED_TYPES)}"
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB")

    ext = Path(file.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / filename

    with open(filepath, "wb") as f:
        f.write(contents)

    try:
        result = identify_item_from_image(str(filepath), media_type=file.content_type)
    except ValueError as e:
        os.remove(filepath)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        os.remove(filepath)
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")

    item = InventoryItem(
        item_name=result["item_name"],
        quantity=1,
        ai_identified="Y",
        raw_ai_response=result.get("raw_response", ""),
        image_filename=filename,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return AIScanResponse(
        identified_item=result["item_name"],
        confidence_note=result["confidence_note"],
        inventory_item=item,
    )


@router.get("/", response_model=List[InventoryItemOut])
def list_inventory(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(InventoryItem).order_by(InventoryItem.updated_at.desc()).offset(skip).limit(limit).all()


@router.get("/{item_id}", response_model=InventoryItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Inventory item {item_id} not found")
    return item


@router.patch("/{item_id}", response_model=InventoryItemOut)
def update_item(item_id: int, payload: InventoryItemUpdate, db: Session = Depends(get_db)):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Inventory item {item_id} not found")

    if payload.item_name is not None:
        item.item_name = payload.item_name
    if payload.quantity is not None:
        item.quantity = payload.quantity

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Inventory item {item_id} not found")

    if item.image_filename:
        img_path = UPLOAD_DIR / item.image_filename
        if img_path.exists():
            os.remove(img_path)

    db.delete(item)
    db.commit()
