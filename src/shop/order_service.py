"""
Order Processing Service.
Mendemonstrasikan Fault 3: Phantom Stock Deduction akibat ketiadaan rollback transaksi.
Serta versi Fixed dengan Compensating Transaction (Unit-of-Work Rollback).
"""
import logging
from typing import List, Optional
from shop.models import Order, OrderItem, Customer, OrderStatus, PaymentStatus
from shop.inventory import VulnerableInventoryManager, FixedInventoryManager
from shop.pricing import VulnerablePricingEngine, FixedPricingEngine
from shop.payment import MockPaymentGateway, PaymentError

logger = logging.getLogger(__name__)

class OrderProcessingError(Exception):
    pass

class VulnerableOrderService:
    """
    [FLAWED IMPLEMENTATION - FAULT 3]
    Alur checkout pesanan yang tidak memiliki mekanisme rollback (Non-Atomic Multi-Step).
    
    FAULT DESCRIPTION:
    Stok barang dikurangi terlebih dahulu di awal alur checkout.
    Ketika proses pembayaran ke payment gateway mengalami kegagalan (Timeout / Insufficient Funds),
    service menangkap error dan menandai pesanan GAGAL, tetapi LUPA mengembalikan
    stok yang telah terpotong.
    Akibatnya: Stok barang 'lenyap' dari gudang padahal pesanan tidak pernah sukses
    (Phantom Inventory Deduction / State Inconsistency).
    """
    def __init__(self, inventory: VulnerableInventoryManager, pricing: VulnerablePricingEngine, gateway: MockPaymentGateway):
        self.inventory = inventory
        self.pricing = pricing
        self.gateway = gateway

    def checkout(
        self,
        customer: Customer,
        items: List[OrderItem],
        percentage_discount: float = 0.0,
        fixed_discount: float = 0.0
    ) -> Order:
        order = Order(customer_id=customer.customer_id, items=items)

        # 1. CACAT KODE (FAULT 3 - Step 1): Deduksi stok langsung dilakukan
        for item in items:
            success = self.inventory.deduct_stock(item.sku, item.quantity)
            if not success:
                order.status = OrderStatus.FAILED
                order.failure_reason = f"Stok tidak cukup untuk SKU: {item.sku}"
                return order

        # 2. Kalkulasi harga
        totals = self.pricing.calculate_totals(items, percentage_discount, fixed_discount)
        order.subtotal = totals["subtotal"]
        order.discount_amount = totals["discount"]
        order.tax_amount = totals["tax"]
        order.total_amount = totals["total"]

        # 3. Eksekusi Pembayaran
        try:
            order.status = OrderStatus.PROCESSING
            self.gateway.process_charge(
                customer_id=customer.customer_id,
                amount=order.total_amount,
                customer_balance=customer.balance
            )
            # Sukses
            customer.balance -= order.total_amount
            order.payment_status = PaymentStatus.CAPTURED
            order.status = OrderStatus.COMPLETED
            return order

        except PaymentError as err:
            # CACAT KODE (FAULT 3 - Step 2):
            # Error ditangkap, status diubah jadi FAILED, tetapi TIDAK ADA ROLLBACK STOK!
            order.status = OrderStatus.FAILED
            order.payment_status = PaymentStatus.FAILED
            order.failure_reason = str(err)
            
            # Stok di inventory dibiarkan berkurang tanpa pemulihan!
            return order


class FixedOrderService:
    """
    [SECURE & ROBUST IMPLEMENTATION]
    Menerapkan pola Compensating Transaction (Saga / Unit-of-Work Rollback Pattern).
    Jika salah satu langkah checkout gagal, semua perubahan state sebelumnya di-rollback.
    """
    def __init__(self, inventory: FixedInventoryManager, pricing: FixedPricingEngine, gateway: MockPaymentGateway):
        self.inventory = inventory
        self.pricing = pricing
        self.gateway = gateway

    def checkout(
        self,
        customer: Customer,
        items: List[OrderItem],
        percentage_discount: float = 0.0,
        fixed_discount: float = 0.0
    ) -> Order:
        order = Order(customer_id=customer.customer_id, items=items)
        allocated_items: List[OrderItem] = []

        try:
            # 1. Alokasi stok dengan pelacakan (tracking)
            for item in items:
                success = self.inventory.deduct_stock(item.sku, item.quantity)
                if not success:
                    # Rollback item yang sudah terlanjur dialokasikan sebelumnya
                    self._rollback_inventory(allocated_items)
                    order.status = OrderStatus.FAILED
                    order.failure_reason = f"Stok tidak cukup untuk SKU: {item.sku}"
                    return order
                allocated_items.append(item)

            # 2. Kalkulasi harga aman
            totals = self.pricing.calculate_totals(items, percentage_discount, fixed_discount)
            order.subtotal = float(totals["subtotal"])
            order.discount_amount = float(totals["discount"])
            order.tax_amount = float(totals["tax"])
            order.total_amount = float(totals["total"])

            # 3. Proses Pembayaran
            order.status = OrderStatus.PROCESSING
            self.gateway.process_charge(
                customer_id=customer.customer_id,
                amount=order.total_amount,
                customer_balance=customer.balance
            )

            # Sukses penuh
            customer.balance -= order.total_amount
            order.payment_status = PaymentStatus.CAPTURED
            order.status = OrderStatus.COMPLETED
            return order

        except Exception as err:
            # KOMPENSASI / ROLLBACK SEMUA STOK YANG TERLANJUR DIKURANGI
            self._rollback_inventory(allocated_items)
            order.status = OrderStatus.FAILED
            order.payment_status = PaymentStatus.FAILED
            order.failure_reason = f"Transaksi dibatalkan karena kegagalan pembayaran: {str(err)}"
            return order

    def _rollback_inventory(self, allocated_items: List[OrderItem]) -> None:
        """Mengembalikan seluruh stok barang yang telah terpotong."""
        for item in allocated_items:
            self.inventory.restore_stock(item.sku, item.quantity)
