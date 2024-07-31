'''Test Localization
'''

import datetime as dt

import numpy as np
from conftest import SimulatedData

from rct_dsp2.localization import LocationEstimator


def test_localization(simulated_data: SimulatedData):
    """Tests ideal localization

    Args:
        simulated_data (SimulatedData): Simulated Data
    """
    dut = LocationEstimator(simulated_data.lookup_position)
    for idx, amplitude in enumerate(simulated_data.received_signal_strength):
        timestamp = dt.datetime.fromtimestamp(simulated_data.times[idx])
        dut.add_ping(timestamp, amplitude, 1)
    result = dut.do_estimate(1)
    assert np.linalg.norm(np.array(result) - simulated_data.tx_location) < 5
