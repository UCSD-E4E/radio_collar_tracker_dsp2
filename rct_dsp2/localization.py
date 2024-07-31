'''Localization
'''
import datetime as dt
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np
from scipy.optimize import least_squares


@dataclass
class Ping:
    """Ping dataclass
    """
    x: float
    y: float
    z: float
    power: float
    freq: int
    time: dt.datetime

    def to_numpy(self) -> np.ndarray:
        """Converts the Ping to a numpy array

        Returns:
            np.ndarray: Numpy array for processing
        """
        return np.array([self.x, self.y, self.z, self.power])


class LocationEstimator:
    """Location Estimator

    All coordinate systems assumed have units in meters, using ENU order of axis
    """
    def __init__(self, location_lookup: Callable[[dt.datetime], Tuple[float, float, float]]):
        self.__loc_fn = location_lookup

        self.__pings: Dict[int, List[Ping]] = {}

        self.__estimate: Dict[int, np.ndarray] = {}

    def add_ping(self, now: dt.datetime, amplitude: float, frequency: int):
        """Adds a ping.

        Ping location is set via the location_lookup callback

        Args:
            now (dt.datetime): timestamp of ping
            amplitude (float): Amplitude of ping
            frequency (int): Ping frequency
        """
        x, y, z = self.__loc_fn(now)
        new_ping = Ping(x, y, z, amplitude, frequency, now)
        if frequency not in self.__pings:
            self.__pings[frequency] = [new_ping]
        else:
            self.__pings[frequency].append(new_ping)

    def do_estimate(self, frequency: int) -> Optional[Tuple[float, float, float]]:
        """Performs the estimate

        Args:
            frequency (int): Frequency to estimate on

        Raises:
            KeyError: Unknown frequency

        Returns:
            Optional[Tuple[float, float, float]]: If estimate is valid, the XYZ coordinates,
            otherwise, None
        """
        if frequency not in self.__pings:
            raise KeyError('Unknown frequency')

        if len(self.__pings[frequency]) < 4:
            return None

        pings = np.array([ping.to_numpy() for ping in self.__pings[frequency]])

        x_tx_0 = np.mean(pings[:, 0])
        y_tx_0 = np.mean(pings[:, 1])
        p_tx_0 = np.max(pings[:, 3])

        n_0 = 2

        if frequency in self.__estimate:
            params = self.__estimate[frequency]
        else:
            params = np.array([x_tx_0, y_tx_0, p_tx_0, n_0])
        res_x = least_squares(
            fun=self.__residuals,
            x0=params,
            bounds=([167000, 0, -np.inf, 2], [833000, 10000000, np.inf, 2.1]),
            args=(pings,)
        )

        if res_x.success:
            retval = (params[0], params[1], 0)
            self.__estimate[frequency] = params
        else:
            retval = None

        return retval

    def get_frequencies(self) -> Iterable[int]:
        """Gets the current frequencies

        Returns:
            Iterable[int]: Iterable of frequencies
        """
        return self.__pings.keys()

    def __residuals(self, params: np.ndarray, data: np.ndarray) -> np.ndarray:
        # Params is expected to be shape(4,)
        # Data is expected to be shape(n, 4)
        estimated_transmitter_x = params[0]
        estimated_transmitter_y = params[1]
        estimated_transmitter_location = np.array(
            [estimated_transmitter_x, estimated_transmitter_y, 0])

        estimated_transmitter_power = params[2]
        estimated_model_order = params[3]

        received_power = data[:, 3]
        received_locations = data[:, 0:3]

        residuals = np.zeros(len(received_power))
        distances = np.linalg.norm(
            received_locations - estimated_transmitter_location, axis=1)
        residuals = received_power - self.__distance_to_receive_power(
            distances, estimated_transmitter_power, estimated_model_order)
        return residuals

    def __distance_to_receive_power(self,
                                    distance: np.ndarray,
                                    k: float,
                                    order: float) -> np.ndarray:
        return k - 10 * order * np.log10(distance)
