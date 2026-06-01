from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Order, OrderItem, OrderStatus
from app.schemas import OrderCreate, OrderOut, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["Orders"])

STATUS_TRANSITIONS = {
    OrderStatus.pending: OrderStatus.preparing,
    OrderStatus.preparing: OrderStatus.done,
    OrderStatus.done: None,
}


@router.post("/", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    order = Order(customer_name=payload.customer_name)
    db.add(order)
    db.flush()

    for item_data in payload.items:
        item = OrderItem(
            order_id=order.id,
            item_name=item_data.item_name,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
        )
        db.add(item)

    db.commit()
    db.refresh(order)
    return order


@router.get("/", response_model=List[OrderOut])
def list_orders(
    status_filter: OrderStatus = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(Order)
    if status_filter:
        query = query.filter(Order.status == status_filter)
    return query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(order_id: int, payload: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    next_status = STATUS_TRANSITIONS.get(order.status)

    if payload.status == order.status:
        raise HTTPException(status_code=400, detail=f"Order is already in '{order.status}' status")

    if payload.status != next_status:
        if next_status is None:
            raise HTTPException(status_code=400, detail="Order is already completed (done)")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition: '{order.status}' → '{payload.status}'. Expected next: '{next_status}'"
        )

    order.status = payload.status
    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    if order.status != OrderStatus.pending:
        raise HTTPException(status_code=400, detail="Only pending orders can be deleted")
    db.delete(order)
    db.commit()
