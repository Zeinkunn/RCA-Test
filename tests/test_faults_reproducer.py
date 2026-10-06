"""
Test Suite: Defect / Fault Reproducer
Membuktikan secara empiris dan deterministik keberadaan 3 defect/fault pada sistem.

Penulis : Zainul Mutawakkil (23EO10003)
Matkul  : Analisis dan Pengujian Sistem
"""
import sys
import os
import unittest
import threading
from typing import List

# Tambahkan src ke sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from shop.models import Product, OrderItem, Customer, OrderStatus, PaymentStatus
from shop.inventory import VulnerableInventoryManager
from shop.pricing import VulnerablePricingEngine
from shop.payment import MockPaymentGateway, InsufficientFundsError, PaymentGatewayTimeoutError
from shop.order_service import VulnerableOrderService

class TestFaultsReproducer(unittest.TestCase):

    def test_fault_1_race_condition_inventory_oversell(self):
        """
        [PEMBUKTIAN FAULT 1: RACE CONDITION & INVENTORY OVERSELLING]
        Skenario:
        - Stok barang fisik hanya ada 1 unit di gudang.
        - 10 thread user berbeda mencoba membeli barang secara bersamaan (konkuren).
        
        Ekspektasi Sistem Benar:
        - Tepat 1 user berhasil, 9 user ditolak. Stok akhir = 0.
        
        Hasil Aktual (FAULT REPRODUCED):
        - Karena check-and-decrement tidak atomik, beberapa thread membaca stok = 1
          dan sama-sama berhasil melakukan deduksi stok.
        - Stok akhir menjadi MINUS (< 0), terjadi overselling parah.
        """
        print("\n" + "="*70)
        print(">>> MENJALANKAN TEST REPRODUKSI FAULT 1: CONCURRENCY RACE CONDITION <<<")
        inventory = VulnerableInventoryManager()
        item_sku = "LAPTOP-GAMING-01"
        initial_stock = 1
        inventory.add_product(Product(sku=item_sku, name="Gaming Laptop High-End", base_price=20_000_000.0, stock=initial_stock))

        successful_orders = 0
        lock_counter = threading.Lock()
        barrier = threading.Barrier(10)

        def buy_worker():
            nonlocal successful_orders
            barrier.wait()  # Sinkronisasi start line agar seluruh thread menyerbu bersamaan
            if inventory.deduct_stock(item_sku, 1):
                with lock_counter:
                    successful_orders += 1

        threads: List[threading.Thread] = []
        for _ in range(10):
            t = threading.Thread(target=buy_worker)
            threads.append(t)

        # Jalankan semua thread secara simultan
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final_stock = inventory.get_stock(item_sku)
        print(f"Stok Awal Fisik     : {initial_stock}")
        print(f"Transaksi Sukses    : {successful_orders} (Seharusnya maks 1!)")
        print(f"Stok Akhir di Gudang: {final_stock}")

        # Pembuktian Defect: Stok menjadi minus atau transaksi sukses lebih dari 1!
        self.assertGreater(
            successful_orders,
            initial_stock,
            f"Fault terbukti: Transaksi sukses ({successful_orders}) melebihi stok awal ({initial_stock})!"
        )
        self.assertLess(
            final_stock,
            0,
            f"Fault terbukti: Stok akhir bernilai minus ({final_stock}) akibat race condition!"
        )
        print(">>> FAULT 1 BERHASIL DIBUKTIKAN (INVENTORY OVERSELLING TERJADI) <<<")

    def test_fault_2_float_precision_and_negative_total(self):
        """
        [PEMBUKTIAN FAULT 2: FLOAT PRECISION LEAK & UNBOUNDED DISCOUNT BOUNDARY]
        Skenario:
        1. Float Inexactness: Akumulasi harga pecahan menghasilkan artefak desimal.
        2. Boundary Flaw: User belanja Rp 100.000, memakai kupon diskon 50% + voucher Rp 70.000.
        
        Ekspektasi Sistem Benar:
        - Presisi mata uang tepat tanpa noise biner.
        - Total diskon dibatasi maksimal Rp 100.000, tagihan akhir minimal Rp 0.
        
        Hasil Aktual (FAULT REPRODUCED):
        - Diskon menjadi Rp 120.000 (melebihi subtotal).
        - Total akhir bernilai NEGATIF (-Rp 22.200 setelah pajak/PPN)!
        - Toko justru merugi membayar customer.
        """
        print("\n" + "="*70)
        print(">>> MENJALANKAN TEST REPRODUKSI FAULT 2: FLOAT PRECISION & UNBOUNDED DISCOUNT <<<")
        pricing = VulnerablePricingEngine(tax_rate=0.11)

        items = [
            OrderItem(sku="BOOK-01", quantity=1, unit_price=100_000.0)
        ]

        # Diskon 50% = 50.000, plus fixed voucher 70.000 -> Total diskon 120.000!
        totals = pricing.calculate_totals(
            items=items,
            percentage_discount=50.0,
            fixed_discount=70_000.0
        )

        print(f"Subtotal       : Rp {totals['subtotal']:,.2f}")
        print(f"Total Diskon   : Rp {totals['discount']:,.2f} (Lebih besar dari subtotal!)")
        print(f"Dasar Pajak    : Rp {totals['subtotal'] - totals['discount']:,.2f}")
        print(f"Pajak (PPN 11%): Rp {totals['tax']:,.2f}")
        print(f"TOTAL TAGIHAN  : Rp {totals['total']:,.2f}")

        # Pembuktian Defect 2a: Total menjadi negatif
        self.assertLess(
            totals["total"],
            0.0,
            f"Fault terbukti: Total tagihan bernilai negatif ({totals['total']})!"
        )

        # Pembuktian Defect 2b: Presisi IEEE 754 float
        fractional_items = [
            OrderItem(sku="CANDY-01", quantity=3, unit_price=0.1),
        ]
        frac_totals = pricing.calculate_totals(fractional_items)
        raw_subtotal_repr = repr(frac_totals["subtotal"])
        print(f"Representasi Raw Float (3 * 0.1): {raw_subtotal_repr}")
        # Dalam float binary IEEE 754: 3 * 0.1 = 0.30000000000000004
        self.assertNotEqual(
            raw_subtotal_repr,
            "0.3",
            "Fault terbukti: Float binary inexactness terjadi pada kalkulasi moneter!"
        )
        print(">>> FAULT 2 BERHASIL DIBUKTIKAN (TAGIHAN NEGATIF & INEXACT PRECISION) <<<")

    def test_fault_3_phantom_stock_deduction_on_payment_failure(self):
        """
        [PEMBUKTIAN FAULT 3: PHANTOM STOCK DEDUCTION / MISSING ROLLBACK]
        Skenario:
        - Stok awal produk: 5 unit.
        - Customer memesan 2 unit.
        - Saat proses pembayaran, gateway melemparkan error (Network Timeout / Saldo Kurang).
        
        Ekspektasi Sistem Benar:
        - Pesanan berstatus FAILED.
        - Stok barang harus tetap utuh (5 unit) karena transaksi tidak berhasil.
        
        Hasil Aktual (FAULT REPRODUCED):
        - Status pesanan FAILED.
        - Stok barang terlanjur dikurangi menjadi 3 unit dan TIDAK DIKEMBALIKAN.
        - 2 unit barang hilang secara gaib (phantom stock loss / data corruption).
        """
        print("\n" + "="*70)
        print(">>> MENJALANKAN TEST REPRODUKSI FAULT 3: PHANTOM STOCK DEDUCTION <<<")
        inventory = VulnerableInventoryManager()
        pricing = VulnerablePricingEngine()
        gateway = MockPaymentGateway(simulate_network_failure=True)  # Memaksa error network

        item_sku = "SMARTPHONE-X"
        initial_stock = 5
        inventory.add_product(Product(sku=item_sku, name="Smartphone X Flagship", base_price=10_000_000.0, stock=initial_stock))

        service = VulnerableOrderService(inventory=inventory, pricing=pricing, gateway=gateway)
        customer = Customer(customer_id="CUST-001", name="Budi Santoso", email="budi@example.com", balance=50_000_000.0)

        # Eksekusi checkout 2 unit
        order = service.checkout(
            customer=customer,
            items=[OrderItem(sku=item_sku, quantity=2, unit_price=10_000_000.0)]
        )

        stock_after_failed_checkout = inventory.get_stock(item_sku)
        print(f"Status Pesanan         : {order.status.value}")
        print(f"Alasan Kegagalan       : {order.failure_reason}")
        print(f"Stok Awal Gudang       : {initial_stock}")
        print(f"Stok Pasca Transaksi   : {stock_after_failed_checkout} (Seharusnya tetap {initial_stock}!)")

        # Pembuktian Defect: Status FAILED tetapi stok berkurang tanpa pemulihan!
        self.assertEqual(order.status, OrderStatus.FAILED)
        self.assertEqual(
            stock_after_failed_checkout,
            3,
            "Fault terbukti: Stok berkurang menjadi 3 padahal pesanan berstatus FAILED!"
        )
        self.assertNotEqual(
            stock_after_failed_checkout,
            initial_stock,
            "Fault terbukti: Ketiadaan mekanisme compensating rollback menyebabkan phantom deduction!"
        )
        print(">>> FAULT 3 BERHASIL DIBUKTIKAN (STOK BERKURANG MESKI PESANAN GAGAL) <<<")

if __name__ == "__main__":
    unittest.main()
