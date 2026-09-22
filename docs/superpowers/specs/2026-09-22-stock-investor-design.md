# Stock Investor — Personal Low-Risk IDX Investment Advisor

Tanggal: 2026-09-22
Status: Approved

## Ringkasan / Tujuan

Sebuah alat pribadi untuk membantu **satu pengguna** (BOS) mengalokasikan tabungan
ke saham Bursa Efek Indonesia (IDX) dengan risiko rendah. Sistem menganalisa
saham IDX yang berpotensi naik (skor hybrid fundamental + technical), memberikan
rekomendasi alokasi dana (dana < Rp 5 juta), menampilkan dashboard web, dan
mengirim notifikasi otomatis ke Telegram saat ada saham yang skornya naik.

**Bukan** marketplace publik — alat personal untuk satu orang.

### Sukses = 
- Dashboard web menampilkan daftar saham IDX dengan skor risiko & peluang.
- Analisa hybrid (fundamental + technical) untuk tiap saham.
- Rekomendasi alokasi dana per saham dengan batas risiko.
- Notifikasi Telegram otomatis saat terjadi peluang (skor naik / sinyal beli).
- Scan berkala otomatis (scheduler).

## Asumsi & Konstrain

- Platform: **Windows 10**, Python 3.11 (aktif).
- Lokasi project: `D:/projek/stock-investor`.
- Pasar: **saham IDX** (suffix `.JK` di Yahoo Finance).
- Dana: **< Rp 5 juta**, low-risk / aman.
- Sumber data: **Yahoo Finance via `yfinance`** (gratis).
- Bahasa & framework: **Python + FastAPI** (modern, async, fast).
- Dashboard: **web** (FastAPI + template/server-rendered atau SPA ringan).
- Notifikasi: **Telegram** (terintegrasi Hermes).
- Eksekusi: **Rekomendasi + alokasi; pembelian dilakukan manual oleh user via
  broker** (Ajaib/Stockbit/Bibit). Sistem TIDAK mengeksekusi order otomatis ke
  broker (belum ada API broker yang disediakan). Ini mengurangi risiko dan
  kompleksitas.
- Pengembangan: **full build** (bukan MVP).

## Arsitektur

```
┌──────────────────────────────────────────────┐
│         DASHBOARD WEB (FastAPI)              │
│  - daftar saham + skor                       │
│  - detail tiap saham (chart, metrik)         │
│  - rekomendasi alokasi dana                  │
└──────────────┬───────────────────────────────┘
               │
┌──────────────▼───────────────────────────────┐
│        ANALYZER ENGINE (background/service)  │
│  - fetch data IDX dari yfinance              │
│  - skor fundamental (PE, PBV, ROE, debt,     │
│    dividend yield)                           │
│  - skor technical (trend, RSI, MACD, volume, │
│    moving average)                           │
│  - gabung jadi skor total + risk rating      │
└──────────────┬───────────────────────────────┘
               │  scan berkala (APScheduler)
┌──────────────▼───────────────────────────────┐
│      NOTIFICATION (Telegram via Hermes)      │
│  - alert skor naik / sinyal beli             │
│  - rekomendasi masuk posisi                  │
└──────────────┬───────────────────────────────┘
               │  persist data
┌──────────────▼───────────────────────────────┐
│        DATABASE (SQLite via SQLAlchemy)      │
│  - daftar saham, hasil scan, riwayat skor,   │
│    alokasi/portofolio                        │
└──────────────────────────────────────────────┘
```

### Komponen & tanggung jawab (unit kecil, single purpose)

1. **Data Layer** (`app/data/`)
   - `fetcher.py` — bungkus `yfinance`; ambil harga historis + fundamental
     untuk kode IDX (`XXXX.JK`).
   - `cache.py` — cache hasil fetch ke SQLite agar tidak spam API.

2. **Analyzer Engine** (`app/analyzer/`)
   - `indicators.py` — RSI, MACD, moving average, volume, ATR, volatilitas.
   - `fundamental.py` — PE, PBV, ROE, debt ratio, dividend yield.
   - `scorer.py` — bobot fundamental+technical → skor 0-100 + risk rating
     (LOW/MEDIUM/HIGH).
   - `screener.py` — filter hanya saham layak (large-cap/liquid/low-risk).

3. **Risk Management** (`app/risk/`)
   - `allocator.py` — hitung alokasi dana per saham dari dana total, batas
     maks per saham, spread antar saham, buffer tunai.
   - `filters.py` — jauhi saham volatilitas tinggi & utang besar.

4. **Web Dashboard** (`app/web/`)
   - FastAPI app, routes, template (Jinja2) atau minim SPA.
   - Halaman: daftar saham+skor, detail saham, rekomendasi alokasi.

5. **Notifier** (`app/notify/`)
   - `telegram.py` — kirim pesan alert ke Telegram (via Hermes/API bot).
   - `rules.py` — aturan kapan mengirim (skor naik melewati threshold, sinyal
     beli muncul).

6. **Scheduler** (`app/scheduler.py`)
   - APScheduler job harian/intraday → trigger analyzer + notifier.

### Database

SQLite (file `data/stock_investor.db`) via SQLAlchemy.
Tabel utama:
- `stocks` — kode, nama, sektor, market_cap.
- `scan_results` — kode, timestamp, skor, komponen skor, risk_rating.
- `portfolio_allocations` — kode, jumlah dana, tanggal, status.
- `alerts` — log notifikasi yg terkirim (avoid spam).

## Scoring (Hybrid)

**Skor = w_fund * fundamental_score + w_tech * technical_score**

Bobot default (bisa dikonfigurasi di config):
- w_fund = 0.6, w_tech = 0.4 (low-risk → condong fundamental)

Komponen (masing 0-100, dinormalisasi):
- Fundamental: PE (valuasi), PBV, ROE (profitabilitas), debt-to-equity
  (leverage), dividend yield (pendapatan pasif).
- Technical: trend (MA), RSI (momentum), MACD (sinyal), volume (likuiditas),
  volatilitas (semakin rendah semakin baik untuk low-risk).

**Risk rating** (dari agregat):
- LOW: skor stabil, valuasi wajar, utang rendah, volatilitas rendah.
- MEDIUM / HIGH: filter lebih ketat; HIGH dikecualikan dari rekomendasi.

## Alokasi Dana (low-risk, < Rp 5 juta)

- Jangan semua dana di satu saham: min 3-5 saham LOW/MEDIUM.
- Batas maks per saham: ~25-30%.
- Sisakan buffer tunai ~10-20% (cash reserve / dry powder).
- Stop-loss mental: rekomendasi cut off jika skor turun / sinyal negatif.

## Notifikasi Telegram

- Dilakukan via **Hermes** (BOS sudah pakai Hermes + Telegram).
- Rules:
  - Saham LOW-risk yang skornya naik melewati threshold → kirim alert + alokasi.
  - Muncul sinyal beli baru pada saham yang dipantau → kirim alert.
  - Peringatan jika saham yg dipegang turun skor (potensi stop-loss).
- Dedup: jangan kirim notif berulang untuk sinyal sama (pakai tabel `alerts`).

## Error Handling

- Jaringan/API gagal (yfinance timeout): retry bounded + log + jangan crash.
- Data fundamental kosong utk sebagian saham: tandai & skip dari skor, jangan
  invent data.
- API rate limit: cache + throttling (interval fetch).
- Scheduler crash: restart aman, idempotent scan.

## Testing

- Unit test per komponen (scorer, indicators, allocator, filters).
- Test dengan data real kecil (yfinance) + mock untuk determinisme.
- Smoke test dashboard (routes return 200).
- TDD diikuti selama implementasi.

## Lingkup Awal (full build)

Yang DIBANGUN:
- Data layer (yfinance IDX fetch + cache)
- Analyzer hybrid + screener + risk rating
- Risk management / allocator
- Dashboard web FastAPI
- Notifier Telegram + rules (dedup)
- Scheduler harian
- SQLite persistence
- Test suite

Yang TIDAK dibangun (sengaja):
- Auto-execution order ke broker (manual via broker user).
- Multi-user / marketplace.
- Analisa saham US.
- Real intraday tick (cukup harian close untuk low-risk).

## Struktur Direktori

```
D:/projek/stock-investor/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI entrypoint
│   ├── config.py          # bobot, thresholds, dana awal
│   ├── scheduler.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── fetcher.py
│   │   ├── cache.py
│   │   └── models.py      # SQLAlchemy models
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── indicators.py
│   │   ├── fundamental.py
│   │   ├── scorer.py
│   │   └── screener.py
│   ├── risk/
│   │   ├── __init__.py
│   │   ├── allocator.py
│   │   └── filters.py
│   ├── web/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── templates/
│   └── notify/
│       ├── __init__.py
│       ├── telegram.py
│       └── rules.py
├── tests/
├── data/
├── requirements.txt
├── README.md
└── docs/superpowers/specs/2026-09-22-stock-investor-design.md
```
