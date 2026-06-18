from dataclasses import dataclass, field
from typing import List
from datetime import datetime

@dataclass
class Customer:
    id: int = None
    name: str = ""
    phone: str = ""
    address: str = ""
    
    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'phone': self.phone, 'address': self.address}

@dataclass
class OrderItem:
    product_name: str = ""
    quantity: int = 1
    price: float = 0.0
    
    def to_dict(self):
        return {'product_name': self.product_name, 'quantity': self.quantity, 'price': self.price}

@dataclass
class Order:
    id: int = None
    customer_id: int = 0
    customer_name: str = ""
    order_date: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))
    status: str = "новый"
    items: List[OrderItem] = field(default_factory=list)
    total: float = 0.0
    
    def __post_init__(self):
        if not self.order_date:
            self.order_date = datetime.now().strftime('%Y-%m-%d')
        self.calc_total()
    
    def calc_total(self):
        self.total = sum(item.quantity * item.price for item in self.items)
        return self.total
    
    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'order_date': self.order_date,
            'status': self.status,
            'items': [item.to_dict() for item in self.items],
            'total': self.total
        }