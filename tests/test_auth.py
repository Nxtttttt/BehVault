"""Authentication and feature extraction tests."""

import sys
import os
import time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.auth.feature_extractor import KeystrokeEvent, FeatureVector, FeatureExtractor


def test_keystroke_event_hold_time():
    e = KeystrokeEvent(key="a", press_time=1.0, release_time=1.15)
    assert abs(e.hold_time - 150.0) < 0.01


def test_feature_vector_to_from_array():
    fv = FeatureVector(mean_hold_time=100, std_hold_time=20, max_hold_time=150,
                       min_hold_time=50, mean_flight_time=60, std_flight_time=15,
                       max_flight_time=90, min_flight_time=30,
                       backspace_count=2, total_time=1500)
    arr = fv.to_array()
    fv2 = FeatureVector.from_array(arr)
    assert fv2.mean_hold_time == 100
    assert fv2.backspace_count == 2


def test_feature_vector_json_roundtrip():
    fv = FeatureVector(mean_hold_time=120, std_hold_time=25, max_hold_time=180,
                       min_hold_time=60, mean_flight_time=70, std_flight_time=18,
                       max_flight_time=100, min_flight_time=40,
                       backspace_count=1, total_time=2000)
    json_str = fv.to_json()
    fv2 = FeatureVector.from_json(json_str)
    assert fv2.mean_hold_time == 120
    assert fv2.total_time == 2000


def test_feature_extractor_simple():
    extractor = FeatureExtractor()
    events = [
        KeystrokeEvent(key="h", press_time=0.0, release_time=0.12),
        KeystrokeEvent(key="i", press_time=0.18, release_time=0.28),
    ]
    fv = extractor.extract(events)
    assert abs(fv.mean_hold_time - 110.0) < 5
    assert fv.backspace_count == 0
    assert len(fv.to_array()) == 10


def test_feature_extractor_with_backspace():
    extractor = FeatureExtractor()
    events = [
        KeystrokeEvent(key="h", press_time=0.0, release_time=0.1),
        KeystrokeEvent(key="BackSpace", press_time=0.15, release_time=0.2, is_backspace=True),
        KeystrokeEvent(key="i", press_time=0.25, release_time=0.35),
    ]
    fv = extractor.extract(events)
    assert fv.backspace_count == 1


def test_feature_extractor_empty():
    extractor = FeatureExtractor()
    fv = extractor.extract([])
    assert fv.mean_hold_time == 0.0


def test_feature_extractor_batch():
    extractor = FeatureExtractor()
    batch = [
        [KeystrokeEvent(key="a", press_time=0.0, release_time=0.1)],
        [KeystrokeEvent(key="b", press_time=0.0, release_time=0.15)],
    ]
    fvs = extractor.extract_batch(batch)
    assert len(fvs) == 2
    assert abs(fvs[1].mean_hold_time - 150.0) < 5


if __name__ == "__main__":
    test_keystroke_event_hold_time()
    test_feature_vector_to_from_array()
    test_feature_vector_json_roundtrip()
    test_feature_extractor_simple()
    test_feature_extractor_with_backspace()
    test_feature_extractor_empty()
    test_feature_extractor_batch()
    print("All auth tests passed!")
