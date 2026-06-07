"""ML module tests: KNN, RiskScorer, AdaptiveLearner."""

import sys
import os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.auth.feature_extractor import FeatureVector
from src.auth.template import BehaviorTemplate
from src.ml.knn_model import KNNModel
from src.ml.risk_scorer import RiskScorer
from src.ml.adaptive_learner import AdaptiveLearner


def generate_feature_vectors(n: int, seed: int = 42, noise: float = 0.1) -> list[FeatureVector]:
    rng = np.random.RandomState(seed)
    base = np.array([120.0, 25.0, 180.0, 60.0, 70.0, 18.0, 100.0, 40.0, 2.0, 1500.0])
    fvs = []
    for i in range(n):
        noisy = base + rng.normal(0, noise * base)
        fvs.append(FeatureVector.from_array(noisy))
    return fvs


def test_knn_fit_predict():
    fvs = generate_feature_vectors(10)
    knn = KNNModel(k=5)
    knn.fit(fvs)
    distances, indices = knn.predict(fvs[0])
    assert len(distances) == 5
    assert distances[0] < 0.01  # self distance near zero


def test_knn_average_distance():
    fvs = generate_feature_vectors(10)
    knn = KNNModel(k=5)
    knn.fit(fvs)
    self_avg = knn.get_average_distance(fvs[0])
    # Out-of-sample should have larger distance
    outlier = generate_feature_vectors(1, seed=999, noise=2.0)[0]
    outlier_avg = knn.get_average_distance(outlier)
    assert outlier_avg > self_avg, "Outlier distance should exceed self-distance"


def test_knn_normalization():
    fvs = generate_feature_vectors(10)
    std_vector = np.array([1.0] * 10) + np.random.random(10) * 10
    knn = KNNModel(k=5)
    knn.fit(fvs, std_vector)
    avg = knn.get_average_distance(fvs[0], std_vector)
    assert avg >= 0


def test_risk_scorer_calibrate():
    self_dists = [0.5, 0.6, 0.4, 0.55, 0.45, 0.7, 0.5, 0.6, 0.55, 0.5]
    scorer = RiskScorer()
    scorer.calibrate(self_dists)
    assert scorer._calibrated
    assert scorer.safe_threshold > 0
    assert scorer.high_risk_threshold > scorer.safe_threshold


def test_risk_scorer_output_range():
    self_dists = [0.1, 0.2, 0.15, 0.25, 0.2, 0.18, 0.22, 0.19, 0.21, 0.17]
    scorer = RiskScorer()
    scorer.calibrate(self_dists)
    assert scorer.score(0.05) <= 30  # close → safe
    assert scorer.score(10.0) >= 70  # far → high risk
    assert 0 <= scorer.score(0.3) <= 100


def test_risk_scorer_categories():
    scorer = RiskScorer()
    scorer.calibrate([0.1, 0.2, 0.15])
    assert scorer.score_category(10) == "safe"
    assert scorer.score_category(50) == "suspicious"
    assert scorer.score_category(90) == "high_risk"


def test_adaptive_learner_ema():
    fvs = generate_feature_vectors(10)
    template = BehaviorTemplate(fvs)
    learner = AdaptiveLearner(alpha=0.8)
    old_mean = template.mean_vector.copy()
    new_sample = generate_feature_vectors(1, seed=99, noise=0.2)[0]
    updated = learner.update_ema(template, new_sample)
    new_mean = updated.mean_vector
    assert not np.allclose(old_mean, new_mean)


def test_adaptive_learner_sliding_window():
    fvs = generate_feature_vectors(25)
    template = BehaviorTemplate(fvs)
    learner = AdaptiveLearner(window_size=20)
    assert len(template) == 25
    updated = learner.update_sliding_window(template)
    assert len(updated) == 20


if __name__ == "__main__":
    test_knn_fit_predict()
    test_knn_average_distance()
    test_knn_normalization()
    test_risk_scorer_calibrate()
    test_risk_scorer_output_range()
    test_risk_scorer_categories()
    test_adaptive_learner_ema()
    test_adaptive_learner_sliding_window()
    print("All ML tests passed!")
