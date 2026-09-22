# 📈 Stock Investor — Personal Low-Risk IDX Investment Advisor

Sistem analisis dan alokasi dana tabungan personal untuk investasi saham di Bursa Efek Indonesia (IDX) dengan pendekatan low-risk & hybrid (fundamental + teknikal), dilengkapi dashboard web interaktif dan notifikasi otomatis Telegram.

---

## 🚀 Fitur Utama
- **Hybrid Scoring Engine:** Bobot 60% Fundamental (PE, PBV, ROE, Debt/Equity, Dividend Yield) + 40% Teknikal (RSI, MACD, Trend MA, Volatilitas, ATR).
- **Risk Rating & Guard:** Klasifikasi risiko LOW, MEDIUM, HIGH dengan filter ketat untuk alokasi dana tabungan.
- **Portofolio Risk Allocator:** Mengalokasikan dana secara proporsional dengan batas maksimal 30% per saham & buffer tunai aman 15%.
- **Dashboard Web Modern:** Tampilan responsif FastAPI + HTML Jinja2 untuk melihat daftar skor, detail saham, dan rekomendasi portofolio.
- **Notifikasi Telegram Otomatis:** Alert saat skor naik signifikan, sinyal BUY teknikal, atau peringatan risiko stop-loss.
- **Cache & Rate-Limit Handling:** Cache 6 jam di SQLite dengan mekanisme anti 429 rate limit Yahoo Finance.

---

## 📋 Persyaratan Sistem
- Python 3.11+
- Koneksi Internet (untuk sinkronisasi data yfinance)

---

## ⚙️ Instalasi

1. **Clone & Buat Virtual Environment:**
   ```bash
   python -m venv .venv
   # Windows (Git Bash)
   source .venv/Scripts/activate
   ```

2. **Install Dependensi:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🔧 Konfigurasi

Dapat dikonfigurasi melalui `app/config.py` atau Environment Variables (dengan prefix `SI_`):

| Variable Environment | Default | Keterangan |
|---|---|---|
| `SI_DANA_TOTAL` | `5000000.0` | Total dana tabungan yang dialokasikan (Rp) |
| `SI_MIN_ALOKASI_PER_SAHAM` | `0.15` | Minimal alokasi per saham (15%) |
| `SI_MAX_ALOKASI_PER_SAHAM` | `0.30` | Maksimal alokasi per saham (30%) |
| `SI_BUFFER_TUNAI` | `0.15` | Cadangan tunai aman (15%) |
| `SI_W_FUNDAMENTAL` | `0.60` | Bobot penilaian fundamental (60%) |
| `SI_W_TECHNICAL` | `0.40` | Bobot penilaian teknikal (40%) |
| `SI_TELEGRAM_TOKEN` | `""` | Telegram Bot Token |
| `SI_TELEGRAM_CHAT_ID` | `""` | Telegram Chat ID penerima notifikasi |
| `SI_IDX_WATCHLIST` | `['BBCA.JK', 'BBRI.JK', ...]` | Daftar kode saham IDX yang dipantau |

---

## 🏃 Cara Menjalankan

1. **Jalankan Aplikasi Web & Scheduler:**
   ```bash
   python -m app.main
   ```
   Atau via uvicorn:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Buka Aplikasi:**
   - **Dashboard:** [http://localhost:8000](http://localhost:8000)
   - **API Stocks:** [http://localhost:8000/api/stocks](http://localhost:8000/api/stocks)
   - **API Portfolio:** [http://localhost:8000/api/portfolio](http://localhost:8000/api/portfolio)

3. **Manual Trigger Scan:**
   Dapat menekan tombol **⚡ Scan Sekarang** di Dashboard Web, atau via HTTP POST:
   ```bash
   curl -X POST http://localhost:8000/scan
   ```

---

## 📁 Struktur Folder Project

```text
stock-investor/
├── app/
│   ├── analyzer/       # Scoring engine & indikator teknikal + fundamental
│   ├── data/           # Database models, yfinance fetcher, cache layer
│   ├── notify/         # Telegram notification bot & rule deduplikasi
│   ├── risk/           # Portfolio allocation engine & risk guard
│   ├── web/            # FastAPI routes & template Jinja2
│   ├── config.py       # Pydantic settings & konfigurasi aplikasi
│   ├── main.py         # Entry point aplikasi FastAPI + APScheduler
│   └── scheduler.py    # Pipeline scan harian otomatis
├── tests/              # Test suite lengkap (Unit test & Integration test)
├── requirements.txt    # Daftar dependensi Python
└── README.md           # Panduan penggunaan
```

---

## ⚠️ Disclaimer
Aplikasi ini dibuat khusus sebagai **alat bantu analisis personal** dan simulasi alokasi dana. **Bukan nasihat finansial profesional.** Keputusan eksekusi investasi di pasar saham tetap menjadi tanggung jawab pengguna sepenuhnya.
