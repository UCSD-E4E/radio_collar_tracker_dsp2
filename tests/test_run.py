from radio_collar_tracker_dsp2 import PingFinder
import time

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

    ping_finder.start()

    # time.sleep(2)

    # ping_finder.stop()