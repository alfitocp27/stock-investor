import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.data.models import (
    Stock,
    ScanResult,
    PortfolioAllocation,
    Alert,
    Base,
    get_engine,
    get_session,
)

EXPECTED_TABLES = {
    "stocks",
    "scan_results",
    "portfolio_allocations",
    "alerts",
}


@pytest.fixture
def session():
    """Fresh in-memory SQLite session with all tables created."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _make_stock(s, **kwargs):
    stock = Stock(kode=kwargs.pop("kode", "BBCA.JK"), nama=kwargs.pop("nama", "BCA"), **kwargs)
    s.add(stock)
    s.commit()
    return stock


def test_create_stock(session):
    stock = Stock(
        kode="BBCA.JK",
        nama="Bank Central Asia",
        sektor="Perbankan",
        market_cap=9e17,
    )
    session.add(stock)
    session.commit()

    assert stock.id is not None
    assert stock.kode == "BBCA.JK"
    assert stock.nama == "Bank Central Asia"
    assert stock.sektor == "Perbankan"
    assert stock.market_cap == 9e17
    # kode is unique + indexed
    assert {c["name"] for c in inspect(session.bind).get_indexes("stocks")} == {"ix_stocks_kode"}


def test_stock_defaults(session):
    stock = _make_stock(session)
    assert stock.last_updated is not None


def test_all_four_tables_created():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    tables = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES <= tables


def test_scan_result_relation(session):
    stock = _make_stock(session)
    sr = ScanResult(stock_id=stock.id, skor_total=75.0, risk_rating="LOW")
    session.add(sr)
    session.commit()

    assert stock.scan_results[0].skor_total == 75.0
    assert sr.stock.kode == "BBCA.JK"  # back-reference works


def test_portfolio_allocation(session):
    stock = _make_stock(session)
    alloc = PortfolioAllocation(stock_id=stock.id, dana_alokasi=1_500_000, status="ACTIVE")
    session.add(alloc)
    session.commit()

    assert stock.allocations[0].dana_alokasi == 1_500_000
    assert alloc.status == "ACTIVE"


def test_portfolio_allocation_default_status(session):
    stock = _make_stock(session)
    alloc = PortfolioAllocation(stock_id=stock.id, dana_alokasi=500_000)
    session.add(alloc)
    session.commit()
    assert alloc.status == "ACTIVE"


def test_alert_deduplication_flag(session):
    stock = _make_stock(session)
    alert = Alert(
        stock_id=stock.id,
        alert_type="SIGNAL_RISE",
        message="Test",
        deduplicated=False,
    )
    session.add(alert)
    session.commit()

    assert alert.deduplicated is False


def test_alert_default_deduplicated_false(session):
    stock = _make_stock(session)
    alert = Alert(stock_id=stock.id, alert_type="RISK_WARNING", message="High debt")
    session.add(alert)
    session.commit()
    assert alert.deduplicated is False


def test_foreign_key_cascade_deletes_scan_results(session):
    """Deleting a Stock cascades to its ScanResults (all, delete-orphan)."""
    stock = _make_stock(session)
    session.add_all(
        [
            ScanResult(stock_id=stock.id, skor_total=80.0),
            ScanResult(stock_id=stock.id, skor_total=60.0),
        ]
    )
    session.commit()

    session.delete(stock)
    session.commit()

    assert session.query(ScanResult).count() == 0
    assert session.query(Stock).count() == 0


def test_foreign_keys_declared():
    fk_map = {t.name: {f.column.table.name for f in t.foreign_keys} for t in Base.metadata.tables.values()}
    assert fk_map["scan_results"] == {"stocks"}
    assert fk_map["portfolio_allocations"] == {"stocks"}
    assert fk_map["alerts"] == {"stocks"}
    # stocks has no outbound FK
    assert fk_map["stocks"] == set()


def test_get_engine_uses_settings_db_url(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "db_url", "sqlite:///:memory:")
    engine = get_engine()
    assert engine is not None


def test_get_session_creates_tables_if_missing(tmp_path, monkeypatch):
    """get_session() must create missing tables against a fresh DB file."""
    from app.config import settings

    db_file = tmp_path / "stock_investor.db"
    monkeypatch.setattr(settings, "db_url", f"sqlite:///{db_file.as_posix()}")

    assert not db_file.exists()
    s = get_session()
    try:
        tables = set(inspect(s.bind).get_table_names())
        assert EXPECTED_TABLES <= tables

        # Session is usable end-to-end
        stock = Stock(kode="BBRI.JK", nama="Bank Rakyat Indonesia")
        s.add(stock)
        s.commit()
        assert stock.id is not None
    finally:
        s.close()
