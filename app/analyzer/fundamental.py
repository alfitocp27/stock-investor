def calculate_fundamental_score(data: dict) -> tuple[float, dict]:
    pe = data.get("pe")
    pbv = data.get("pbv")
    roe = data.get("roe")
    debt_eq = data.get("debt_to_equity")
    div_yield = data.get("dividend_yield")

    def score_pe(p):
        if p is None: return 0.0
        if p < 15: return 100.0
        if p <= 25: return float(100.0 - (p - 15) * 5)
        return float(max(0.0, 50.0 - (p - 25) * 2.5))

    def score_pbv(b):
        if b is None: return 0.0
        if b < 1.5: return 100.0
        if b <= 3.0: return float(100.0 - (b - 1.5) * 20)
        return float(max(0.0, 50.0 - (b - 3.0) * 5))

    def score_roe(r):
        if r is None: return 0.0
        pct = r * 100 if r < 1 else r  # handle decimal vs percent
        if pct > 15: return 100.0
        if pct >= 5: return float(50.0 + (pct - 5) * 5)
        return float(max(0.0, pct / 5 * 50))

    def score_debt(d):
        if d is None: return 50.0
        if d < 1.0: return 100.0
        if d <= 2.0: return float(100.0 - (d - 1.0) * 50)
        return 0.0

    def score_yield(y):
        if y is None: return 0.0
        pct = y * 100 if y < 1 else y  # handle decimal vs percent
        if pct > 4: return 100.0
        if pct >= 2: return float(50.0 + (pct - 2) * 25)
        return float(max(0.0, pct / 2 * 50))

    breakdown = {
        "pe_score": score_pe(pe),
        "pbv_score": score_pbv(pbv),
        "roe_score": score_roe(roe),
        "debt_score": score_debt(debt_eq),
        "yield_score": score_yield(div_yield),
    }
    score = sum(breakdown.values()) / len(breakdown)
    return float(score), breakdown
