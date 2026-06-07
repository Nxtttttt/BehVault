import numpy as np

from src.auth.feature_extractor import FeatureVector
from src.auth.template import BehaviorTemplate


class AdaptiveLearner:
    def __init__(self, alpha: float = 0.8, window_size: int = 20):
        self.alpha = alpha
        self.window_size = window_size

    def should_update(self, risk_score: int, continuous_auth_ok: bool,
                      distance: float, template: BehaviorTemplate) -> bool:
        if risk_score >= 30:
            return False
        if not continuous_auth_ok:
            return False
        if len(template.feature_vectors) < 2:
            return True
        # Check distance is within 2 sigma of template self-distances
        arrays = np.array([fv.to_array() for fv in template.feature_vectors])
        center = np.mean(arrays, axis=0)
        self_dists = [float(np.linalg.norm(arrays[i] - center)) for i in range(len(arrays))]
        mu = np.mean(self_dists)
        sigma = np.std(self_dists, ddof=1) if len(self_dists) > 1 else 1e-6
        sigma = max(sigma, 1e-6)
        return distance <= mu + 2.0 * sigma

    def update_ema(self, template: BehaviorTemplate, new_sample: FeatureVector) -> BehaviorTemplate:
        new_mean = self.alpha * template.mean_vector + (1 - self.alpha) * new_sample.to_array()
        updated_fv = FeatureVector.from_array(new_mean)
        # Keep the original samples but append the new one
        template.add_sample(new_sample)
        # Recompute with EMA weight: override mean vector
        # The template recompute uses equal weights; we replace with EMA
        template.mean_vector = new_mean
        return template

    def update_sliding_window(self, template: BehaviorTemplate) -> BehaviorTemplate:
        if len(template.feature_vectors) > self.window_size:
            template.feature_vectors = template.feature_vectors[-self.window_size:]
            template._recompute()
        return template
