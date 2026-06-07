"""Visualization charts for behavioral analysis and attack evaluation."""

import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.auth.feature_extractor import FeatureVector

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


class ChartGenerator:
    @staticmethod
    def _figure_to_bytes(fig: plt.Figure) -> bytes:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    @classmethod
    def hold_time_curve(cls, feature_vectors: list[FeatureVector], title: str = "Hold Time per Sample") -> bytes:
        hold_means = [fv.mean_hold_time for fv in feature_vectors]
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(range(1, len(hold_means) + 1), hold_means, "b-o", markersize=6)
        ax.axhline(y=np.mean(hold_means), color="r", linestyle="--", label=f"Mean: {np.mean(hold_means):.1f}ms")
        ax.set_xlabel("Sample Index")
        ax.set_ylabel("Mean Hold Time (ms)")
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        return cls._figure_to_bytes(fig)

    @classmethod
    def flight_time_curve(cls, feature_vectors: list[FeatureVector], title: str = "Flight Time per Sample") -> bytes:
        flight_means = [fv.mean_flight_time for fv in feature_vectors]
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(range(1, len(flight_means) + 1), flight_means, "g-o", markersize=6)
        ax.axhline(y=np.mean(flight_means), color="r", linestyle="--", label=f"Mean: {np.mean(flight_means):.1f}ms")
        ax.set_xlabel("Sample Index")
        ax.set_ylabel("Mean Flight Time (ms)")
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        return cls._figure_to_bytes(fig)

    @classmethod
    def feature_distribution(cls, feature_vectors: list[FeatureVector], title: str = "Feature Distribution") -> bytes:
        arrays = np.array([fv.to_array() for fv in feature_vectors])
        labels = ["MH", "SH", "MaH", "MiH", "MF", "SF", "MaF", "MiF", "BS", "TT"]
        means = np.mean(arrays, axis=0)
        stds = np.std(arrays, axis=0, ddof=1)
        fig, ax = plt.subplots(figsize=(10, 5))
        x = range(len(labels))
        ax.bar(x, means, yerr=stds, capsize=5, color="steelblue", edgecolor="navy")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_ylabel("Value")
        ax.set_title(title)
        ax.grid(True, alpha=0.3, axis="y")
        return cls._figure_to_bytes(fig)

    @classmethod
    def user_vs_attacker(cls, genuine_scores: list[int], attack_scores: list[int],
                         title: str = "Genuine vs Attacker Risk Scores") -> bytes:
        fig, ax = plt.subplots(figsize=(8, 5))
        bins = np.linspace(0, 100, 21)
        ax.hist(genuine_scores, bins=bins, alpha=0.6, label="Genuine User", color="green", edgecolor="black")
        ax.hist(attack_scores, bins=bins, alpha=0.6, label="Attacker", color="red", edgecolor="black")
        ax.axvline(x=30, color="orange", linestyle="--", label="Safe (30)")
        ax.axvline(x=70, color="red", linestyle="--", label="High Risk (70)")
        ax.set_xlabel("Risk Score")
        ax.set_ylabel("Frequency")
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        return cls._figure_to_bytes(fig)

    @classmethod
    def risk_timeline(cls, scores: list[int], title: str = "Risk Score Timeline") -> bytes:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(range(len(scores)), scores, "b-", linewidth=1)
        ax.fill_between(range(len(scores)), 0, 30, color="green", alpha=0.1)
        ax.fill_between(range(len(scores)), 30, 70, color="yellow", alpha=0.1)
        ax.fill_between(range(len(scores)), 70, 100, color="red", alpha=0.1)
        ax.axhline(y=30, color="orange", linestyle="--", linewidth=1)
        ax.axhline(y=70, color="red", linestyle="--", linewidth=1)
        ax.set_xlabel("Login Attempt")
        ax.set_ylabel("Risk Score")
        ax.set_ylim(0, 100)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        return cls._figure_to_bytes(fig)

    @classmethod
    def far_frr_curve(cls, far_list: list[float], frr_list: list[float],
                      thresholds: list[int], title: str = "FAR/FRR vs Threshold") -> bytes:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(thresholds, far_list, "r-o", label="FAR", markersize=4)
        ax.plot(thresholds, frr_list, "b-o", label="FRR", markersize=4)
        ax.set_xlabel("Threshold")
        ax.set_ylabel("Rate")
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        return cls._figure_to_bytes(fig)

    @classmethod
    def attack_comparison(cls, results: dict, title: str = "Attack Comparison") -> bytes:
        categories = ["Password Leak", "Imitation", "Random"]
        means = [
            np.mean(results.get("password_leak_scores", [0])),
            np.mean(results.get("imitation_scores", [0])),
            np.mean(results.get("random_scores", [0])),
        ]
        stds = [
            np.std(results.get("password_leak_scores", [0])),
            np.std(results.get("imitation_scores", [0])),
            np.std(results.get("random_scores", [0])),
        ]
        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(categories, means, yerr=stds, capsize=8, color=["darkorange", "tomato", "firebrick"])
        ax.axhline(y=30, color="green", linestyle="--", label="Safe (30)")
        ax.axhline(y=70, color="red", linestyle="--", label="High Risk (70)")
        ax.set_ylabel("Mean Risk Score")
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3, axis="y")
        return cls._figure_to_bytes(fig)
