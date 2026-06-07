import hashlib

from src.auth.feature_extractor import FeatureExtractor, FeatureVector, KeystrokeEvent
from src.auth.template import BehaviorTemplate
from src.database.db_manager import DatabaseManager
from src.ml.knn_model import KNNModel
from src.ml.risk_scorer import RiskScorer
from src.ml.adaptive_learner import AdaptiveLearner


class AuthService:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.extractor = FeatureExtractor()
        self.knn = KNNModel(k=5)
        self.scorer = RiskScorer()
        self.learner = AdaptiveLearner(alpha=0.8, window_size=20)
        # Continuous auth state
        self._ca_user_id: int = None
        self._ca_buffer: list[KeystrokeEvent] = []
        self._ca_callback: callable = None
        self._ca_job_id: str = None
        self._ca_consecutive_warnings: int = 0
        self._ca_ok: bool = True

    # ─── Registration ────────────────────────────────────────

    def register(self, username: str, password: str, events_list: list[list[KeystrokeEvent]]) -> bool:
        if self.db.get_user_by_username(username) is not None:
            raise ValueError("Username already exists")
        if len(events_list) < 5:
            raise ValueError("At least 5 samples required for registration")
        password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        feature_vectors = self.extractor.extract_batch(events_list)
        template = BehaviorTemplate(feature_vectors)
        user_id = self.db.create_user(username, password_hash, template.to_json())
        for fv in feature_vectors:
            self.db.save_sample(user_id, fv.to_json())
        # Calibrate scorer from self-distances
        self_dists = self.knn.compute_self_distances(feature_vectors, template.std_vector)
        self.scorer.calibrate(self_dists)
        return True

    # ─── Login ───────────────────────────────────────────────

    def login(self, username: str, password: str, events: list[KeystrokeEvent]) -> tuple[int, str]:
        user = self.db.get_user_by_username(username)
        if user is None:
            return (100, "user_not_found")
        password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        if password_hash != user["password_hash"]:
            self.db.save_login_log(user["id"], 100, "wrong_password")
            return (100, "wrong_password")
        if user["template_blob"] is None:
            self.db.save_login_log(user["id"], 0, "safe")
            return (0, "safe")
        if not events:
            self.db.save_login_log(user["id"], 100, "no_events")
            return (100, "no_events")
        template = BehaviorTemplate.from_json(user["template_blob"])
        fv = self.extractor.extract(events)
        self.knn.fit(template.feature_vectors, template.std_vector)
        self_dists = self.knn.compute_self_distances(template.feature_vectors, template.std_vector)
        self.scorer.calibrate(self_dists)
        self.knn.fit(template.feature_vectors, template.std_vector)
        avg_dist = self.knn.get_average_distance(fv, template.std_vector)
        risk = self.scorer.score(avg_dist)
        category = self.scorer.score_category(risk)
        self.db.save_login_log(user["id"], risk, category)
        # Save sample if risk low enough
        if risk < 30:
            self.db.save_sample(user["id"], fv.to_json())
        return (risk, category)

    # ─── Continuous Authentication ───────────────────────────

    def start_continuous_auth(self, user_id: int, vault_key: bytes,
                              on_risk_change: callable, tk_widget) -> bool:
        user = self.db.get_user(user_id)
        if user is None or user["template_blob"] is None:
            return False
        self._ca_user_id = user_id
        self._ca_callback = on_risk_change
        self._ca_consecutive_warnings = 0
        self._ca_ok = True
        self._schedule_check(tk_widget)
        return True

    def stop_continuous_auth(self, tk_widget):
        if self._ca_job_id is not None:
            tk_widget.after_cancel(self._ca_job_id)
            self._ca_job_id = None
        self._ca_user_id = None

    def feed_continuous_events(self, events: list[KeystrokeEvent]):
        self._ca_buffer.extend(events)
        if len(self._ca_buffer) > 50:
            self._ca_buffer = self._ca_buffer[-50:]

    def _schedule_check(self, tk_widget):
        self._ca_job_id = tk_widget.after(5000, lambda: self._check_continuous_auth(tk_widget))

    def _check_continuous_auth(self, tk_widget):
        user = self.db.get_user(self._ca_user_id)
        if user is None:
            return
        if len(self._ca_buffer) < 10:
            self._schedule_check(tk_widget)
            return
        template = BehaviorTemplate.from_json(user["template_blob"])
        effective_events = self._ca_buffer[-30:]
        fv = self.extractor.extract(effective_events)
        self.knn.fit(template.feature_vectors, template.std_vector)
        avg_dist = self.knn.get_average_distance(fv, template.std_vector)
        self_dists = self.knn.compute_self_distances(template.feature_vectors, template.std_vector)
        self.scorer.calibrate(self_dists)
        risk = self.scorer.score(avg_dist)
        category = self.scorer.score_category(risk)
        if category == "high_risk":
            self._ca_ok = False
            self._ca_callback("high_risk", risk, "Vault locked due to anomaly")
        elif category == "suspicious":
            self._ca_consecutive_warnings += 1
            if self._ca_consecutive_warnings >= 3:
                self._ca_callback("re_auth", risk, "Please re-authenticate")
                self._ca_consecutive_warnings = 0
        else:
            self._ca_consecutive_warnings = 0
            self._ca_ok = True
        self._schedule_check(tk_widget)

    # ─── Adaptive Update ─────────────────────────────────────

    def trigger_adaptive_update(self, user_id: int, recent_events: list[KeystrokeEvent]) -> bool:
        user = self.db.get_user(user_id)
        if user is None or user["template_blob"] is None:
            return False
        template = BehaviorTemplate.from_json(user["template_blob"])
        fv = self.extractor.extract(recent_events)
        self.knn.fit(template.feature_vectors, template.std_vector)
        avg_dist = self.knn.get_average_distance(fv, template.std_vector)
        self_dists = self.knn.compute_self_distances(template.feature_vectors, template.std_vector)
        self.scorer.calibrate(self_dists)
        risk = self.scorer.score(avg_dist)
        if not self.learner.should_update(risk, self._ca_ok, avg_dist, template):
            return False
        self.learner.update_ema(template, fv)
        self.learner.update_sliding_window(template)
        self.db.update_user_template(user_id, template.to_json())
        self.db.save_sample(user_id, fv.to_json())
        return True
