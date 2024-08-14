'''Fixed runtime, record only example
'''
# pylint: disable=duplicate-code
import datetime as dt
import time

from rct_dsp2 import SDR_TYPE_GENERATOR, PingFinder


def callback(now: dt.datetime, amplitude: float, frequency: int):
    """Callback whenever the PingFinder detects a ping

    Args:
        now (dt.datetime): Timestamp of the ping
        amplitude (float): Ping amplitude
        frequency (int): Ping frequency
    """
    print(
        f'Got ping at {now}, amplitude is {amplitude} on frequency {frequency} Hz')


def main():
    """Main function
    """
    ping_finder = PingFinder()
    ping_finder.gain = 14.0
    ping_finder.sampling_rate = 2500000
    ping_finder.center_frequency = 173500000
    ping_finder.run_num = 1
    ping_finder.enable_test_data = False
    ping_finder.output_dir = '.'
    ping_finder.ping_width_ms = 25
    ping_finder.ping_min_snr = 25
    ping_finder.ping_max_len_mult = 1.5
    ping_finder.ping_min_len_mult = 0.5
    ping_finder.target_frequencies = [173500000 + 1000]

    ping_finder.register_callback(callback)

    # Optionally:
    ping_finder.sdr_type = SDR_TYPE_GENERATOR

    ping_finder.start()

    time.sleep(10)

    ping_finder.stop()


if __name__ == '__main__':
    main()
