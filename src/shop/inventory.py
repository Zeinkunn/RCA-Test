"""
Inventory Management Module.
Mendemonstrasikan Fault 1: Concurrency Race Condition pada pengurangan stok.
Serta versi Fixed dengan Reentrant Lock dan Atomic Decrement.
"""
import threading
import time
from typing import Dict, Optional
from shop.models import Product

class InsufficientStockError(Exception):
    """Dilempar ketika stok barang tidak mencukupi."""
    pass

class VulnerableInventoryManager:
    """
    [FLAWED IMPLEMENTATION - FAULT 1]
    Mengelola stok barang tanpa mekanisme sinkronisasi (thread-safety).
    
    FAULT DESCRIPTION:
    Pengecekan (check) dan pengurangan (act) stok terpisah tanpa atomic lock.
    Ketika multiple thread mengakses method reserve_stock() secara bersamaan,
    terjadi Race Condition (Time-of-Check to Time-of-Use / TOCTOU).
    """
    def __init__(self):
        self._products: Dict[str, Product] = {}

    def add_product(self, product: Product) -> None:
        self._products[product.sku] = product

    def get_stock(self, sku: str) -> int:
        if sku not in self._products:
            raise KeyError(f"Product {sku} not found")
        return self._products[sku].stock

    def deduct_stock(self, sku: str, quantity: int) -> bool:
        """
        CACAT KODE (FAULT 1):
        Tidak ada lock. Di antara pengecekan stok dan modifikasi nilai,
        terjadi context switch yang menyebabkan overselling (stok minus).
        """
        if sku not in self._products:
            raise KeyError(f"Product {sku} not found")

        # Pengecekan stok (Time of Check)
        if self._products[sku].stock >= quantity:
            # Simulasi delay I/O atau context-switch thread
            time.sleep(0.005)
            
            # Pengurangan stok (Time of Use) - Tidak thread-safe!
            self._products[sku].stock -= quantity
            return True
        else:
            return False

    def restore_stock(self, sku: str, quantity: int) -> None:
        """Mengembalikan stok (tidak otomatis terpanggil saat kegagalan di payment flow vulnerable)."""
        if sku in self._products:
            self._products[sku].stock += quantity


class FixedInventoryManager:
    """
    [SECURE & ROBUST IMPLEMENTATION]
    Menggunakan Reentrant Mutex Lock (threading.RLock) untuk memastikan
    operasi check-and-decrement bersifat ATOMIK.
    """
    def __init__(self):
        self._products: Dict[str, Product] = {}
        self._lock = threading.RLock()

    def add_product(self, product: Product) -> None:
        with self._lock:
            self._products[product.sku] = product

    def get_stock(self, sku: str) -> int:
        with self._lock:
            if sku not in self._products:
                raise KeyError(f"Product {sku} not found")
            return self._products[sku].stock

    def deduct_stock(self, sku: str, quantity: int) -> bool:
        """
        THREAD-SAFE ATOMIC DECREMENT:
        Memastikan operasi read-check-modify berada di dalam critical section.
        """
        with self._lock:
            if sku not in self._products:
                raise KeyError(f"Product {sku} not found")

            if self._products[sku].stock >= quantity:
                time.sleep(0.005)  # Delay simulasi, tetap aman karena terkunci
                self._products[sku].stock -= quantity
                return True
            return False

    def restore_stock(self, sku: str, quantity: int) -> None:
        """Thread-safe rollback stok."""
        with self._lock:
            if sku in self._products:
                self._products[sku].stock += quantity
