import json
import numpy as np

from src.auth.feature_extractor import FeatureVector


class BehaviorTemplate:
    def __init__(self, feature_vectors: list[FeatureVector] = None):
        self.feature_vectors: list[FeatureVector] = feature_vectors or []
        self.mean_vector: np.ndarray = np.zeros(10)
        self.std_vector: np.ndarray = np.zeros(10)
        if self.feature_vectors:
            self._recompute()

    def add_sample(self, fv: FeatureVector):
        self.feature_vectors.append(fv)
        self._recompute()

    def _recompute(self):
        arrays = np.array([fv.to_array() for fv in self.feature_vectors])
        self.mean_vector = np.mean(arrays, axis=0)
        self.std_vector = np.std(arrays, axis=0, ddof=1) if len(self.feature_vectors) > 1 else np.ones(10)

    def to_json(self) -> str:
        return json.dumps({
            "feature_vectors": [fv.to_json() for fv in self.feature_vectors],
        })

    @staticmethod
    def from_json(json_str: str) -> "BehaviorTemplate":
        data = json.loads(json_str)
        fvs = [FeatureVector.from_json(s) for s in data["feature_vectors"]]
        return BehaviorTemplate(fvs)

    def __len__(self):
        return len(self.feature_vectors)
