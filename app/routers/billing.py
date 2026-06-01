from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Order, Invoice, DiscountType
from app.schemas import InvoiceCreate, InvoiceOut

router = APIRouter(prefix="/billing", tags=["Billing"])


def calculate_invoice(subtotal: float, tax_rate: float, discount_type, discount_value: float):
    discount_amount = 0.0

    if discount_type == DiscountType.percentage:
        discount_amount = round(subtotal * (discount_value / 100), 2)
    elif discount_type == DiscountType.fixed:
        discount_amount = min(discount_value, subtotal)

    after_discount = subtotal - discount_amount
    tax_amount = round(after_discount * (tax_rate / 100), 2)
    total = round(after_discount + tax_amount, 2)

    return discount_amount, tax_amount, total


@router.post("/invoice/{order_id}", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(order_id: int, payload: InvoiceCreate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    existing = db.query(Invoice).filter(Invoice.order_id == order_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Invoice already exists for order {order_id}")

    if not order.items:
        raise HTTPException(status_code=400, detail="Cannot create invoice for an order with no items")

    subtotal = round(sum(item.unit_price * item.quantity for item in order.items), 2)

    discount_amount, tax_amount, total = calculate_invoice(
        subtotal=subtotal,
        tax_rate=payload.tax_rate,
        discount_type=payload.discount_type,
        discount_value=payload.discount_value or 0.0,
    )

    invoice = Invoice(
        order_id=order_id,
        subtotal=subtotal,
        discount_type=payload.discount_type,
        discount_value=payload.discount_value,
        discount_amount=discount_amount,
        tax_rate=payload.tax_rate,
        tax_amount=tax_amount,
        total=total,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/invoice/{order_id}", response_model=InvoiceOut)
def get_invoice(order_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.order_id == order_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"No invoice found for order {order_id}")
    return invoice


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Invoice).order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
