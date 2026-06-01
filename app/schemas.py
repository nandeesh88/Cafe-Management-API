from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models import OrderStatus, DiscountType


# ─── Order Schemas ────────────────────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., gt=0)


class OrderItemOut(BaseModel):
    id: int
    item_name: str
    quantity: int
    unit_price: float

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=100)
    items: List[OrderItemCreate] = Field(..., min_items=1)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderOut(BaseModel):
    id: int
    customer_name: str
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemOut]

    class Config:
        from_attributes = True


# ─── Billing Schemas ──────────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    tax_rate: float = Field(default=0.0, ge=0, le=100, description="Tax percentage (0-100)")
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[float] = Field(default=0.0, ge=0)

    @validator("discount_value", always=True)
    def validate_discount(cls, v, values):
        discount_type = values.get("discount_type")
        if discount_type == DiscountType.percentage and v and v > 100:
            raise ValueError("Percentage discount cannot exceed 100")
        return v or 0.0


class InvoiceOut(BaseModel):
    id: int
    order_id: int
    subtotal: float
    discount_type: Optional[DiscountType]
    discount_value: Optional[float]
    discount_amount: float
    tax_rate: float
    tax_amount: float
    total: float
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Inventory Schemas ────────────────────────────────────────────────────────

class InventoryItemOut(BaseModel):
    id: int
    item_name: str
    quantity: int
    ai_identified: str
    image_filename: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InventoryItemUpdate(BaseModel):
    item_name: Optional[str] = Field(None, min_length=1, max_length=100)
    quantity: Optional[int] = Field(None, ge=0)


class AIScanResponse(BaseModel):
    identified_item: str
    confidence_note: str
    inventory_item: InventoryItemOut
