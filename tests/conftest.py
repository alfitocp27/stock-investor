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
