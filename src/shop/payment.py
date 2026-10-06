"""
Payment Gateway Simulator.
Mendukung simulasi transaksi sukses, saldo tidak cukup, dan network failure.
"""
from enum import Enum
import uuid

class PaymentError(Exception):
    """Exception dasar pembayaran."""
    pass

class InsufficientFundsError(PaymentError):
    """Saldo pelanggan tidak mencukupi."""
    pass

class PaymentGatewayTimeoutError(PaymentError):
    """Koneksi ke gateway pembayaran timeout / error jaringan."""
    pass

class MockPaymentGateway:
    def __init__(self, simulate_network_failure: bool = False):
        self.simulate_network_failure = simulate_network_failure

    def process_charge(self, customer_id: str, amount: float, customer_balance: float) -> str:
        """
        Memproses pemotongan dana pelanggan.
        Jika terjadi masalah jaringan atau saldo kurang, exception dilempar.
        """
        if self.simulate_network_failure:
            raise PaymentGatewayTimeoutError("HTTP 504: Gateway Timeout saat menghubungi provider bank")

        if customer_balance < amount:
            raise InsufficientFundsError(
                f"Saldo customer (Rp {customer_balance:,.2f}) tidak cukup untuk membayar Rp {amount:,.2f}"
            )

        # Transaksi sukses -> return transaction ID
        return f"TXN-{uuid.uuid4().hex[:10].upper()}"
