from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
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

    scan_results = relationship("ScanResult", back_populates="stock", cascade="all, delete-orphan")
    allocations = relationship("PortfolioAllocation", back_populates="stock")

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
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    return Session()
