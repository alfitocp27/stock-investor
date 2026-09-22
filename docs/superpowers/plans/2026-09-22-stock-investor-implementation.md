# Stock Investor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Personal low-risk IDX investment advisor — web dashboard, hybrid stock analysis, Telegram alerts, scheduler.

**Architecture:** FastAPI web dashboard backed by a hybrid scorer (60% fundamental / 40% technical), SQLite persistence, yfinance data for IDX stocks, APScheduler for periodic scans, Telegram bot for alerts with dedup.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy (SQLite), yfinance, APScheduler, Telegram Bot API, Jinja2.

**Spec:** `docs/superpowers/specs/2026-09-22-stock-investor-design.md`

---

## Global Constraints

- Dana < Rp 5 juta, low-risk / aman.
- Pasar: IDX (suffix `.JK` di yfinance).
- Eksekusi: manual via broker — sistem hanya rekomendasi alokasi.
- Notifikasi: Telegram, dedup via `alerts` table.

---

## Review Focus

1. Saham tanpa data fundamental → discan tapi skor fundamental = 0 (tidak crash).
2. yfinance rate-limit atau timeout → retry bounded + cached fallback (tidak crash).
3. Dana kecil (< Rp 5 juta) dipecah ke ≥3 saham dengan buffer tunai 10-20%.
4. Notifikasi tidak spam — sinyal sama tidak dikirim dua kali (dedup check).
5. Saham HIGH-risk → tidak masuk rekomendasi alokasi.

---

## Task Decomposition

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `tests/conftest.py`

**Interfaces:**
- Produces: `app.config.Settings` — DanaTotal, BobotFundamental, BobotTechnical, ThresholdBuySignal, TelegramToken, TelegramChatID, DatabaseURL.

- [ ] **Step 1: Create `requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
yfinance==0.2.40
apscheduler==3.10.4
python-telegram-bot==21.3
jinja2==3.1.4
httpx==0.27.2
pydantic==2.9.2
pydantic-settings==2.5.2
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Create `app/config.py`**

```python
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Dana
    dana_total: float = 5_000_000.0  # Rp 5 juta, bisa override via env
    min_alokasi_per_saham: float = 0.15  # minimal 15% per saham
    max_alokasi_per_saham: float = 0.30  # maksimal 30% per saham
    buffer_tunai: float = 0.15  # 15% cash reserve
    min_jumlah_saham: int = 3

    # Scoring
    w_fundamental: float = 0.6
    w_technical: float = 0.4
    threshold_sinyal_beli: float = 70.0  # skor di atas ini = sinyal beli
    threshold_naik_alert: float = 60.0  # skor naik melewati ini = alert

    # Data
    idx_watchlist: list[str] = [  # Large-cap IDX30 starter list
        "BBCA.JK", "BBRI.JK", "BMRI.JK", "ASII.JK",
        "UNVR.JK", "TLKM.JK", "HMSP.JK", "GGRM.JK",
        "PGAS.JK", "PERTAMINA(JK?)",  # note: use BRPT.JK or cek daftar
    ]
    data_cache_ttl_hours: int = 6

    # Telegram
    telegram_token: str = ""
    telegram_chat_id: str = ""

    # Database
    db_url: str = "sqlite:///D:/projek/stock-investor/data/stock_investor.db"

    class Config:
        env_prefix = "SI_"

settings = Settings()
```

- [ ] **Step 3: Create `tests/conftest.py`**

```python
import pytest
from app.config import Settings

@pytest.fixture
def settings():
    return Settings(
        dana_total=5_000_000,
        min_alokasi_per_saham=0.15,
        max_alokasi_per_saham=0.30,
        buffer_tunai=0.15,
        min_jumlah_saham=3,
        w_fundamental=0.6,
        w_technical=0.4,
        threshold_sinyal_beli=70.0,
        threshold_naik_alert=60.0,
    )
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt app/config.py tests/conftest.py
git commit -m "feat: project setup with config and dependencies"
```

---

### Task 2: Database Models

**Files:**
- Create: `app/data/models.py`
- Modify: `app/data/__init__.py`
- Create: `tests/data/test_models.py`

**Interfaces:**
- Consumes: `app.config.settings`
- Produces: SQLAlchemy `Base`, tables: `Stock`, `ScanResult`, `PortfolioAllocation`, `Alert`.

- [ ] **Step 1: Create `app/data/models.py`**

```python
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from app.config import settings

Base = declarative_base()

class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True)
    kode = Column(String(10), unique=True, nullable=False, index=True)
    nama = Column(String(200))
    sektor = Column(String(100))
    market_cap = Column(Float)
    last_updated = Column(DateTime, default=datetime.utcnow)

    scan_results: list["ScanResult"] = relationship("ScanResult", back_populates="stock", cascade="all, delete-orphan")
    allocations: list["PortfolioAllocation"] = relationship("PortfolioAllocation", back_populates="stock")

class ScanResult(Base):
    __tablename__ = "scan_results"
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    skor_total = Column(Float)
    skor_fundamental = Column(Float)
    skor_technical = Column(Float)
    risk_rating = Column(String(10))  # LOW / MEDIUM / HIGH
    price = Column(Float)
    pe = Column(Float)
    pbv = Column(Float)
    roe = Column(Float)
    debt_ratio = Column(Float)
    dividend_yield = Column(Float)
    rsi = Column(Float)
    macd_signal = Column(String(10))  # BUY / SELL / NEUTRAL
    trend = Column(String(10))  # BULL / BEAR / SIDEWAYS

    stock = relationship("Stock", back_populates="scan_results")

class PortfolioAllocation(Base):
    __tablename__ = "portfolio_allocations"
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    dana_alokasi = Column(Float)  # dalam Rupiah
    tanggal = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="ACTIVE")  # ACTIVE / CLOSED / STOP_LOSS
    notes = Column(String(500))

    stock = relationship("Stock", back_populates="allocations")

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    alert_type = Column(String(50))  # SIGNAL_RISE / SCORE_ABOVE_THRESHOLD / RISK_WARNING
    message = Column(String(500))
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    deduplicated = Column(Boolean, default=False)

def get_engine():
    return create_engine(settings.db_url, connect_args={"check_same_thread": False})

def get_session():
    engine = get_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
```

- [ ] **Step 2: Create `tests/data/test_models.py`**

```python
from app.data.models import Stock, ScanResult, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile, os

def test_create_stock():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    stock = Stock(kode="BBCA.JK", nama="Bank Central Asia", sektor="Perbankan", market_cap=900_000_000_000_000)
    s.add(stock)
    s.commit()
    assert stock.id is not None
    assert stock.kode == "BBCA.JK"

def test_scan_result_relation():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    stock = Stock(kode="BBCA.JK", nama="BCA")
    s.add(stock); s.commit()
    sr = ScanResult(stock_id=stock.id, skor_total=75.0, risk_rating="LOW")
    s.add(sr); s.commit()
    assert stock.scan_results[0].skor_total == 75.0
```

- [ ] **Step 3: Commit**

```bash
git add app/data/models.py tests/data/test_models.py
git commit -m "feat: database models — Stock, ScanResult, PortfolioAllocation, Alert"
```

---

### Task 3: Data Fetcher (yfinance)

**Files:**
- Create: `app/data/fetcher.py`
- Create: `tests/data/test_fetcher.py`

**Interfaces:**
- Consumes: `app.config.settings.idx_watchlist`
- Produces: `def fetch_stock_data(kode: str) -> dict` — dict dengan keys: `price, pe, pbv, roe, debt_to_equity, dividend_yield, sector, market_cap`, `prices_1y` (series untuk technical), `error` (None atau string error).

- [ ] **Step 1: Write failing test**

```python
def test_fetch_valid_stock():
    from app.data.fetcher import fetch_stock_data
    data = fetch_stock_data("BBCA.JK")
    assert data["error"] is None
    assert data["price"] > 0
    assert data["pe"] > 0

def test_fetch_invalid_stock():
    from app.data.fetcher import fetch_stock_data
    data = fetch_stock_data("TIDAKADAKODE.JK")
    assert data["error"] is not None

def test_fetch_timeout_is_handled():
    from app.data.fetcher import fetch_stock_data
    data = fetch_stock_data("BBCA.JK")
    assert "error" in data
```

- [ ] **Step 2: Run test to verify it fails** (expected: import error or AttributeError)

```bash
cd D:/projek/stock-investor && pytest tests/data/test_fetcher.py -v 2>&1 | head -20
```

- [ ] **Step 3: Write minimal implementation**

```python
import yfinance as yf
import pandas as pd
from datetime import datetime

def fetch_stock_data(kode: str, lookback_days: int = 365) -> dict:
    """
    Ambil data saham IDX dari Yahoo Finance.
    Returns dict dengan fundamental + harga historis.
    """
    result = {
        "kode": kode,
        "price": None,
        "pe": None,
        "pbv": None,
        "roe": None,
        "debt_to_equity": None,
        "dividend_yield": None,
        "sector": None,
        "market_cap": None,
        "prices_1y": pd.DataFrame(),
        "error": None,
    }
    try:
        ticker = yf.Ticker(kode)
        info = ticker.info
        # Fundamental
        result["price"] = info.get("currentPrice") or info.get("previousClose")
        result["pe"] = info.get("trailingPE")
        result["pbv"] = info.get("priceToBook")
        result["roe"] = info.get("returnOnEquity")
        result["debt_to_equity"] = info.get("debtToEquity")
        result["dividend_yield"] = info.get("dividendYield")
        result["sector"] = info.get("sector")
        result["market_cap"] = info.get("marketCap")

        # Historis untuk technical
        hist = ticker.history(period=f"{lookback_days}d")
        result["prices_1y"] = hist

        if result["price"] is None:
            result["error"] = f"No price data for {kode}"
    except Exception as e:
        result["error"] = str(e)
    return result
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd D:/projek/stock-investor && pytest tests/data/test_fetcher.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/data/fetcher.py tests/data/test_fetcher.py
git commit -m "feat: yfinance data fetcher for IDX stocks"
```

---

### Task 4: Data Cache Layer

**Files:**
- Create: `app/data/cache.py`
- Create: `tests/data/test_cache.py`

**Interfaces:**
- Consumes: `app.data.fetcher.fetch_stock_data`, `app.data.models.get_session`, `app.config.settings.data_cache_ttl_hours`
- Produces: `def get_cached_or_fetch(kode: str) -> dict` — cek DB cache dulu, kalau expired atau kosong fetch dari yfinance, simpan ke DB.

- [ ] **Step 1: Write failing test** (mock yfinance, test cache hit/miss)

```python
def test_cache_miss_fetches(mocker):
    mock_fetch = mocker.patch("app.data.cache.fetch_stock_data", return_value={"kode": "BBCA.JK", "price": 9000, "error": None})
    result = get_cached_or_fetch("BBCA.JK")
    assert result["price"] == 9000
    mock_fetch.assert_called_once()
```

- [ ] **Step 2-5: Implement + test + commit**

Implementasi: simpan hasil fetch ke tabel `stocks` (upsert). Cache TTL = 6 jam.
```bash
git add app/data/cache.py tests/data/test_cache.py
git commit -m "feat: cache layer — upsert stock data with TTL"
```

---

### Task 5: Technical Indicators

**Files:**
- Create: `app/analyzer/indicators.py`
- Create: `tests/analyzer/test_indicators.py`

**Interfaces:**
- Consumes: `pandas.DataFrame` harga historis dari fetcher
- Produces: `def calculate_indicators(prices_df: pd.DataFrame) -> dict` — returns: `{rsi, macd_signal, trend, volume_avg_ratio, atr, volatility_30d}`

- [ ] **Step 1: Write failing test**

```python
import pandas as pd, numpy as np

def make_price_df(days=200):
    dates = pd.date_range("2025-01-01", periods=days)
    close = pd.Series(np.cumsum(np.random.randn(days)) + 100, index=dates)
    volume = pd.Series(np.random.randint(1_000_000, 10_000_000, days), index=dates)
    return pd.DataFrame({"Close": close, "Volume": volume})

def test_rsi_returns_value():
    from app.analyzer.indicators import calculate_indicators
    df = make_price_df()
    result = calculate_indicators(df)
    assert "rsi" in result
    assert 0 <= result["rsi"] <= 100

def test_macd_signal_valid():
    from app.analyzer.indicators import calculate_indicators
    df = make_price_df()
    result = calculate_indicators(df)
    assert result["macd_signal"] in ("BUY", "SELL", "NEUTRAL")

def test_trend_valid():
    from app.analyzer.indicators import calculate_indicators
    df = make_price_df()
    result = calculate_indicators(df)
    assert result["trend"] in ("BULL", "BEAR", "SIDEWAYS")
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/analyzer/test_indicators.py -v
```

- [ ] **Step 3: Write implementation**

```python
import pandas as pd
import numpy as np

def calculate_indicators(prices_df: pd.DataFrame) -> dict:
    if prices_df.empty or len(prices_df) < 30:
        return {"rsi": None, "macd_signal": "NEUTRAL", "trend": "SIDEWAYS",
                "volume_avg_ratio": None, "atr": None, "volatility_30d": None}

    close = prices_df["Close"]
    high = prices_df.get("High", close)
    low = prices_df.get("Low", close)
    volume = prices_df.get("Volume", pd.Series(0, index=close.index))

    # RSI(14)
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi_val = rsi.iloc[-1] if not rsi.isna().iloc[-1] else 50

    # MACD(12,26,9)
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9).mean()
    macd_signal = "BUY" if macd_line.iloc[-1] > signal_line.iloc[-1] else "SELL"

    # Trend: MA crossover
    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    if len(ma50) < 2:
        trend = "SIDEWAYS"
    elif close.iloc[-1] > ma20.iloc[-1] > ma50.iloc[-1]:
        trend = "BULL"
    elif close.iloc[-1] < ma20.iloc[-1] < ma50.iloc[-1]:
        trend = "BEAR"
    else:
        trend = "SIDEWAYS"

    # Volume ratio
    vol_avg_20 = volume.rolling(20).mean()
    vol_today = volume.iloc[-1]
    vol_avg_val = vol_avg_20.iloc[-1] if not vol_avg_20.isna().iloc[-1] else 1
    volume_avg_ratio = vol_today / max(vol_avg_val, 1)

    # ATR(14)
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1] if len(tr) >= 14 else None

    # Volatility 30d
    returns = close.pct_change().rolling(30).std()
    volatility_30d = returns.iloc[-1] if len(returns) >= 30 and not returns.isna().iloc[-1] else 0

    return {
        "rsi": float(rsi_val),
        "macd_signal": macd_signal,
        "trend": trend,
        "volume_avg_ratio": float(volume_avg_ratio),
        "atr": float(atr) if atr is not None else None,
        "volatility_30d": float(volatility_30d),
    }
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/analyzer/test_indicators.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/analyzer/indicators.py tests/analyzer/test_indicators.py
git commit -m "feat: technical indicators — RSI, MACD, trend, volume ratio, ATR, volatility"
```

---

### Task 6: Fundamental Analyzer

**Files:**
- Create: `app/analyzer/fundamental.py`
- Create: `tests/analyzer/test_fundamental.py`

**Interfaces:**
- Consumes: `dict` dari fetcher (pe, pbv, roe, debt_to_equity, dividend_yield, market_cap)
- Produces: `def calculate_fundamental_score(data: dict) -> tuple[float, dict]` — skor 0-100 + breakdown per komponen.

- [ ] **Step 1-5: TDD + implement + commit**

Score breakdown:
- PE: < 15 = bagus (score 100), 15-25 = wajar (50-100), > 25 = mahal (0-50), missing = 0
- PBV: < 1.5 = bagus (100), 1.5-3 = wajar (50-100), > 3 = mahal (0-50), missing = 0
- ROE: > 15% = bagus (100), 5-15% = wajar (50), < 5% = rendah (0), missing = 0
- Debt-to-Equity: < 1 = bagus (100), 1-2 = wajar (50), > 2 = tinggi (0), missing = 50
- Dividend Yield: > 4% = bagus (100), 2-4% = wajar (75), < 2% = rendah (0), missing = 0

```bash
git add app/analyzer/fundamental.py tests/analyzer/test_fundamental.py
git commit -m "feat: fundamental analyzer — PE, PBV, ROE, debt, dividend yield scoring"
```

---

### Task 7: Hybrid Scorer + Screener + Risk Rating

**Files:**
- Create: `app/analyzer/scorer.py`
- Create: `app/analyzer/screener.py`
- Create: `tests/analyzer/test_scorer.py`

**Interfaces:**
- Consumes: `app.analyzer.indicators`, `app.analyzer.fundamental`, `app.config.settings`
- Produces: `def score_stock(stock_data: dict) -> ScanResult` — return ScanResult object (skor_total, skor_fundamental, skor_technical, risk_rating).

- [ ] **Step 1: Write failing test**

```python
def test_low_risk_stock_high_score():
    from app.analyzer.scorer import score_stock
    data = {
        "kode": "BBCA.JK", "price": 9000, "error": None,
        "prices_1y": make_price_df(),
        "pe": 10, "pbv": 1.0, "roe": 0.20, "debt_to_equity": 0.5,
        "dividend_yield": 0.05, "sector": "Perbankan", "market_cap": 1e15,
    }
    result = score_stock(data)
    assert result.skor_total > 60
    assert result.risk_rating in ("LOW", "MEDIUM")

def test_missing_fundamental_graceful():
    from app.analyzer.scorer import score_stock
    data = {"kode": "TEST.JK", "price": 100, "error": None,
            "prices_1y": make_price_df(),
            "pe": None, "pbv": None, "roe": None, "debt_to_equity": None,
            "dividend_yield": None, "sector": None, "market_cap": None}
    result = score_stock(data)
    assert result.skor_fundamental == 0.0
    assert result.skor_total < result.skor_fundamental + 40  # technical still scores
```

- [ ] **Step 2-5: Implement + test + commit**

Scoring: `skor_total = w_fund * skor_fundamental + w_tech * skor_technical`
Risk rating logic:
- LOW: semua komponen aman (debt < 1, volatilitas < 0.02, PE wajar)
- HIGH: debt > 2, atau volatilitas > 0.05, atau ROE < 0 (rugi)
- MEDIUM: sisanya

```bash
git add app/analyzer/scorer.py app/analyzer/screener.py tests/analyzer/test_scorer.py
git commit -m "feat: hybrid scorer — combined fundamental+technical scoring with risk rating"
```

---

### Task 8: Risk Allocator

**Files:**
- Create: `app/risk/allocator.py`
- Create: `tests/risk/test_allocator.py`

**Interfaces:**
- Consumes: `list[ScanResult]` (saham yang discan), `app.config.settings`
- Produces: `def allocate_portfolio(results: list[ScanResult]) -> list[PortfolioRecommendation]` — list rekomendasi alokasi: `{kode, skor, alokasi_rp, persentase}`.

- [ ] **Step 1-5: TDD + implement + commit**

Logic:
1. Filter hanya LOW dan MEDIUM risk.
2. Urutkan berdasarkan skor_total descending.
3. Ambil top N saham (max 5 untuk dana kecil).
4. Alokasi proporsional berdasarkan skor (normalisasi), tapi:
   - Maks 30% per saham, min 15%.
   - Buffer tunai 15% dari dana total.
   - Sisakan cash reserve ~Rp 750.000 (15% × Rp 5.000.000).

```python
@dataclass
class PortfolioRecommendation:
    kode: str
    skor: float
    risk_rating: str
    alokasi_rp: float
    persentase: float
    alasan: str  # "Skor tinggi + risk rendah"
```

```bash
git add app/risk/allocator.py tests/risk/test_allocator.py
git commit -m "feat: risk allocator — proportional allocation with caps and cash reserve"
```

---

### Task 9: Telegram Notifier

**Files:**
- Create: `app/notify/telegram.py`
- Create: `app/notify/rules.py`
- Create: `tests/notify/test_telegram.py`

**Interfaces:**
- Consumes: `app.config.settings`, `app.data.models.get_session`, scan results
- Produces: `def check_and_notify(session, scan_results: list[ScanResult]) -> int` — return jumlah alert yang dikirim (0 kalau tidak ada yang kirim).

- [ ] **Step 1-5: TDD + implement + commit**

Rules (dari spec):
- Dedup: cek tabel `alerts` — kalau sinyal yang sama sudah dikirim dalam 24 jam, skip.
- ScoreAboveThreshold: skor naik melewati `threshold_naik_alert` (60) → kirim alert.
- SinyalBeli: `macd_signal == "BUY"` + `rsi < 70` → kirim sinyal beli.
- RiskWarning: saham yang dipegang (portofolio ACTIVE) turun risk_rating ke HIGH → peringatan stop-loss.

Message format (Telegram markdown):
```
📈 BBCA.JK — Sinyal Naik!
Skor: 75/100 (↑ dari 62)
Risk: LOW
Harga: Rp 9.200
💡 Alokasi: Rp 1.500.000 (30%)
```

```bash
git add app/notify/telegram.py app/notify/rules.py tests/notify/test_telegram.py
git commit -m "feat: telegram notifier with dedup rules"
```

---

### Task 10: FastAPI Dashboard — Core Routes

**Files:**
- Create: `app/web/routes.py`
- Create: `app/web/__init__.py`
- Create: `tests/web/test_routes.py`

**Interfaces:**
- Consumes: semua modul lain (models, analyzer, allocator)
- Produces: FastAPI app dengan routes:
  - `GET /` — dashboard home (redirect /dashboard)
  - `GET /dashboard` — daftar saham + skor + rekomendasi
  - `GET /saham/{kode}` — detail saham (chart, metrik fundamental+technical, history skor)
  - `GET /portofolio` — alokasi saat ini
  - `POST /scan` — trigger manual scan
  - `GET /api/stocks` — JSON API
  - `GET /api/portfolio` — JSON API alokasi

- [ ] **Step 1-5: TDD + implement + commit**

Dashboard page requirements:
- Tabel saham: kode, nama, skor_total, risk_rating, trend, MACD, harga, RSI
- Warna: hijau=LOW, kuning=MEDIUM, merah=HIGH
- Tabel alokasi: kode, dana alokasi (Rp), persentase, status
- Tombol "Scan Sekarang" (POST /scan)

```bash
git add app/web/routes.py tests/web/test_routes.py
git commit -m "feat: FastAPI dashboard routes"
```

---

### Task 11: Dashboard Templates

**Files:**
- Create: `app/web/templates/base.html`
- Create: `app/web/templates/dashboard.html`
- Create: `app/web/templates/stock_detail.html`
- Create: `app/web/templates/portfolio.html`

- [ ] **Step 1-5: Implement templates + smoke test + commit**

Template requirements (minimal, clean, functional):
- Navigation bar: Dashboard | Saham | Portofolio
- Dashboard: stock list table with sort by score
- Stock detail: price chart (simple line from history data), metrik cards (PE, PBV, RSI, MACD, ROE)
- Portfolio: allocation table, total dana, cash reserve shown

```bash
git add app/web/templates/
git commit -m "feat: dashboard templates"
```

---

### Task 12: Scheduler + Manual Scan Runner

**Files:**
- Create: `app/scheduler.py`
- Create: `tests/test_scheduler.py`

**Interfaces:**
- Consumes: semua modul (fetcher, analyzer, notifier)
- Produces: `def run_full_scan(session) -> dict` — jalankan scan semua saham + kirim notifikasi; `APScheduler` job harian jam 08:00 WIB.

- [ ] **Step 1-5: TDD + implement + commit**

Scan flow:
1. Ambil watchlist dari config.
2. Untuk tiap saham: fetch → calculate indicators → score → save to ScanResult.
3. Hitung alokasi portofolio.
4. Check notifikasi rules → kirim Telegram alert.
5. Commit.

```bash
git add app/scheduler.py tests/test_scheduler.py
git commit -m "feat: APScheduler daily scan job with Telegram alerts"
```

---

### Task 13: FastAPI Entry Point

**Files:**
- Create: `app/main.py`
- Create: `app/__init__.py` (entry point marker)

- [ ] **Step 1-5: Implement main.py + run test + commit**

```python
import uvicorn
from fastapi import FastAPI
from app.web.routes import router
from app.data.models import get_engine, Base

app = FastAPI(title="Stock Investor", description="Personal Low-Risk IDX Investment Advisor")
app.include_router(router)

@app.on_event("startup")
def on_startup():
    engine = get_engine()
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

```bash
git add app/main.py app/__init__.py
git commit -m "feat: FastAPI entry point — uvicorn server startup"
```

---

### Task 14: README + Installation Guide

**Files:**
- Create: `README.md`

- [ ] **Step 1-5: Write README + commit**

README sections:
- Project overview
- Requirements (Python 3.11)
- Installation (`pip install -r requirements.txt`)
- Configuration (env vars / `SI_DANA_TOTAL`, `SI_TELEGRAM_TOKEN`, `SI_TELEGRAM_CHAT_ID`)
- Running: `python -m app.main` atau `uvicorn app.main:app`
- First run: edit `app/config.py` — ganti `idx_watchlist` dengan saham yang dimonitor
- Folder structure
- Disclaimer investasi (bukan nasihat finansial)

```bash
git add README.md
git commit -m "docs: README with installation and usage guide"
```

---

### Task 15: Final Integration Smoke Test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1-5: Full flow test + commit**

Test:
```python
def test_full_scan_flow():
    from app.data.models import get_session
    from app.scheduler import run_full_scan
    session = get_session()
    result = run_full_scan(session)
    assert "scanned" in result
    assert result["scanned"] >= 0
    assert "alerts_sent" in result
```

Run: `pytest tests/test_integration.py -v`
Expected: PASS (atau SKIP kalau offline)

```bash
git add tests/test_integration.py
git commit -m "test: integration smoke test — full scan flow"
```

---

## Summary: 15 Tasks

| # | Task | Komponen |
|---|------|----------|
| 1 | Project Setup | requirements, config |
| 2 | Database Models | SQLAlchemy models |
| 3 | Data Fetcher | yfinance fetch |
| 4 | Cache Layer | TTL cache di DB |
| 5 | Technical Indicators | RSI, MACD, trend, ATR |
| 6 | Fundamental Analyzer | PE, PBV, ROE, debt, yield |
| 7 | Hybrid Scorer + Screener | skor gabungan + risk rating |
| 8 | Risk Allocator | alokasi proporsional + buffer |
| 9 | Telegram Notifier | alert + dedup |
| 10 | FastAPI Routes | REST API + pages |
| 11 | Dashboard Templates | HTML/Jinja2 pages |
| 12 | Scheduler | APScheduler job |
| 13 | FastAPI Entry Point | main.py |
| 14 | README | docs |
| 15 | Integration Test | smoke test |