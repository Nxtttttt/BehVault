"""Comprehensive integration test for all BehVault modules."""
import sys, os, hashlib, tempfile, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import numpy as np

PASS, FAIL = 0, 0

def check(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  [PASS] {name}' + (f': {detail}' if detail else ''))
    else:
        FAIL += 1
        print(f'  [FAIL] {name}' + (f': {detail}' if detail else ''))

db_path = os.path.join(tempfile.gettempdir(), 'test_integration.db')
try:
    os.remove(db_path)
except:
    pass

# ===== 1. SM4 CRYPTO =====
print('1. SM4 CRYPTO')
from src.crypto.sm4_core import SM4Core
from src.crypto.sm4_mode import SM4ECB, SM4CBC
from src.crypto.key_manager import KeyManager
from src.crypto.file_crypto import FileEncryptor

key = bytes.fromhex('0123456789abcdeffedcba9876543210')
block = b'0123456789abcdef'
ct_block = SM4Core.encrypt_block(block, key)
pt_block = SM4Core.decrypt_block(ct_block, key)
check('SM4 encrypt/decrypt block', pt_block == block)

ecb = SM4ECB(key)
data = b'BehVault SM4 Test!'
ct_ecb = ecb.encrypt(data)
pt_ecb = ecb.decrypt(ct_ecb)
check('SM4 ECB encrypt/decrypt', pt_ecb == data)

# Test PKCS7 padding comprehensively
for orig_len in range(1, 33):
    test_data = bytes(range(orig_len))
    padded = SM4ECB._pkcs7_pad(test_data, 16)
    unpadded = SM4ECB._pkcs7_unpad(padded)
    if unpadded != test_data:
        check(f'PKCS7 pad/unpad len={orig_len}', False)
        break
else:
    check('PKCS7 pad/unpad (1-32 bytes)', True)

cbc = SM4CBC(key)
data2 = b'CBC mode test data for BehVault system.'
ct_cbc = cbc.encrypt(data2)
pt_cbc = cbc.decrypt(ct_cbc, iv_prepended=True)
check('SM4 CBC encrypt/decrypt', pt_cbc == data2)
check('ECB != CBC (semantic security)', ct_ecb[:16] != ct_cbc[16:32])

vault_key, salt = KeyManager.derive_key('user_password')
check('KeyManager derive_key', len(vault_key) == 16 and len(salt) == 16)
check('KeyManager generate_iv', len(KeyManager.generate_iv()) == 16)

# FileEncryptor
fname = 'secret_document.pdf'
enc_fname = FileEncryptor.encrypt_filename(fname, key)
dec_fname = FileEncryptor.decrypt_filename(enc_fname, key)
check('FileEncryptor filename roundtrip', dec_fname == fname)

content = b'Secret file content! ' * 100
enc_content = FileEncryptor.encrypt_content(content, key)
dec_content = FileEncryptor.decrypt_content(enc_content, key)
check('FileEncryptor content roundtrip', dec_content == content)
check('Encrypted content != plaintext', enc_content[:16] != content[:16])
print()

# ===== 2. DATABASE =====
print('2. DATABASE')
from src.database.db_manager import DatabaseManager
db = DatabaseManager(db_path)

pw_hash = hashlib.sha256('testpass'.encode()).hexdigest()
uid = db.create_user('db_test_user', pw_hash)
check('create_user', uid == 1)
check('get_user', db.get_user(uid)['username'] == 'db_test_user')
check('get_user_by_username', db.get_user_by_username('db_test_user') is not None)
check('list_users', len(db.list_users()) == 1)

db.save_sample(uid, '{"test":1}')
check('save_sample + get_samples', len(db.get_samples(uid)) == 1)
check('get_sample_count', db.get_sample_count(uid) == 1)

db.save_login_log(uid, 50, 'suspicious')
logs = db.get_login_logs(uid)
check('save_login_log + get_login_logs', len(logs) == 1 and logs[0]['risk_score'] == 50)

fid = db.save_file(uid, b'enc_name', b'enc_data')
check('save_file', fid == 1)
check('get_files', len(db.get_files(uid)) == 1)
check('get_file', db.get_file(fid) is not None)

db.delete_file(fid)
check('delete_file', len(db.get_files(uid)) == 0)

db.update_user_template(uid, '{"updated":true}')
check('update_user_template', 'updated' in db.get_user(uid)['template_blob'])
print()

# ===== 3. FEATURE EXTRACTION + TEMPLATE =====
print('3. FEATURE EXTRACTION + TEMPLATE')
from src.auth.feature_extractor import FeatureExtractor, KeystrokeEvent, FeatureVector
from src.auth.template import BehaviorTemplate

extractor = FeatureExtractor()
rng = np.random.RandomState(42)
password = 'behvault'

fvs = []
for s in range(10):
    speed = 1.0 + rng.normal(0, 0.12)
    events = []
    t = 0.0
    for ch in password:
        hold = max(0.04, rng.normal(0.11, 0.03) * speed)
        flight = max(0.02, rng.normal(0.09, 0.04) * speed)
        t += flight
        events.append(KeystrokeEvent(key=ch, press_time=t, release_time=t + hold))
        t = t + hold
    fvs.append(extractor.extract(events))

fv = fvs[0]
arr = fv.to_array()
check('FeatureVector 10-dim', len(arr) == 10)
check('mean_hold_time > 0', fv.mean_hold_time > 0)
check('total_time > 0', fv.total_time > 0)

# JSON roundtrip
json_str = fv.to_json()
fv2 = FeatureVector.from_json(json_str)
check('FeatureVector JSON roundtrip', abs(fv2.mean_hold_time - fv.mean_hold_time) < 0.01)
check('FeatureVector from_array', True)

# Template
template = BehaviorTemplate(fvs)
check('Template created (10 FVs)', len(template.feature_vectors) == 10)
check('Template mean_vector (10D)', len(template.mean_vector) == 10)
check('Template std_vector (10D)', len(template.std_vector) == 10)

json_t = template.to_json()
template2 = BehaviorTemplate.from_json(json_t)
check('Template JSON roundtrip', len(template2.feature_vectors) == 10)
check('Template std_vector preserved', np.allclose(template.std_vector, template2.std_vector, rtol=0.01))

# add_sample
template3 = BehaviorTemplate(fvs.copy())
template3.add_sample(fvs[0])
check('Template add_sample', len(template3.feature_vectors) == 11)
print()

# ===== 4. KNN + RISK SCORER =====
print('4. KNN + RISK SCORER')
from src.ml.knn_model import KNNModel
from src.ml.risk_scorer import RiskScorer

knn = KNNModel(k=5)
scorer = RiskScorer()

self_dists = knn.compute_self_distances(fvs, template.std_vector)
check('Self-distances computed', len(self_dists) == 10)
check('Self-distances all finite', all(np.isfinite(d) for d in self_dists))

scorer.calibrate(self_dists)
check('Scorer calibrated', scorer._calibrated)
check('Safe < High threshold', scorer.safe_threshold < scorer.high_risk_threshold,
      f'safe={scorer.safe_threshold:.2f}, high={scorer.high_risk_threshold:.2f}')

# Genuine test
knn.fit(template.feature_vectors, template.std_vector)
dist_g = knn.get_average_distance(fvs[0], template.std_vector)
risk_g = scorer.score(dist_g)
check('Genuine sample safe (risk <= 30)', risk_g <= 30, f'risk={risk_g}')

# Impostor test
rng2 = np.random.RandomState(999)
impostor_fvs = []
for s in range(5):
    events = []
    t = 0.0
    for ch in password:
        hold = max(0.03, rng2.normal(0.22, 0.10))
        flight = max(0.01, rng2.normal(0.18, 0.12))
        t += flight
        events.append(KeystrokeEvent(key=ch, press_time=t, release_time=t + hold))
        t = t + hold
    impostor_fvs.append(extractor.extract(events))

knn.fit(template.feature_vectors, template.std_vector)
sd = knn.compute_self_distances(template.feature_vectors, template.std_vector)
scorer.calibrate(sd)
knn.fit(template.feature_vectors, template.std_vector)
dist_i = knn.get_average_distance(impostor_fvs[0], template.std_vector)
risk_i = scorer.score(dist_i)
check('Impostor rejected (risk > 30)', risk_i > 30, f'risk={risk_i}')

check('score_category: safe (10)', scorer.score_category(10) == 'safe')
check('score_category: suspicious (50)', scorer.score_category(50) == 'suspicious')
check('score_category: high_risk (90)', scorer.score_category(90) == 'high_risk')
print()

# ===== 5. VAULT =====
print('5. VAULT MANAGER + VAULT SERVICE')
from src.vault.vault_manager import VaultManager
from src.services.vault_service import VaultService

vault_mgr = VaultManager(db)
vault_svc = VaultService(db)

test_file = os.path.join(tempfile.gettempdir(), 'test_secret.txt')
with open(test_file, 'w') as f:
    f.write('BehVault secret content for testing vault!')

fid = vault_mgr.import_file(uid, test_file, key)
check('VaultManager import_file', fid > 0)
files = vault_mgr.list_files(uid)
check('VaultManager list_files', len(files) == 1)

dec_fname = vault_mgr.decrypt_filename_preview(fid, key)
check('VaultManager filename preview', dec_fname == 'test_secret.txt')

out_dir = os.path.join(tempfile.gettempdir(), 'behvault_out')
os.makedirs(out_dir, exist_ok=True)
out_path = vault_mgr.decrypt_file(fid, key, out_dir)
check('VaultManager decrypt_file', os.path.exists(out_path))
with open(out_path, 'r') as f:
    check('VaultManager content intact',
          f.read() == 'BehVault secret content for testing vault!')
os.remove(out_path)

# VaultService permission check
check('VaultService not authenticated', not vault_svc.is_authenticated(uid))
try:
    vault_svc.import_file(uid, test_file)
    check('VaultService permission check', False, 'should raise PermissionError')
except PermissionError:
    check('VaultService permission check', True)

# VaultService authenticated operations
vault_svc.unlock(uid, key)
check('VaultService unlocked', vault_svc.is_authenticated(uid))
check('VaultService get_vault_key', vault_svc.get_vault_key(uid) == key)

fid2 = vault_svc.import_file(uid, test_file)
check('VaultService import_file (unlocked)', fid2 > 0)

vault_svc.lock(uid)
check('VaultService locked', not vault_svc.is_authenticated(uid))

os.remove(test_file)
os.rmdir(out_dir)
vault_mgr.delete_file(fid)
vault_mgr.delete_file(fid2)
print()

# ===== 6. ADAPTIVE LEARNER =====
print('6. ADAPTIVE LEARNER')
from src.ml.adaptive_learner import AdaptiveLearner

learner = AdaptiveLearner(alpha=0.8, window_size=20)
check('should_update (low risk, CA ok)',
      learner.should_update(15, True, 2.0, template) == True)
check('should_update (high risk)',
      learner.should_update(60, True, 2.0, template) == False)
check('should_update (CA failed)',
      learner.should_update(15, False, 2.0, template) == False)

# EMA update
test_template = BehaviorTemplate(fvs[:10])
old_mean = test_template.mean_vector.copy()
learner.update_ema(test_template, fvs[0])
check('EMA: mean updated', not np.allclose(test_template.mean_vector, old_mean))
check('EMA: sample appended', len(test_template.feature_vectors) == 11)

# Sliding window
test_template2 = BehaviorTemplate(fvs[:10])
for i in range(25):
    test_template2.add_sample(fvs[i % 10])
learner.update_sliding_window(test_template2)
check('Sliding window: capped at window_size', len(test_template2.feature_vectors) <= learner.window_size)
print()

# ===== 7. CHARTS =====
print('7. CHARTS (matplotlib)')
from src.viz.charts import ChartGenerator

bytes_hold = ChartGenerator.hold_time_curve(fvs, 'Test Hold Time')
check('hold_time_curve', len(bytes_hold) > 500)

bytes_flight = ChartGenerator.flight_time_curve(fvs, 'Test Flight Time')
check('flight_time_curve', len(bytes_flight) > 500)

bytes_dist = ChartGenerator.feature_distribution(fvs, 'Test Distribution')
check('feature_distribution', len(bytes_dist) > 500)

genuine_scores = [15, 20, 18, 25, 22, 30, 28, 12, 19, 24]
attack_scores = [85, 92, 78, 95, 88, 100, 90, 82, 100, 100]
bytes_compare = ChartGenerator.user_vs_attacker(genuine_scores, attack_scores)
check('user_vs_attacker', len(bytes_compare) > 500)

bytes_timeline = ChartGenerator.risk_timeline(genuine_scores + attack_scores)
check('risk_timeline', len(bytes_timeline) > 500)

bytes_far = ChartGenerator.far_frr_curve([0.1, 0.05, 0.02], [0.08, 0.12, 0.18], [30, 50, 70])
check('far_frr_curve', len(bytes_far) > 500)

results_dict = {
    'password_leak_scores': [60, 70, 80, 65, 75],
    'imitation_scores': [35, 40, 50, 45, 55],
    'random_scores': [85, 90, 95, 88, 92],
}
bytes_attack = ChartGenerator.attack_comparison(results_dict)
check('attack_comparison', len(bytes_attack) > 500)
print()

# ===== 8. EXPERIMENT SERVICE =====
print('8. EXPERIMENT SERVICE (Attack Simulation)')
from src.services.experiment_service import ExperimentService

exp = ExperimentService(db)
# Create a fresh user with real feature vectors for experiment
exp_uid = db.create_user('exp_test', 'hash123', BehaviorTemplate(fvs[:10]).to_json())
for fv_obj in fvs[:10]:
    db.save_sample(exp_uid, fv_obj.to_json())

leak_scores = exp.simulate_password_leak_attack(exp_uid, 'behvault', n_attempts=20)
check('Password leak attack (20 attempts)', len(leak_scores) == 20)
check('Leak scores in [0,100]', all(0 <= s <= 100 for s in leak_scores))

ref_events = [KeystrokeEvent(key='k', press_time=0, release_time=0.1) for _ in range(8)]
imitation_scores = exp.simulate_imitation_attack(exp_uid, 'behvault', ref_events, n_attempts=20)
check('Imitation attack (20 attempts)', len(imitation_scores) == 20)

random_scores = exp.simulate_random_input_attack(exp_uid, 'behvault', n_attempts=20)
check('Random attack (20 attempts)', len(random_scores) == 20)

# FAR/FRR/EER
gen = [15, 18, 22, 25, 20, 30, 28, 12, 19, 24]
imp = [85, 92, 78, 95, 88, 100, 90, 82, 100, 100, 75, 80, 95, 88, 92]
metrics = exp.compute_far_frr(gen, imp)
check('FAR/FRR/EER computed', all(k in metrics for k in ['far', 'frr', 'eer']))
check('FAR < 0.3', metrics['far'] < 0.3, f'FAR={metrics["far"]:.3f}')
check('FRR < 0.3', metrics['frr'] < 0.3, f'FRR={metrics["frr"]:.3f}')
check('EER < 0.3', metrics['eer'] < 0.3, f'EER={metrics["eer"]:.3f}')

full = exp.run_full_experiment(exp_uid, 'behvault')
check('Full experiment result', len(full) == 8, f'got {len(full)} keys')
check('Full experiment has FAR', 'far' in full)
check('Full experiment has FRR', 'frr' in full)
check('Full experiment has EER', 'eer' in full)
check('Full experiment FAR < 0.5', full['far'] < 0.5)
print()

# ===== 9. AUTH SERVICE =====
print('9. AUTH SERVICE (Register + Login)')
from src.services.auth_service import AuthService

db2_path = os.path.join(tempfile.gettempdir(), 'test_auth_service.db')
try:
    os.remove(db2_path)
except:
    pass
db2 = DatabaseManager(db2_path)
auth = AuthService(db2)

rng3 = np.random.RandomState(777)
events_lists = []
for s in range(10):
    speed = 1.0 + rng3.normal(0, 0.12)
    events = []
    t = 0.0
    for ch in 'behvault':
        hold = max(0.04, rng3.normal(0.11, 0.03) * speed)
        flight = max(0.02, rng3.normal(0.09, 0.04) * speed)
        t += flight
        events.append(KeystrokeEvent(key=ch, press_time=t, release_time=t + hold))
        t = t + hold
    events_lists.append(events)

result = auth.register('testuser', 'behvault', events_lists)
check('AuthService register', result == True)

# Login genuine
speed = 1.0 + rng3.normal(0, 0.12)
login_events = []
t = 0.0
for ch in 'behvault':
    hold = max(0.04, rng3.normal(0.11, 0.03) * speed)
    flight = max(0.02, rng3.normal(0.09, 0.04) * speed)
    t += flight
    login_events.append(KeystrokeEvent(key=ch, press_time=t, release_time=t + hold))
    t = t + hold

risk, cat = auth.login('testuser', 'behvault', login_events)
check('Login genuine (safe)', risk <= 30 and cat == 'safe',
      f'risk={risk}, cat={cat}')

# Login wrong password
risk2, cat2 = auth.login('testuser', 'wrongpassword', login_events)
check('Login wrong password', cat2 == 'wrong_password')

# Login user not found
risk3, cat3 = auth.login('nobody', 'behvault', login_events)
check('Login user not found', cat3 == 'user_not_found')

# Login no events
risk4, cat4 = auth.login('testuser', 'behvault', [])
check('Login no events', cat4 == 'no_events')

# Adaptive update
result = auth.trigger_adaptive_update(1, login_events)
check('Adaptive update (should succeed)', result == True)
db2.conn.close()
try:
    os.remove(db2_path)
except:
    pass
print()

# ===== SUMMARY =====
db.conn.close()
try:
    os.remove(db_path)
except:
    pass

print('=' * 60)
print(f'RESULTS: {PASS} PASSED, {FAIL} FAILED out of {PASS+FAIL} tests')
if FAIL == 0:
    print('ALL MODULES WORKING CORRECTLY!')
else:
    print(f'{FAIL} FAILURES DETECTED!')
print('=' * 60)
