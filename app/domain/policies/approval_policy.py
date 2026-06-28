def requires_human_approval(priority_score: float, recommendation: str) -> bool:
    high_risk_actions = ("contain", "disable", "block", "isolate")
    return priority_score >= 8.0 or any(token in recommendation.lower() for token in high_risk_actions)

