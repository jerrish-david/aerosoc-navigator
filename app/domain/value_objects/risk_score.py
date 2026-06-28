from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RiskScore:
    base_score: float
    asset_modifier: float
    exploit_modifier: float

    @property
    def total(self) -> float:
        return round(self.base_score + self.asset_modifier + self.exploit_modifier, 2)

