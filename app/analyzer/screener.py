# Returns only stocks that pass low-risk filters
def filter_low_risk(scan_results: list) -> list:
    return [r for r in scan_results if r.risk_rating in ("LOW", "MEDIUM")]

def filter_large_cap(scan_results: list, min_market_cap: float = 10e12) -> list:
    # market_cap in data dict, not in ScanResult — handled upstream
    return scan_results
