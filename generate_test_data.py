"""Generate all screenshots, charts, and test data for the report."""
import sys, os, hashlib, json, tempfile, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

from src.database.db_manager import DatabaseManager
from src.auth.feature_extractor import FeatureExtractor, KeystrokeEvent, FeatureVector
from src.auth.template import BehaviorTemplate
from src.ml.knn_model import KNNModel
from src.ml.risk_scorer import RiskScorer
from src.ml.adaptive_learner import AdaptiveLearner
from src.services.experiment_service import ExperimentService
from src.services.auth_service import AuthService
from src.viz.charts import ChartGenerator
from src.crypto.sm4_core import SM4Core
from src.crypto.sm4_mode import SM4ECB, SM4CBC
from src.crypto.key_manager import KeyManager
from src.crypto.file_crypto import FileEncryptor
from src.vault.vault_manager import VaultManager

OUTDIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(OUTDIR, exist_ok=True)
RESULTS = {}

def save_chart(data: bytes, name: str):
    path = os.path.join(OUTDIR, name)
    with open(path, "wb") as f:
        f.write(data)
    print(f"  Saved: {name}")

# ================================================================
# 1. Generate realistic keystroke data & template
# ================================================================
print("=== 1. Generating realistic data ===")
rng = np.random.RandomState(42)
password = "behvault2024"
extractor = FeatureExtractor()

# Registration: 10 samples with human-like variation
fvs = []
for s in range(10):
    speed = 1.0 + rng.normal(0, 0.12)
    events = []
    t = 0.0
    for ch in password:
        hold = max(0.04, rng.normal(0.11, 0.03) * speed)
        flight = max(0.02, rng.normal(0.09, 0.04) * speed)
        if rng.random() < 0.08:
            flight += rng.exponential(0.04)
        t += flight
        events.append(KeystrokeEvent(key=ch, press_time=t, release_time=t + hold))
        t = t + hold
    fvs.append(extractor.extract(events))

template = BehaviorTemplate(fvs)

# Genuine login samples (50)
genuine_fvs = []
for s in range(50):
    speed = 1.0 + rng.normal(0, 0.12)
    events = []
    t = 0.0
    for ch in password:
        hold = max(0.04, rng.normal(0.11, 0.03) * speed)
        flight = max(0.02, rng.normal(0.09, 0.04) * speed)
        t += flight
        events.append(KeystrokeEvent(key=ch, press_time=t, release_time=t + hold))
        t = t + hold
    genuine_fvs.append(extractor.extract(events))

# Impostor samples (50)
impostor_fvs = []
impostor_rng = np.random.RandomState(999)
for s in range(50):
    speed = 1.4 + impostor_rng.normal(0, 0.3)
    events = []
    t = 0.0
    for ch in password:
        hold = max(0.03, impostor_rng.normal(0.22, 0.08) * speed)
        flight = max(0.01, impostor_rng.normal(0.16, 0.10) * speed)
        t += flight
        events.append(KeystrokeEvent(key=ch, press_time=t, release_time=t + hold))
        t = t + hold
    impostor_fvs.append(extractor.extract(events))

# Compute scores
knn = KNNModel(k=5)
scorer = RiskScorer()
self_dists = knn.compute_self_distances(fvs, template.std_vector)
scorer.calibrate(self_dists)

print(f"  Template: {len(fvs)} vectors, mu_d={scorer.mu_d:.2f}, sigma_d={scorer.sigma_d:.2f}")

genuine_scores = []
for fv in genuine_fvs:
    knn.fit(template.feature_vectors, template.std_vector)
    sd = knn.compute_self_distances(template.feature_vectors, template.std_vector)
    scorer.calibrate(sd)
    knn.fit(template.feature_vectors, template.std_vector)
    d = knn.get_average_distance(fv, template.std_vector)
    genuine_scores.append(scorer.score(d))

impostor_scores = []
for fv in impostor_fvs:
    knn.fit(template.feature_vectors, template.std_vector)
    sd = knn.compute_self_distances(template.feature_vectors, template.std_vector)
    scorer.calibrate(sd)
    knn.fit(template.feature_vectors, template.std_vector)
    d = knn.get_average_distance(fv, template.std_vector)
    impostor_scores.append(scorer.score(d))

safe_cnt = sum(1 for s in genuine_scores if s <= 30)
susp_cnt = sum(1 for s in genuine_scores if 30 < s <= 70)
high_cnt = sum(1 for s in genuine_scores if s > 70)
imp_rejected = sum(1 for s in impostor_scores if s > 30)

print(f"  Genuine: safe={safe_cnt}, suspicious={susp_cnt}, high_risk={high_cnt}")
print(f"  Impostor rejected (>30): {imp_rejected}/50")
RESULTS["genuine_stats"] = {"safe": safe_cnt, "suspicious": susp_cnt, "high_risk": high_cnt}
RESULTS["impostor_rejected"] = imp_rejected

# ================================================================
# 2. Generate charts
# ================================================================
print("\n=== 2. Generating charts ===")

# Hold time curve
bytes_hold = ChartGenerator.hold_time_curve(fvs, "Hold Time per Registration Sample")
save_chart(bytes_hold, "01_hold_time_curve.png")

# Flight time curve
bytes_flight = ChartGenerator.flight_time_curve(fvs, "Flight Time per Registration Sample")
save_chart(bytes_flight, "02_flight_time_curve.png")

# Feature distribution
bytes_dist = ChartGenerator.feature_distribution(fvs, "10-Dimensional Feature Distribution")
save_chart(bytes_dist, "03_feature_distribution.png")

# User vs Attacker
bytes_compare = ChartGenerator.user_vs_attacker(genuine_scores, impostor_scores,
    "Genuine User vs Impostor Risk Score Distribution")
save_chart(bytes_compare, "04_user_vs_attacker.png")

# Risk timeline (genuine + impostor)
combined_scores = genuine_scores[:20] + impostor_scores[:20]
bytes_timeline = ChartGenerator.risk_timeline(combined_scores, "Risk Score Timeline (20 Genuine + 20 Impostor)")
save_chart(bytes_timeline, "05_risk_timeline.png")

# FAR/FRR curve
# Compute FAR/FRR directly
thresholds = list(range(10, 100, 5))
far_list, frr_list = [], []
for t in thresholds:
    fa = sum(1 for s in impostor_scores if s < t) / len(impostor_scores)
    fr = sum(1 for s in genuine_scores if s >= t) / len(genuine_scores)
    far_list.append(fa)
    frr_list.append(fr)
bytes_far = ChartGenerator.far_frr_curve(far_list, frr_list, thresholds, "FAR/FRR vs Threshold")
save_chart(bytes_far, "06_far_frr_curve.png")

# FAR/FRR data
far_at_30 = sum(1 for s in impostor_scores if s < 30) / len(impostor_scores)
frr_at_30 = sum(1 for s in genuine_scores if s >= 30) / len(genuine_scores)
eer_idx = min(range(len(thresholds)), key=lambda i: abs(far_list[i] - frr_list[i]))
RESULTS["far"] = far_at_30
RESULTS["frr"] = frr_at_30
RESULTS["eer"] = (far_list[eer_idx] + frr_list[eer_idx]) / 2
RESULTS["eer_threshold"] = thresholds[eer_idx]
print(f"  FAR@30={far_at_30:.3f}, FRR@30={frr_at_30:.3f}, EER={RESULTS['eer']:.3f}")

# ================================================================
# 3. Attack simulation via ExperimentService
# ================================================================
print("\n=== 3. Attack simulation ===")

db_path = os.path.join(tempfile.gettempdir(), "report_test.db")
try: os.remove(db_path)
except: pass
db = DatabaseManager(db_path)

uid = db.create_user("report_user", hashlib.sha256(password.encode()).hexdigest(),
                     template.to_json())
for fv in fvs:
    db.save_sample(uid, fv.to_json())
exp_svc = ExperimentService(db)
exp_svc.knn = KNNModel(k=5)
exp_svc.scorer = RiskScorer()
exp_svc.extractor = FeatureExtractor()

full = exp_svc.run_full_experiment(uid, password)
RESULTS["experiment"] = {
    "far": full["far"], "frr": full["frr"], "eer": full["eer"],
    "best_threshold": full["best_threshold"],
    "leak_mean": np.mean(full["password_leak_scores"]),
    "imitation_mean": np.mean(full["imitation_scores"]),
    "random_mean": np.mean(full["random_scores"]),
}
print(f"  Password leak mean risk: {RESULTS['experiment']['leak_mean']:.1f}")
print(f"  Imitation mean risk: {RESULTS['experiment']['imitation_mean']:.1f}")
print(f"  Random mean risk: {RESULTS['experiment']['random_mean']:.1f}")

# Attack comparison chart
attack_results = {
    "password_leak_scores": full["password_leak_scores"],
    "imitation_scores": full["imitation_scores"],
    "random_scores": full["random_scores"],
}
bytes_attack = ChartGenerator.attack_comparison(attack_results, "Attack Type Comparison")
save_chart(bytes_attack, "07_attack_comparison.png")

# ================================================================
# 4. Run unit tests
# ================================================================
print("\n=== 4. Running unit tests ===")

# Run the existing test files
test_results = {}
for test_name, test_file in [
    ("SM4 Core", "tests/test_sm4.py"),
    ("Authentication", "tests/test_auth.py"),
    ("Machine Learning", "tests/test_ml.py"),
    ("Vault", "tests/test_vault.py"),
]:
    import subprocess
    result = subprocess.run(
        [sys.executable, test_file],
        capture_output=True, text=True, cwd=os.path.dirname(__file__), timeout=60
    )
    passed = "FAILED" not in result.stdout and "Error" not in result.stdout and result.returncode == 0
    test_results[test_name] = {
        "passed": passed,
        "output": result.stdout[-500:] if result.stdout else result.stderr[:500]
    }
    print(f"  {test_name}: {'PASSED' if passed else 'FAILED'}")

RESULTS["unit_tests"] = test_results

# ================================================================
# 5. SM4 correctness verification
# ================================================================
print("\n=== 5. SM4 verification ===")
key = bytes.fromhex("0123456789abcdeffedcba9876543210")
# Test vector from GB/T 32907-2016
plaintext = bytes.fromhex("0123456789abcdeffedcba9876543210")
ct = SM4Core.encrypt_block(plaintext, key)
# Known SM4 test vector
expected_ct = bytes.fromhex("681edf34d206965e86b3e94f536e4246")
sm4_correct = ct == expected_ct
print(f"  SM4 test vector match: {sm4_correct}")
if not sm4_correct:
    print(f"    Got: {ct.hex()}, Expected: {expected_ct.hex()}")
RESULTS["sm4_correct"] = sm4_correct

# ================================================================
# 6. Adaptive learning comparison
# ================================================================
print("\n=== 6. Adaptive learning experiment ===")

# Fixed template baseline
fixed_scores = genuine_scores  # Already computed above

# Simulate adaptive template over time
adaptive_template = BehaviorTemplate(fvs[:10])
learner = AdaptiveLearner(alpha=0.8, window_size=20)
adaptive_scores = []
for i, fv in enumerate(genuine_fvs[:30]):
    knn.fit(adaptive_template.feature_vectors, adaptive_template.std_vector)
    sd = knn.compute_self_distances(adaptive_template.feature_vectors, adaptive_template.std_vector)
    scorer.calibrate(sd)
    knn.fit(adaptive_template.feature_vectors, adaptive_template.std_vector)
    d = knn.get_average_distance(fv, adaptive_template.std_vector)
    risk = scorer.score(d)
    adaptive_scores.append(risk)
    # Update if safe
    if risk < 30:
        learner.update_ema(adaptive_template, fv)
        learner.update_sliding_window(adaptive_template)

fixed_frr = sum(1 for s in fixed_scores[:30] if s >= 30) / 30
adaptive_frr = sum(1 for s in adaptive_scores if s >= 30) / 30
RESULTS["adaptive"] = {"fixed_frr": fixed_frr, "adaptive_frr": adaptive_frr}
print(f"  Fixed template FRR: {fixed_frr:.3f}")
print(f"  Adaptive template FRR: {adaptive_frr:.3f}")
print(f"  Improvement: {(fixed_frr - adaptive_frr)*100:.1f}%")

# ================================================================
# 7. Vault encryption performance
# ================================================================
print("\n=== 7. Vault performance ===")
import time

# Test with various file sizes
FILE_SIZES = [
    ("1 KB", os.urandom(1024)),
    ("10 KB", os.urandom(10240)),
    ("100 KB", os.urandom(102400)),
    ("1 MB", os.urandom(1048576)),
]
vault_key = bytes.fromhex("0123456789abcdeffedcba9876543210")
perf_results = {}
for label, data in FILE_SIZES:
    t0 = time.perf_counter()
    enc = FileEncryptor.encrypt_content(data, key)
    t1 = time.perf_counter()
    dec = FileEncryptor.decrypt_content(enc, key)
    t2 = time.perf_counter()
    assert dec == data
    perf_results[label] = {"encrypt_ms": (t1-t0)*1000, "decrypt_ms": (t2-t1)*1000}
    print(f"  {label}: encrypt={perf_results[label]['encrypt_ms']:.1f}ms, decrypt={perf_results[label]['decrypt_ms']:.1f}ms")

RESULTS["vault_performance"] = perf_results

# ================================================================
# Save all results
# ================================================================
print("\n=== 8. Saving results ===")
RESULTS["template_stats"] = {
    "n_samples": len(fvs),
    "mean_hold": float(np.mean([fv.mean_hold_time for fv in fvs])),
    "std_hold": float(np.std([fv.mean_hold_time for fv in fvs])),
    "mean_flight": float(np.mean([fv.mean_flight_time for fv in fvs])),
    "std_flight": float(np.std([fv.mean_flight_time for fv in fvs])),
    "mu_d": float(scorer.mu_d),
    "sigma_d": float(scorer.sigma_d),
    "safe_threshold": float(scorer.safe_threshold),
    "high_risk_threshold": float(scorer.high_risk_threshold),
}

# Write numerical results as JSON
results_path = os.path.join(OUTDIR, "results.json")
# Convert numpy types to native Python
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, (np.ndarray,)): return obj.tolist()
        return super().default(obj)

with open(results_path, "w", encoding="utf-8") as f:
    json.dump(RESULTS, f, indent=2, ensure_ascii=False, cls=NpEncoder)
print(f"  Saved results to {results_path}")

db.conn.close()
try: os.remove(db_path)
except: pass

print("\n=== DONE ===")
print(f"All screenshots saved to: {OUTDIR}")
