import os
import tempfile

import numpy as np

from src.database.db_manager import DatabaseManager
from src.auth.feature_extractor import FeatureExtractor, KeystrokeEvent, FeatureVector
from src.auth.template import BehaviorTemplate
from src.ml.knn_model import KNNModel
from src.ml.risk_scorer import RiskScorer


class ExperimentService:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.extractor = FeatureExtractor()
        self.knn = KNNModel(k=5)
        self.scorer = RiskScorer()

    # ─── Attack simulation helpers ───────────────────────────

    def _generate_random_events(self, password_len: int, seed: int = None) -> list[KeystrokeEvent]:
        rng = np.random.RandomState(seed)
        events = []
        t = 0.0
        for i in range(password_len):
            hold = max(0.03, rng.normal(0.15, 0.05))
            flight = max(0.02, rng.normal(0.12, 0.06))
            t += flight
            events.append(KeystrokeEvent(key=f"key{i}", press_time=t, release_time=t + hold))
            t += hold
        return events

    def _generate_imitation_events(self, ref_events: list[KeystrokeEvent], noise: float = 0.3) -> list[KeystrokeEvent]:
        rng = np.random.RandomState()
        events = []
        t = 0.0
        for e in ref_events:
            if e.is_backspace:
                continue
            hold = e.hold_time / 1000.0
            noisy_hold = max(0.02, hold * (1 + rng.normal(0, noise)))
            fake_hold_sec = noisy_hold
            events.append(KeystrokeEvent(key=e.key, press_time=t, release_time=t + fake_hold_sec))
            t += fake_hold_sec
        return events

    # ─── Attack experiments ──────────────────────────────────

    def simulate_password_leak_attack(self, user_id: int, password: str, n_attempts: int = 50) -> list[int]:
        """Attacker knows correct password but types differently."""
        user = self.db.get_user(user_id)
        if user is None or user["template_blob"] is None:
            return []
        template = BehaviorTemplate.from_json(user["template_blob"])
        scores = []
        for i in range(n_attempts):
            events = self._generate_random_events(len(password), seed=i + 1000)
            fv = self.extractor.extract(events)
            self.knn.fit(template.feature_vectors, template.std_vector)
            self_dists = self.knn.compute_self_distances(template.feature_vectors, template.std_vector)
            self.scorer.calibrate(self_dists)
            avg_dist = self.knn.get_average_distance(fv, template.std_vector)
            scores.append(self.scorer.score(avg_dist))
        return scores

    def simulate_imitation_attack(self, user_id: int, password: str,
                                   reference_events: list[KeystrokeEvent], n_attempts: int = 50) -> list[int]:
        """Attacker has observed user typing and tries to mimic."""
        user = self.db.get_user(user_id)
        if user is None or user["template_blob"] is None:
            return []
        template = BehaviorTemplate.from_json(user["template_blob"])
        scores = []
        for i in range(n_attempts):
            events = self._generate_imitation_events(reference_events, noise=0.2 + 0.02 * i)
            fv = self.extractor.extract(events)
            self.knn.fit(template.feature_vectors, template.std_vector)
            self_dists = self.knn.compute_self_distances(template.feature_vectors, template.std_vector)
            self.scorer.calibrate(self_dists)
            avg_dist = self.knn.get_average_distance(fv, template.std_vector)
            scores.append(self.scorer.score(avg_dist))
        return scores

    def simulate_random_input_attack(self, user_id: int, password: str, n_attempts: int = 50) -> list[int]:
        """Attacker inputs randomly with no knowledge."""
        return self.simulate_password_leak_attack(user_id, password, n_attempts)

    # ─── Metrics ─────────────────────────────────────────────

    def compute_far_frr(self, genuine_scores: list[int], impostor_scores: list[int],
                        thresholds: list[int] = None) -> dict:
        if thresholds is None:
            thresholds = list(range(10, 100, 5))
        results = []
        for t in thresholds:
            # Genuine rejected: risk >= t (FR)
            fr = sum(1 for s in genuine_scores if s >= t)
            frr = fr / len(genuine_scores) if genuine_scores else 0
            # Impostor accepted: risk < t (FA)
            fa = sum(1 for s in impostor_scores if s < t)
            far = fa / len(impostor_scores) if impostor_scores else 0
            results.append({"threshold": t, "far": far, "frr": frr, "eer_approx": abs(far - frr)})
        best = min(results, key=lambda r: r["eer_approx"])
        eer = (best["far"] + best["frr"]) / 2
        return {"far": best["far"], "frr": best["frr"], "eer": eer, "threshold": best["threshold"],
                "details": results}

    def run_full_experiment(self, user_id: int, password: str) -> dict:
        """Run all three attack types and return summary."""
        user = self.db.get_user(user_id)
        if user is None or user["template_blob"] is None:
            return {}
        template = BehaviorTemplate.from_json(user["template_blob"])
        reference_events = None
        # Use first sample as reference for imitation attack
        samples = self.db.get_samples(user_id, limit=1)
        if samples:
            fv = FeatureVector.from_json(samples[0]["features_json"])
            reference_events = [KeystrokeEvent(key="k", press_time=0, release_time=fv.mean_hold_time / 1000.0)]

        # Genuine scores: use self-distances from template
        self.knn.fit(template.feature_vectors, template.std_vector)
        self_dists = self.knn.compute_self_distances(template.feature_vectors, template.std_vector)
        self.scorer.calibrate(self_dists)
        genuine_scores = []
        for fv_obj in template.feature_vectors:
            d = self.knn.get_average_distance(fv_obj, template.std_vector)
            genuine_scores.append(self.scorer.score(d))

        # Attack scores
        leak_scores = self.simulate_password_leak_attack(user_id, password, n_attempts=50)
        imitation_scores = self.simulate_imitation_attack(user_id, password, reference_events, n_attempts=50)
        random_scores = self.simulate_random_input_attack(user_id, password, n_attempts=50)

        all_impostor = leak_scores + imitation_scores + random_scores
        metrics = self.compute_far_frr(genuine_scores, all_impostor)

        return {
            "genuine_scores": genuine_scores,
            "password_leak_scores": leak_scores,
            "imitation_scores": imitation_scores,
            "random_scores": random_scores,
            "far": metrics["far"],
            "frr": metrics["frr"],
            "eer": metrics["eer"],
            "best_threshold": metrics["threshold"],
        }
