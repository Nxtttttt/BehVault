import json
import numpy as np
from dataclasses import dataclass, field


@dataclass
class KeystrokeEvent:
    key: str
    press_time: float
    release_time: float
    is_backspace: bool = False

    @property
    def hold_time(self) -> float:
        """Hold time in milliseconds."""
        return (self.release_time - self.press_time) * 1000.0


@dataclass
class FeatureVector:
    mean_hold_time: float = 0.0
    std_hold_time: float = 0.0
    max_hold_time: float = 0.0
    min_hold_time: float = 0.0
    mean_flight_time: float = 0.0
    std_flight_time: float = 0.0
    max_flight_time: float = 0.0
    min_flight_time: float = 0.0
    backspace_count: int = 0
    total_time: float = 0.0

    def to_array(self) -> np.ndarray:
        return np.array([
            self.mean_hold_time, self.std_hold_time, self.max_hold_time, self.min_hold_time,
            self.mean_flight_time, self.std_flight_time, self.max_flight_time, self.min_flight_time,
            float(self.backspace_count), self.total_time,
        ], dtype=np.float64)

    def to_json(self) -> str:
        return json.dumps({
            "mean_hold_time": self.mean_hold_time,
            "std_hold_time": self.std_hold_time,
            "max_hold_time": self.max_hold_time,
            "min_hold_time": self.min_hold_time,
            "mean_flight_time": self.mean_flight_time,
            "std_flight_time": self.std_flight_time,
            "max_flight_time": self.max_flight_time,
            "min_flight_time": self.min_flight_time,
            "backspace_count": self.backspace_count,
            "total_time": self.total_time,
        })

    @staticmethod
    def from_json(json_str: str) -> "FeatureVector":
        d = json.loads(json_str)
        return FeatureVector(**d)

    @staticmethod
    def from_array(arr: np.ndarray) -> "FeatureVector":
        return FeatureVector(
            mean_hold_time=float(arr[0]),
            std_hold_time=float(arr[1]),
            max_hold_time=float(arr[2]),
            min_hold_time=float(arr[3]),
            mean_flight_time=float(arr[4]),
            std_flight_time=float(arr[5]),
            max_flight_time=float(arr[6]),
            min_flight_time=float(arr[7]),
            backspace_count=int(arr[8]),
            total_time=float(arr[9]),
        )


class FeatureExtractor:
    """Extracts 10-dimensional feature vectors from keystroke events."""

    def extract(self, events: list[KeystrokeEvent]) -> FeatureVector:
        if not events:
            return FeatureVector()

        # Separate backspaced and effective characters
        effective = self._remove_backspaced(events)
        backspace_count = sum(1 for e in events if e.is_backspace)

        if len(effective) < 2:
            hold_times = [effective[0].hold_time] if effective else [0]
            return FeatureVector(
                mean_hold_time=float(np.mean(hold_times)),
                std_hold_time=0.0,
                max_hold_time=float(np.max(hold_times)),
                min_hold_time=float(np.min(hold_times)),
                backspace_count=backspace_count,
                total_time=hold_times[0],
            )

        hold_times = np.array([e.hold_time for e in effective])
        flight_times = np.array([
            (effective[i + 1].press_time - effective[i].release_time) * 1000.0
            for i in range(len(effective) - 1)
        ])
        total_time = (effective[-1].release_time - effective[0].press_time) * 1000.0

        return FeatureVector(
            mean_hold_time=float(np.mean(hold_times)),
            std_hold_time=float(np.std(hold_times, ddof=1)) if len(hold_times) > 1 else 0.0,
            max_hold_time=float(np.max(hold_times)),
            min_hold_time=float(np.min(hold_times)),
            mean_flight_time=float(np.mean(flight_times)) if len(flight_times) > 0 else 0.0,
            std_flight_time=float(np.std(flight_times, ddof=1)) if len(flight_times) > 1 else 0.0,
            max_flight_time=float(np.max(flight_times)) if len(flight_times) > 0 else 0.0,
            min_flight_time=float(np.min(flight_times)) if len(flight_times) > 0 else 0.0,
            backspace_count=backspace_count,
            total_time=total_time,
        )

    def extract_batch(self, event_lists: list[list[KeystrokeEvent]]) -> list[FeatureVector]:
        return [self.extract(events) for events in event_lists]

    @staticmethod
    def _remove_backspaced(events: list[KeystrokeEvent]) -> list[KeystrokeEvent]:
        """Remove characters that were backspaced."""
        result = []
        for e in events:
            if e.is_backspace:
                if result:
                    result.pop()
            else:
                result.append(e)
        return result
