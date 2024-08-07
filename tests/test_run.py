"""RCT DSP2 C++ Tests
"""
import datetime as dt
import time
from pathlib import Path
from unittest.mock import Mock

from rct_dsp2 import PingFinder, SDR_TYPE_GENERATOR

SDR_ENABLED = True
GPS_ENABLED = True
USB_ENABLED = True
TX_ENABLED = False
# callback_called = 0
# def phony_callback(now: dt.datetime, amplitude:float, frequency: int):
#     assert(isinstance(now, dt.datetime))
#     assert(isinstance(amplitude, float))
#     assert(isinstance(frequency, int))
#     global callback_called
#     callback_called += 1
#     print(f'Got ping at {now}, amplitude is {amplitude} on frequency {frequency} Hz')


def test_run():
    """Test Run
    """
    run_time = 8
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

    ping_finder.sdr_type = SDR_TYPE_GENERATOR

    phony_callback = Mock()

    ping_finder.register_callback(phony_callback)
    if TX_ENABLED:
        phony_callback.assert_called()
        assert isinstance(phony_callback.call_args.args[0], dt.datetime)
        assert isinstance(phony_callback.call_args.args[1], float)
        assert isinstance(phony_callback.call_args.args[2], int)

    output_path = Path(ping_finder.output_dir)
    for file in output_path.glob(f"RAW_DATA_{ping_finder.run_num:06d}_*"):
        file.unlink()

    if SDR_ENABLED is False:
        return
    assert not ping_finder.run_flag
    ping_finder.start()
    assert ping_finder.run_flag

    time.sleep(run_time)

    assert ping_finder.run_flag
    ping_finder.stop()
    assert not ping_finder.run_flag
    raw_files = list(output_path.glob(f"RAW_DATA_{ping_finder.run_num:06d}_*"))
    assert len(raw_files) > 0

    file_sizes = [f.stat().st_size for f in raw_files]
    total_written_data_bytes = sum(file_sizes)
    total_written_data_samples = total_written_data_bytes / 2 / 2
    assert abs(total_written_data_samples /
               ping_finder.sampling_rate - run_time) < 1
