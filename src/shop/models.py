"""
Domain models for Mini E-Commerce System.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import time
import uuid

class OrderStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class PaymentStatus(Enum):
    UNPAID = "UNPAID"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

@dataclass
class Product:
    sku: str
    name: str
    base_price: float  # Digunakan dalam vulnerable model
    stock: int
    category: str = "general"

@dataclass
class OrderItem:
    sku: str
    quantity: int
    unit_price: float

@dataclass
class Customer:
    customer_id: str
    name: str
    email: str
    balance: float = 1_000_000.0

@dataclass
class Order:
    order_id: str = field(default_factory=lambda: f"ORD-{uuid.uuid4().hex[:8].upper()}")
    customer_id: str = ""
    items: List[OrderItem] = field(default_factory=list)
    subtotal: float = 0.0
    discount_amount: float = 0.0
    tax_amount: float = 0.0
    total_amount: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.UNPAID
    created_at: float = field(default_factory=time.time)
    failure_reason: Optional[str] = None
