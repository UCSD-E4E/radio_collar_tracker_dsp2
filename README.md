# Setup
This requires Ubuntu 24.04 or later.

```
sudo add-apt-repository ppa:ettusresearch/uhd
sudo apt-get update
sudo apt-get install -y fftw-dev libboost-all-dev libuhd-dev uhd-host libairspy-dev libhackrf-dev python3 python3-dev python3-pip python3-venv cmake build-essential
python -m pip install .
```

# Usage:
```
import datetime as dt
import time

from rct_dsp2 import PingFinder, SDR_TYPE_USRP

def callback(now: dt.datetime, amplitude: float, frequency: int):
    print(f'Got ping at {now}, amplitude is {amplitude} on frequency {frequency} Hz')

def main():
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

    // Optionally:
    ping_finder.sdr_type = SDR_TYPE_USRP

    ping_finder.start()

    time.sleep(10)

    ping_finder.stop()

if __name__ == '__main__':
    main()
```