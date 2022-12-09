import datetime as dt
import glob
import os
import time
from typing import Dict, List

import numpy as np

from RCTDSP2 import PingFinder

callback_called = 0

pings: List[float] = []
def phony_callback(now: dt.datetime, amplitude:float, frequency: int):
    global pings
    assert(isinstance(now, dt.datetime))
    assert(isinstance(amplitude, float))
    assert(isinstance(frequency, int))
    global callback_called
    callback_called += 1
    pings.append(amplitude)

def test_run():
    RUN_TIME = 8
    ping_finder = PingFinder()
    ping_finder.gain = 56.0
    ping_finder.sampling_rate = 2500000
    ping_finder.center_frequency = 173500000
    ping_finder.run_num = 1
    ping_finder.enable_test_data = False
    ping_finder.output_dir = '.'
    ping_finder.ping_width_ms = 25
    ping_finder.ping_min_snr = 25
    ping_finder.ping_max_len_mult = 1.5
    ping_finder.ping_min_len_mult = 0.5
    ping_finder.target_frequencies = [173964000]

    ping_finder.sdr_type = 3

    if ping_finder.sdr_type == 1:
        ping_finder.gain = 56.0
    elif ping_finder.sdr_type == 2:
        ping_finder.gain = 14.0
    elif ping_finder.sdr_type == 3:
        ping_finder.gain = 40.0

    ping_finder.register_callback(phony_callback)
    raw_files = glob.glob(os.path.join(ping_finder.output_dir, f"RAW_DATA_{ping_finder.run_num:06d}_*"))
    for f in raw_files:
        os.remove(f)

    ping_finder.start()

    time.sleep(RUN_TIME)

    ping_finder.stop()

    print(f"Mean amplitude: {np.mean(pings)}")
    print(f"std.dev: {np.std(pings)}")
    print(f'num ping: {len(pings)}')

if __name__ == "__main__":
    test_run()
