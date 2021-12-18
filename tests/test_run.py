from radio_collar_tracker_dsp2 import PingFinder
import time
import datetime as dt

callback_called = 0
def phony_callback(now: dt.datetime, amplitude:float, frequency: int):
    print(f"Calling callback with {now}, amplitude: {amplitude}, frequency {frequency}")
    assert(isinstance(now, dt.datetime))
    assert(isinstance(amplitude, float))
    assert(isinstance(frequency, int))
    global callback_called
    callback_called += 1
    print("Finished callback")

def test_run():
    ping_finder = PingFinder()
    ping_finder.gain = 22.0
    ping_finder.sampling_rate = 1500000
    ping_finder.rx_frequency = 173500000
    ping_finder.run_num = 1
    ping_finder.test_config = False
    ping_finder.data_dir = '/tmp'
    ping_finder.ping_width_ms = 50
    ping_finder.ping_min_snr = 25
    ping_finder.ping_max_len_mult = 1.5
    ping_finder.ping_min_len_mult = 0.5
    ping_finder.target_frequencies = [173700000, 173900000]

    ping_finder.register_callback(phony_callback)
    ping_finder.start()

    time.sleep(2)

    ping_finder.stop()