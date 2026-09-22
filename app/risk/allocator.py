from app.config import settings
from dataclasses import dataclass

@dataclass
class PortfolioRecommendation:
    kode: str
    skor: float
    risk_rating: str
    alokasi_rp: float
    persentase: float
    alasan: str

def allocate_portfolio(scan_results: list, total_dana: float = None) -> list[dict]:
    total = total_dana or settings.dana_total
    usable = total * (1 - settings.buffer_tunai)  # setelah buffer tunai

    # Filter + sort
    candidates = [r for r in scan_results if getattr(r, "risk_rating", None) in ("LOW", "MEDIUM")]
    candidates.sort(key=lambda r: getattr(r, "skor_total", 0), reverse=True)
    candidates = candidates[:5]

    if not candidates:
        return []

    # Proportional scores
    total_score = sum(getattr(r, "skor_total", 0) for r in candidates) or 1.0
    allocations = []
    for r in candidates:
        skor = getattr(r, "skor_total", 0)
        prop = skor / total_score
        alokasi = usable * prop
        # Cap at max / min
        max_alokasi = total * settings.max_alokasi_per_saham
        if alokasi > max_alokasi:
            alokasi = max_alokasi
        alokasi = max(alokasi, total * settings.min_alokasi_per_saham)

        kode = ""
        if hasattr(r, "stock") and r.stock and hasattr(r.stock, "kode"):
            kode = r.stock.kode
        elif isinstance(r, dict):
            kode = r.get("kode", "")
        elif hasattr(r, "kode"):
            kode = r.kode

        risk_rating = getattr(r, "risk_rating", "MEDIUM")
        if risk_rating == "LOW":
            alasan = f"Skor {skor:.0f}/100 — risk LOW — stabil"
        else:
            alasan = f"Skor {skor:.0f}/100 — risk MEDIUM"

        allocations.append({
            "kode": kode,
            "skor": skor,
            "risk_rating": risk_rating,
            "alokasi_rp": round(alokasi),
            "persentase": round(alokasi / total * 100, 1),
            "alasan": alasan,
        })
    return allocations
