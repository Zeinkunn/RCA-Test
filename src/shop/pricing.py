"""
Pricing & Discount Calculation Module.
Mendemonstrasikan Fault 2: IEEE 754 Floating-Point Precision Leak & Unbounded Discount Boundary Flaw.
Serta versi Fixed dengan Decimal Precision & Boundary Validation Rule.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from shop.models import OrderItem

class VulnerablePricingEngine:
    """
    [FLAWED IMPLEMENTATION - FAULT 2]
    Kalkulator harga menggunakan tipe data float dan tidak memiliki batas atas diskon.
    
    FAULT DESCRIPTION:
    1. Floating-Point Inexactness: Menggunakan tipe data 'float' bawaan yang berbasis
       IEEE 754 binary floating point. Menyebabkan desimal imajiner (cth: 0.1 + 0.2 != 0.3)
       sehingga terjadi selisih saldo pembukuan (rounding leakage).
    2. Unbounded Discount Stacking (Boundary Issue): Mengizinkan penumpukan voucher
       persentase dan voucher nominal tanpa ceiling cap. Mengakibatkan total harga
       bisa bernilai NEGATIF (toko berhutang ke pembeli).
    """
    def __init__(self, tax_rate: float = 0.11):
        self.tax_rate = tax_rate

    def calculate_totals(
        self,
        items: List[OrderItem],
        percentage_discount: float = 0.0,
        fixed_discount: float = 0.0
    ) -> Dict[str, float]:
        """
        CACAT KODE (FAULT 2):
        - Float arithmetic tanpa presisi moneter.
        - Tidak ada validasi total_discount <= subtotal.
        """
        # Subtotal dihitung dengan float
        subtotal = sum(item.quantity * item.unit_price for item in items)

        # Diskon persentase dihitung
        discount_pct_val = subtotal * (percentage_discount / 100.0)
        
        # Akumulasi diskon tanpa batas maksimum
        total_discount = discount_pct_val + fixed_discount

        # Subtotal setelah diskon bisa menjadi NEGATIF!
        taxable_amount = subtotal - total_discount

        # Pajak dihitung dari taxable amount
        tax = taxable_amount * self.tax_rate

        # Total amount akhir
        total = taxable_amount + tax

        return {
            "subtotal": subtotal,
            "discount": total_discount,
            "tax": tax,
            "total": total
        }


class FixedPricingEngine:
    """
    [SECURE & ROBUST IMPLEMENTATION]
    Menggunakan Decimal (Fixed-point arithmetic) dan validasi batas diskon (Boundary Checking).
    """
    def __init__(self, tax_rate: str = "0.11"):
        self.tax_rate = Decimal(tax_rate)

    @staticmethod
    def _to_decimal(val: float | str | int | Decimal) -> Decimal:
        return Decimal(str(val))

    @staticmethod
    def _round_money(amount: Decimal) -> Decimal:
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_totals(
        self,
        items: List[OrderItem],
        percentage_discount: float = 0.0,
        fixed_discount: float = 0.0
    ) -> Dict[str, Decimal]:
        """
        MONEY ARITHMETIC WITH BOUNDARY VALIDATION:
        - Tipe data Decimal dengan pembulatan ROUND_HALF_UP.
        - Diskon persentase dibatasi maksimal 100%.
        - Total diskon tidak boleh melebihi subtotal (Cap: min(discount, subtotal)).
        - Total belanja tidak akan pernah negatif.
        """
        # 1. Hitung Subtotal dengan Decimal
        subtotal = sum(
            (Decimal(str(item.quantity)) * self._to_decimal(item.unit_price))
            for item in items
        )
        subtotal = self._round_money(subtotal)

        # 2. Validasi Batas Diskon Persentase (0% - 100%)
        safe_pct = max(0.0, min(100.0, percentage_discount))
        pct_decimal = Decimal(str(safe_pct)) / Decimal("100")
        discount_from_pct = self._round_money(subtotal * pct_decimal)

        # 3. Validasi Diskon Nominal (tidak boleh negatif)
        fixed_disc_decimal = max(Decimal("0.00"), self._to_decimal(fixed_discount))

        # 4. Ceiling Cap: Total diskon tidak boleh melebihi subtotal
        total_discount_raw = discount_from_pct + fixed_disc_decimal
        effective_discount = min(total_discount_raw, subtotal)
        effective_discount = self._round_money(effective_discount)

        # 5. Taxable Amount (dijamin >= 0)
        taxable_amount = max(Decimal("0.00"), subtotal - effective_discount)

        # 6. Hitung Pajak
        tax = self._round_money(taxable_amount * self.tax_rate)

        # 7. Total Akhir
        total = self._round_money(taxable_amount + tax)

        return {
            "subtotal": subtotal,
            "discount": effective_discount,
            "tax": tax,
            "total": total
        }
