from app.services.risk_engine import RiskEngine


def test_risk_engine_increases_priority_for_kev_and_internet_exposed_assets() -> None:
    engine = RiskEngine()
    score = engine.calculate(base_score=7.5, asset_criticality=5, internet_exposed=True, kev_flag=True)
    assert score.total > 10.0

