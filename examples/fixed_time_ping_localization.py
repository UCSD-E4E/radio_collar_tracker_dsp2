'''Fixed runtime, random position localization example
'''
# pylint: disable=duplicate-code
import datetime as dt
import time
from random import randint
from typing import Tuple

from rct_dsp2 import SDR_TYPE_GENERATOR, PingFinder
from rct_dsp2.localization import LocationEstimator


def position_lookup(now: dt.datetime) -> Tuple[float, float, float]:
    """Position lookup request

    Args:
        now (dt.datetime): Timestamp of the ping
    """
    # pylint: disable=unused-argument
    x = randint(-100, 0)
    y = randint(100, 200)
    z = randint(30, 40)
    return (x, y, z)


def main():
    """Main function
    """
    localizer = LocationEstimator(
        location_lookup=position_lookup
    )
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

    ping_finder.register_callback(localizer.add_ping)

    # Optionally:
    ping_finder.sdr_type = SDR_TYPE_GENERATOR

    ping_finder.start()

    time.sleep(10)

    ping_finder.stop()

    for frequency in localizer.get_frequencies():
        estimate = localizer.do_estimate(
            frequency=frequency, xy_bounds=(-200, 200, -200, 200))
        print(f'Frequency {frequency} estimated at {estimate}')


if __name__ == '__main__':
    main()
