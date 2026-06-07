import numpy as np


class RiskScorer:
    SAFE_THRESHOLD_SIGMA = 1.5
    HIGH_RISK_THRESHOLD_SIGMA = 3.0

    def __init__(self):
        self.mu_d: float = 0.0
        self.sigma_d: float = 0.0
        self.safe_threshold: float = 0.0
        self.high_risk_threshold: float = 0.0
        self._calibrated = False

    def calibrate(self, self_distances: list[float]):
        if len(self_distances) < 2:
            self.mu_d = self_distances[0] if self_distances else 0.0
            self.sigma_d = 1e-6
        else:
            self.mu_d = float(np.mean(self_distances))
            self.sigma_d = float(np.std(self_distances, ddof=1))
        self.sigma_d = max(self.sigma_d, 1e-6)
        self.safe_threshold = self.mu_d + self.SAFE_THRESHOLD_SIGMA * self.sigma_d
        self.high_risk_threshold = self.mu_d + self.HIGH_RISK_THRESHOLD_SIGMA * self.sigma_d
        self._calibrated = True

    def score(self, distance: float) -> int:
        if not self._calibrated:
            return 100
        if distance <= self.safe_threshold:
            risk = int((distance / self.safe_threshold) * 30)
        elif distance <= self.high_risk_threshold:
            t = (distance - self.safe_threshold) / (self.high_risk_threshold - self.safe_threshold)
            risk = 30 + int(t * 40)
        else:
            t = min((distance - self.high_risk_threshold) / self.high_risk_threshold, 1.0)
            risk = 70 + int(t * 30)
        return min(risk, 100)

    def score_category(self, score: int) -> str:
        if score <= 30:
            return "safe"
        elif score <= 70:
            return "suspicious"
        else:
            return "high_risk"
