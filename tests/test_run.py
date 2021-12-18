from radio_collar_tracker_dsp2 import PingFinder
import time
import datetime as dt
import glob
import os

callback_called = 0
def phony_callback(now: dt.datetime, amplitude:float, frequency: int):
    assert(isinstance(now, dt.datetime))
    assert(isinstance(amplitude, float))
    assert(isinstance(frequency, int))
    global callback_called
    callback_called += 1
    print(f'Got ping at {now}, amplitude is {amplitude} on frequency {frequency} Hz')

def test_run():
    RUN_TIME = 8
    ping_finder = PingFinder()
    ping_finder.gain = 22.0
    ping_finder.sampling_rate = 2000000
    ping_finder.center_frequency = 173500000
    ping_finder.run_num = 1
    ping_finder.enable_test_data = False
    ping_finder.output_dir = '.'
    ping_finder.ping_width_ms = 25
    ping_finder.ping_min_snr = 25
    ping_finder.ping_max_len_mult = 1.5
    ping_finder.ping_min_len_mult = 0.5
    ping_finder.target_frequencies = [173964000, 173900000]

    ping_finder.register_callback(phony_callback)
    raw_files = glob.glob(os.path.join(ping_finder.output_dir, f"RAW_DATA_{ping_finder.run_num:06d}_*"))
    for f in raw_files:
        os.remove(f)

    ping_finder.start()

    time.sleep(RUN_TIME)

    ping_finder.stop()
    raw_files = glob.glob(os.path.join(ping_finder.output_dir, f"RAW_DATA_{ping_finder.run_num:06d}_*"))
    assert(len(raw_files) > 0)

    file_sizes = [os.path.getsize(f) for f in raw_files]
    assert(abs(sum(file_sizes) / 2 / 2 / ping_finder.sampling_rate - RUN_TIME) < 1)