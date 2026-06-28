from app.domain.value_objects.risk_score import RiskScore


class RiskEngine:
    def calculate(
        self,
        base_score: float,
        asset_criticality: int = 3,
        internet_exposed: bool = False,
        kev_flag: bool = False,
    ) -> RiskScore:
        asset_modifier = 0.6 * asset_criticality
        exploit_modifier = 1.5 if internet_exposed else 0.0
        exploit_modifier += 1.5 if kev_flag else 0.0
        return RiskScore(
            base_score=base_score,
            asset_modifier=asset_modifier,
            exploit_modifier=exploit_modifier,
        )

