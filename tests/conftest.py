'''Test Configurations
'''
from dataclasses import dataclass
from typing import List, Tuple
import datetime as dt
import numpy as np
import pytest


@dataclass
class PathLeg:
    """Path Leg

    """
    v_x: float
    v_y: float
    v_z: float

    def to_numpy(self) -> np.ndarray:
        """Returns a np array representation

        Returns:
            np.ndarray: Numpy representation
        """
        return np.array


@dataclass
class SimulatedPath:
    """Simulated path structure
    """
    time_per_leg: float
    leg_velocities: List[PathLeg]
    start_location: np.ndarray


@pytest.fixture
def simulated_path() -> SimulatedPath:
    """Simulated path

    Returns:
        SimulatedPath: Simulated path
    """
    return SimulatedPath(
        time_per_leg=30,
        leg_velocities=[
            PathLeg(5, 1, 0),
            PathLeg(-1, 5, 0),
            PathLeg(-5, -1, 0),
            PathLeg(1, -5, 0)
        ],
        start_location=np.array([-100, 0, 30])
    )


@dataclass
class SimulatedData:
    """Simulated Data Structure
    """
    tx_location: np.ndarray
    tx_power: float
    tx_order: float

    positions: List[np.ndarray]
    received_signal_strength: List[float]
    times: List[float]

    def lookup_position(self, time: dt.datetime) -> Tuple[float, float, float]:
        """Looks up the ENU position at the given time

        Args:
            time (dt.datetime): Timestamp to look up

        Returns:
            Tuple[float, float, float]: ENU position
        """
        timestamp = time.timestamp()
        idx = self.times.index(timestamp)
        return self.positions[idx][0], self.positions[idx][1], self.positions[idx][2]


@pytest.fixture
def simulated_data() -> SimulatedData:
    """Simulated Exact Data

    Returns:
        SimulatedData: Simulated exact data
    """
    rng = np.random.default_rng(0)
    tx_location = rng.standard_normal(3) + np.array([500000, 5000000, 0])
    tx_power = rng.normal(100, 5)
    tx_order = rng.uniform(2, 6)

    n_samples = rng.integers(4, 1024)
    positions = rng.uniform([-100, -100, 25], [100, 100, 35],
                            (n_samples, 3)) + np.array([500000, 5000000, 0])
    times = [(dt.datetime.now() + dt.timedelta(seconds=1) * idx).timestamp()
             for idx in range(n_samples)]
    offsets = positions - tx_location
    distances = np.linalg.norm(offsets, axis=1)
    rx_power = tx_power - 10 * tx_order * np.log10(distances)
    return SimulatedData(
        tx_location=tx_location,
        tx_power=tx_power,
        tx_order=tx_order,
        positions=positions,
        received_signal_strength=rx_power,
        times=times
    )
