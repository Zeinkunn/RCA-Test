"""
Test Suite: Defect / Fault Fixed (Verification Suite)
Membuktikan secara empiris bahwa perbaikan (patches) berhasil menyelesaikan
seluruh 3 defect/fault tanpa menimbulkan efek samping (regresi).

Penulis : Zainul Mutawakkil (23EO10003)
Matkul  : Analisis dan Pengujian Sistem
"""
import sys
import os
import unittest
import threading
from decimal import Decimal
from typing import List

# Tambahkan src ke sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from shop.models import Product, OrderItem, Customer, OrderStatus, PaymentStatus
from shop.inventory import FixedInventoryManager
from shop.pricing import FixedPricingEngine
from shop.payment import MockPaymentGateway, PaymentGatewayTimeoutError
from shop.order_service import FixedOrderService

class TestFaultsFixed(unittest.TestCase):

    def test_fixed_1_concurrency_race_condition_resolved(self):
        """
        [VERIFIKASI SOLUSI FAULT 1: THREAD-SAFE CONCURRENCY LOCK]
        Skenario:
        - Stok barang fisik hanya ada 1 unit di gudang.
        - 10 thread user berbeda mencoba membeli barang secara bersamaan (barrier sync).
        
        Hasil Ekspektasi & Aktual (FIXED):
        - Dengan RLock, tepat 1 transaksi yang berhasil.
        - 9 transaksi lainnya ditolak secara aman.
        - Stok akhir tepat bernilai 0 (TIDAK MINUS, TIDAK OVERSELLING).
        """
        print("\n" + "="*70)
        print(">>> VERIFIKASI SOLUSI FAULT 1: THREAD-SAFE LOCKING <<<")
        inventory = FixedInventoryManager()
        item_sku = "LAPTOP-GAMING-01"
        initial_stock = 1
        inventory.add_product(Product(sku=item_sku, name="Gaming Laptop High-End", base_price=20_000_000.0, stock=initial_stock))

        successful_orders = 0
        rejected_orders = 0
        lock_counter = threading.Lock()
        barrier = threading.Barrier(10)

        def buy_worker():
            nonlocal successful_orders, rejected_orders
            barrier.wait()  # Semua thread jalan bersamaan
            if inventory.deduct_stock(item_sku, 1):
                with lock_counter:
                    successful_orders += 1
            else:
                with lock_counter:
                    rejected_orders += 1

        threads = [threading.Thread(target=buy_worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final_stock = inventory.get_stock(item_sku)
        print(f"Stok Awal Fisik     : {initial_stock}")
        print(f"Transaksi Sukses    : {successful_orders} (Harus tepat 1)")
        print(f"Transaksi Ditolak   : {rejected_orders} (Harus tepat 9)")
        print(f"Stok Akhir di Gudang: {final_stock} (Harus tepat 0)")

        self.assertEqual(successful_orders, 1, "Hanya boleh 1 transaksi sukses!")
        self.assertEqual(rejected_orders, 9, "9 transaksi lainnya harus ditolak!")
        self.assertEqual(final_stock, 0, "Stok akhir harus tepat 0 (tidak boleh minus)!")
        print(">>> SOLUSI FAULT 1 TERVERIFIKASI SUKSES (ZERO OVERSELLING) <<<")

    def test_fixed_2_decimal_precision_and_capped_discount(self):
        """
        [VERIFIKASI SOLUSI FAULT 2: DECIMAL ARITHMETIC & BOUNDARY RULES]
        Skenario:
        1. User belanja Rp 100.000, mencoba memasang voucher berlebihan (50% + Rp 70.000 = Rp 120.000).
        2. Pecahan moneter dengan angka desimal.
        
        Hasil Ekspektasi & Aktual (FIXED):
        - Diskon otomatis di-cap maksimum senilai subtotal (Rp 100.000).
        - Total tagihan Rp 0 (TIDAK BISA NEGATIF).
        - Presisi Decimal moneter tepat hingga 2 digit tanpa artefak biner IEEE 754.
        """
        print("\n" + "="*70)
        print(">>> VERIFIKASI SOLUSI FAULT 2: DECIMAL PRECISION & BOUNDARY RULES <<<")
        pricing = FixedPricingEngine(tax_rate="0.11")

        items = [OrderItem(sku="BOOK-01", quantity=1, unit_price=100_000.0)]

        totals = pricing.calculate_totals(
            items=items,
            percentage_discount=50.0,
            fixed_discount=70_000.0
        )

        print(f"Subtotal       : Rp {totals['subtotal']}")
        print(f"Diskon Ter-cap : Rp {totals['discount']} (Dibatasi setara subtotal)")
        print(f"Pajak          : Rp {totals['tax']}")
        print(f"TOTAL TAGIHAN  : Rp {totals['total']} (Aman, tidak minus)")

        self.assertEqual(totals["discount"], Decimal("100000.00"), "Diskon harus di-cap maksimal Rp 100.000!")
        self.assertEqual(totals["total"], Decimal("0.00"), "Total tagihan harus Rp 0.00 (tidak negatif)!")
        self.assertGreaterEqual(totals["total"], Decimal("0.00"), "Total tidak boleh negatif!")

        # Uji presisi desimal
        fractional_items = [OrderItem(sku="CANDY-01", quantity=3, unit_price=0.1)]
        frac_totals = pricing.calculate_totals(fractional_items)
        print(f"Kalkulasi Moneter Pecahan (3 * 0.1): {frac_totals['subtotal']}")
        self.assertEqual(frac_totals["subtotal"], Decimal("0.30"), "Presisi moneter terjamin tepat 0.30!")
        print(">>> SOLUSI FAULT 2 TERVERIFIKASI SUKSES (DATA INTEGRITY TERJAMIN) <<<")

    def test_fixed_3_compensating_transaction_on_payment_failure(self):
        """
        [VERIFIKASI SOLUSI FAULT 3: COMPENSATING TRANSACTION / ROLLBACK]
        Skenario:
        - Stok awal produk: 5 unit.
        - Customer memesan 2 unit.
        - Payment gateway mengalami failure (timeout jaringan).
        
        Hasil Ekspektasi & Aktual (FIXED):
        - Order Service menangkap error pembayaran dan mengeksekusi kompensasi rollback.
        - Status order FAILED.
        - Seluruh stok (2 unit) dikembalikan ke gudang secara utuh.
        - Stok akhir kembali tepat 5 unit (TIDAK ADA PHANTOM DEDUCTION).
        """
        print("\n" + "="*70)
        print(">>> VERIFIKASI SOLUSI FAULT 3: COMPENSATING ROLLBACK <<<")
        inventory = FixedInventoryManager()
        pricing = FixedPricingEngine()
        gateway = MockPaymentGateway(simulate_network_failure=True)

        item_sku = "SMARTPHONE-X"
        initial_stock = 5
        inventory.add_product(Product(sku=item_sku, name="Smartphone X Flagship", base_price=10_000_000.0, stock=initial_stock))

        service = FixedOrderService(inventory=inventory, pricing=pricing, gateway=gateway)
        customer = Customer(customer_id="CUST-001", name="Budi Santoso", email="budi@example.com", balance=50_000_000.0)

        order = service.checkout(
            customer=customer,
            items=[OrderItem(sku=item_sku, quantity=2, unit_price=10_000_000.0)]
        )

        stock_after_rollback = inventory.get_stock(item_sku)
        print(f"Status Pesanan       : {order.status.value}")
        print(f"Alasan Pembatalan    : {order.failure_reason}")
        print(f"Stok Awal Gudang     : {initial_stock}")
        print(f"Stok Pasca Rollback  : {stock_after_rollback} (Dipulihkan penuh ke {initial_stock})")

        self.assertEqual(order.status, OrderStatus.FAILED)
        self.assertEqual(stock_after_rollback, initial_stock, "Stok harus dipulihkan 100% saat pembayaran gagal!")
        print(">>> SOLUSI FAULT 3 TERVERIFIKASI SUKSES (NO PHANTOM DEDUCTION) <<<")

if __name__ == "__main__":
    unittest.main()
