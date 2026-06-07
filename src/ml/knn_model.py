import numpy as np
from sklearn.neighbors import NearestNeighbors

from src.auth.feature_extractor import FeatureVector


class KNNModel:
    def __init__(self, k: int = 5):
        self.k = k
        self._features: np.ndarray = None
        self._nn: NearestNeighbors = None

    @staticmethod
    def _safe_std(std_vector: np.ndarray, feature_arrays: np.ndarray = None) -> np.ndarray:
        """Clip std to prevent over-normalization when variance is tiny.

        Floor: max(10% of feature mean, 5.0 absolute) to keep all dimensions
        on a comparable normalized scale.
        """
        std_safe = np.where(std_vector < 1e-6, 1.0, std_vector)
        if feature_arrays is not None and len(feature_arrays) > 0:
            feature_means = np.mean(np.abs(feature_arrays), axis=0)
            min_std = np.maximum(feature_means * 0.1, 5.0)
            std_safe = np.maximum(std_safe, min_std)
        return std_safe

    def fit(self, features: list[FeatureVector], std_vector: np.ndarray = None):
        arrays = np.array([fv.to_array() for fv in features])
        self._raw_features = arrays.copy()
        if std_vector is not None:
            std_safe = self._safe_std(std_vector, arrays)
            arrays = arrays / std_safe
            self._active_std = std_safe
        else:
            self._active_std = None
        self._features = arrays
        effective_k = min(self.k, len(features))
        self._nn = NearestNeighbors(n_neighbors=effective_k, metric="euclidean")
        self._nn.fit(arrays)

    def predict(self, sample: FeatureVector, std_vector: np.ndarray = None) -> tuple[list[float], list[int]]:
        arr = sample.to_array().reshape(1, -1)
        if std_vector is not None:
            # Use the same std_safe that was used during fit() to keep scales consistent
            if self._active_std is not None:
                arr = arr / self._active_std
            else:
                std_safe = self._safe_std(std_vector)
                arr = arr / std_safe
        distances, indices = self._nn.kneighbors(arr)
        return distances[0].tolist(), indices[0].tolist()

    def get_average_distance(self, sample: FeatureVector, std_vector: np.ndarray = None) -> float:
        distances, _ = self.predict(sample, std_vector)
        return float(np.mean(distances))

    def compute_self_distances(self, features: list[FeatureVector],
                              std_vector: np.ndarray = None) -> list[float]:
        n = len(features)
        if n < 2:
            return [0.0] * n
        self_distances = []
        for i in range(n):
            others = [features[j] for j in range(n) if j != i]
            self.fit(others, std_vector)
            d = self.get_average_distance(features[i], std_vector)
            self_distances.append(d)
        return self_distances
