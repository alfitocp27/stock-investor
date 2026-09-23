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
        "PGAS.JK",
    ]
    data_cache_ttl_hours: int = 6

    # Telegram
    telegram_token: str = ""
    telegram_chat_id: str = ""

    # Database (relatif terhadap direktori project agar dapat berjalan di PC/laptop mana pun)
    db_url: str = f"sqlite:///{Path(__file__).parent.parent / 'data' / 'stock_investor.db'}"

    class Config:
        env_prefix = "SI_"

settings = Settings()
