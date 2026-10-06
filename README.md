# Mini E-Commerce Order & Inventory System: Root Cause Analysis (RCA) & Fault Identification

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)]()
[![Course](https://img.shields.io/badge/Mata%20Kuliah-Analisis%20dan%20Pengujian%20Sistem-orange.svg)]()

> Repositori tugas besar mata kuliah **Analisis dan Pengujian Sistem**. Berisi implementasi mini program transaksi *e-commerce*, pembuktian empiris **3 Defect/Fault kritis**, analisis mendalam **Root Cause Analysis (RCA)** menggunakan metode **5-Whys** dan **Ishikawa (Fishbone) Diagram**, matriks **CAPA**, serta generator slide presentasi **PowerPoint (`.pptx`)**.

---

## 👤 Informasi Mahasiswa

- **Nama**        : Zainul Mutawakkil
- **NIM**         : 23EO10003
- **Mata Kuliah** : Analisis dan Pengujian Sistem
- **Topik Tugas** : Pembuatan Mini Program, Identifikasi 3 Defect/Fault, Root Cause Analysis (RCA), dan Presentasi PPT

---

## 📁 Struktur Repositori

```
RCA/
├── src/
│   └── shop/
│       ├── __init__.py           # Package initializer
│       ├── models.py             # Data models (Product, Order, Customer, OrderStatus)
│       ├── inventory.py          # Inventory Manager (Vulnerable [Fault 1] & Fixed)
│       ├── pricing.py            # Pricing Engine (Vulnerable [Fault 2] & Fixed)
│       ├── payment.py            # Third-Party Payment Gateway Mock
│       └── order_service.py      # Checkout Orchestrator (Vulnerable [Fault 3] & Fixed)
├── tests/
│   ├── test_faults_reproducer.py # Automated test pembuktian 3 defect deterministik
│   └── test_faults_fixed.py      # Automated test verifikasi 100% perbaikan lolos
├── docs/
│   └── RCA_REPORT.md             # Dokumen Laporan Lengkap RCA (5-Whys, Fishbone, CAPA)
├── scripts/
│   └── generate_ppt.py           # Script python-pptx pembuat file presentasi PowerPoint
├── RCA_Presentasi_Tugas_AP.pptx  # File Slide PowerPoint Final Widescreen 16:9 (16 Slides)
└── README.md                     # Panduan repositori
```

---

## 🎯 3 Defect / Fault Kritis yang Ditemukan

| No | Nama Defect / Fault | Kategori | Lokasi Kode | Gejala / Failure | Status Perbaikan |
|:---:|---|---|---|---|:---:|
| **1** | **Concurrency Race Condition** *(Inventory Overselling)* | Thread Safety / Concurrency | `src/shop/inventory.py` | Stok fisik 1 unit diserbu 10 user paralel $\rightarrow$ seluruh 10 order lolos, stok akhir **-9**. | ✅ Fixed (`threading.RLock`) |
| **2** | **Float Precision Leak & Unbounded Discount** | Business Logic & Arithmetic | `src/shop/pricing.py` | Akumulasi float biner (0.3000...4) dan kupon tumpuk menghasilkan **total tagihan -Rp 22.200**. | ✅ Fixed (`decimal.Decimal` & Cap) |
| **3** | **Phantom Stock Deduction** *(No Transaction Rollback)* | Data Integrity & Consistency | `src/shop/order_service.py` | Gateway timeout saat bayar $\rightarrow$ order GAGAL, namun stok barang **berkurang dan hilang permanen**. | ✅ Fixed (Compensating Rollback) |

---

## 🔬 Taksonomi Kegagalan Software (IEEE 610.12)

Dalam rekayasa pengujian perangkat lunak, rantai terjadinya malfungsi adalah:
1. **Human Mistake / Error**: Asumsi keliru programmer saat mendesain arsitektur.
2. **Fault / Defect**: Cacat statis yang tersimpan dalam baris kode program.
3. **Error**: Kondisi state memori internal yang korup saat kode cacat dieksekusi.
4. **Failure**: Kegagalan fungsional eksternal yang teramati oleh pengguna/sistem lain.

---

## 🚀 Panduan Eksekusi & Menjalankan Pengujian

### 1. Prasyarat Lingkungan
- Python versi 3.10 atau lebih baru terpasang di sistem.
- Instalasi dependensi untuk slide generator:
  ```bash
  pip install python-pptx
  ```

### 2. Menjalankan Uji Pembuktian Bug (Defect Reproducer)
Perintah ini membuktikan bahwa ketiga defect benar-benar ada dan memicu kegagalan sistem:
```bash
python tests/test_faults_reproducer.py
```
*Output cuplikan:*
```text
>>> MENJALANKAN TEST REPRODUKSI FAULT 1: CONCURRENCY RACE CONDITION <<<
Stok Awal Fisik     : 1
Transaksi Sukses    : 10 (Seharusnya maks 1!)
Stok Akhir di Gudang: -9
>>> FAULT 1 BERHASIL DIBUKTIKAN (INVENTORY OVERSELLING TERJADI) <<<

>>> MENJALANKAN TEST REPRODUKSI FAULT 2: FLOAT PRECISION & UNBOUNDED DISCOUNT <<<
Subtotal       : Rp 100,000.00
Total Diskon   : Rp 120,000.00
TOTAL TAGIHAN  : Rp -22,200.00 (Minus!)
>>> FAULT 2 BERHASIL DIBUKTIKAN (TAGIHAN NEGATIF & INEXACT PRECISION) <<<

>>> MENJALANKAN TEST REPRODUKSI FAULT 3: PHANTOM STOCK DEDUCTION <<<
Status Pesanan         : FAILED
Stok Pasca Transaksi   : 3 (Seharusnya tetap 5!)
>>> FAULT 3 BERHASIL DIBUKTIKAN (STOK BERKURANG MESKI PESANAN GAGAL) <<<
```

### 3. Menjalankan Uji Verifikasi Perbaikan (Fixed Verification)
Perintah ini membuktikan bahwa seluruh perbaikan telah menyelesaikan ketiga defect tanpa menimbulkan regresi:
```bash
python tests/test_faults_fixed.py
```
*Hasil:* `Ran 3 tests ... OK (100% Passed)`.

### 4. Menghasilkan Ulang Slide PowerPoint (`.pptx`)
Untuk membuat ulang file presentasi slide secara otomatis:
```bash
python scripts/generate_ppt.py
```
File akan diperbarui di root repositori: `RCA_Presentasi_Tugas_AP.pptx`.

---

## 📊 Ringkasan Root Cause Analysis (RCA)

### 1. Defect 1: Concurrency Race Condition
- **5-Whys**: Stok -9 $\rightarrow$ 10 pesanan disetujui bersamaan $\rightarrow$ Seluruh thread melihat stok $\ge 1$ $\rightarrow$ Tidak ada Mutex Lock $\rightarrow$ **Root Cause**: Developer mengira operasi in-memory bersifat atomik dan tim QA tidak memiliki automated concurrency stress testing.
- **Fishbone 4M**:
  - *Man*: Kurang pemahaman *Time-of-Check to Time-of-Use* (TOCTOU).
  - *Machine*: Multi-core preemptive thread context switching.
  - *Method*: Pengujian hanya *single-threaded*.
  - *Material*: Spesifikasi tidak merinci batasan *concurrent user* saat promo.

### 2. Defect 2: Float Precision & Unbounded Discount
- **5-Whys**: Invoice minus $\rightarrow$ Diskon lebih besar dari belanja $\rightarrow$ Voucher persentase & nominal diakumulasi tanpa batas $\rightarrow$ Menggunakan tipe primitif `float` $\rightarrow$ **Root Cause**: Ketiadaan *Value Object* moneter berbasis `Decimal` dan tidak adanya *Boundary Value Analysis (BVA)* pada pengujian kalkulator diskon.
- **Fishbone 4M**:
  - *Man*: Anggapan keliru bahwa `float` aman untuk mata uang.
  - *Machine*: Representasi biner IEEE 754 berbasis aproksimasi basis-2.
  - *Method*: Ketiadaan pengujian nilai batas ekstrem ($<0, =0, >\text{subtotal}$).
  - *Material*: Aturan marketing promo ambigu mengenai *stackability*.

### 3. Defect 3: Phantom Stock Deduction
- **5-Whys**: Stok berkurang padahal order batal $\rightarrow$ Deduksi stok dieksekusi sebelum otorisasi payment sukses $\rightarrow$ Blok `except` lupa memanggil restorasi $\rightarrow$ Tidak ada transaksi atomik $\rightarrow$ **Root Cause**: Ketiadaan arsitektur *Compensating Transaction* (Saga Pattern) dan minimnya *Fault-Injection / Chaos Testing*.
- **Fishbone 4M**:
  - *Man*: Mindset pengembang hanya fokus pada *Happy-Path*.
  - *Machine*: Fluktuasi jaringan payment gateway eksternal.
  - *Method*: Ketiadaan simulasi kegagalan jaringan saat QA.
  - *Material*: Arsitektur checkout tidak memiliki mekanisme rollback terdistribusi.

---

## 📋 Matriks Tindakan CAPA (Corrective & Preventive Actions)

| Defect ID | Corrective Action (Jangka Pendek) | Preventive Action (Jangka Panjang) | PIC |
|---|---|---|---|
| **DEF-01** | Implementasi `threading.RLock` pada critical section. | Tambahkan *Concurrency Testing* (k6/Locust) ke CI/CD & Database Pessimistic Locking. | Backend Engineer |
| **DEF-02** | Refactor ke `Decimal` & validasi `min(discount, subtotal)`. | Terapkan *Money Value Object* & wajibkan *Boundary Value Analysis* (BVA) test. | QA & Analyst |
| **DEF-03** | Blok kompensasi `try-except-rollback` pada checkout. | Desain arsitektur *Saga Pattern* & pasang cron job rekonsiliasi data stok berkala. | Architect |

---

## 🖥️ Struktur Slide Presentasi (`RCA_Presentasi_Tugas_AP.pptx`)

Presentasi dibuat sebanyak **16 slide** dengan format **Widescreen (16:9)** dan desain profesional:
1. **Slide 1**: Cover (Judul, Nama: Zainul Mutawakkil, NIM: 23EO10003, Matkul: Analisis dan Pengujian Sistem).
2. **Slide 2**: Gambaran Umum Sistem & Arsitektur Modul E-Commerce.
3. **Slide 3**: Landasan Teori: Taksonomi Kegagalan Software (Fault $\rightarrow$ Error $\rightarrow$ Failure) & Metodologi RCA.
4. **Slide 4**: Ringkasan Eksekutif 3 Defect Kritis yang Ditemukan.
5. **Slide 5**: Deep Dive Defect 1: Race Condition & Inventory Overselling.
6. **Slide 6**: RCA Defect 1: Analisis 5-Whys & Diagram Fishbone.
7. **Slide 7**: Solusi Defect 1: Mutex Lock & Bukti Verifikasi Pengujian.
8. **Slide 8**: Deep Dive Defect 2: Float Precision Leak & Unbounded Discount.
9. **Slide 9**: RCA Defect 2: Analisis 5-Whys & Diagram Fishbone.
10. **Slide 10**: Solusi Defect 2: Decimal Moneter & Bukti Verifikasi Pengujian.
11. **Slide 11**: Deep Dive Defect 3: Phantom Stock Deduction (No Rollback).
12. **Slide 12**: RCA Defect 3: Analisis 5-Whys & Diagram Fishbone.
13. **Slide 13**: Solusi Defect 3: Compensating Rollback & Bukti Verifikasi Pengujian.
14. **Slide 14**: Matriks Tindakan Korektif & Preventif (CAPA).
15. **Slide 15**: Best Practices Pengujian & Keandalan Perangkat Lunak.
16. **Slide 16**: Kesimpulan & Sesi Tanya Jawab (Q&A).

---

## 📜 Lisensi & Penggunaan Akademik

Repositori ini disusun sebagai pemenuhan tugas akademik mata kuliah **Analisis dan Pengujian Sistem** oleh **Zainul Mutawakkil (NIM: 23EO10003)**. Bebas digunakan untuk referensi pembelajaran analisis cacat perangkat lunak dan Root Cause Analysis.
