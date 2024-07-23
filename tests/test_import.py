'''Testing imports
'''
from RCTDSP2 import PingFinder

def test_import():
    """Testing RCT DSP2 members
    """
    assert hasattr(PingFinder, '__init__')
    pf_ = PingFinder()
    assert pf_ is not None
    assert hasattr(pf_, 'gain')
    assert isinstance(pf_.gain, float)
    assert PingFinder.gain.__doc__ != ''
    assert hasattr(pf_, 'sampling_rate')
    assert isinstance(pf_.sampling_rate, int)
    assert PingFinder.sampling_rate.__doc__ != ''
    assert hasattr(pf_, 'center_frequency')
    assert isinstance(pf_.center_frequency, int)
    assert PingFinder.center_frequency.__doc__ != ''
    assert hasattr(pf_, 'run_num')
    assert isinstance(pf_.run_num, int)
    assert PingFinder.run_num.__doc__ != ''
    assert hasattr(pf_, 'enable_test_data')
    assert isinstance(pf_.enable_test_data, bool)
    assert PingFinder.enable_test_data.__doc__ != ''
    assert hasattr(pf_, 'output_dir')
    assert isinstance(pf_.output_dir, str)
    assert PingFinder.output_dir.__doc__ != ''
    assert hasattr(pf_, 'test_data_path')
    assert isinstance(pf_.test_data_path, str)
    assert PingFinder.test_data_path.__doc__ != ''
    assert hasattr(pf_, 'ping_width_ms')
    assert isinstance(pf_.ping_width_ms, int)
    assert PingFinder.ping_width_ms.__doc__ != ''
    assert hasattr(pf_, 'ping_min_snr')
    assert isinstance(pf_.ping_min_snr, float)
    assert PingFinder.ping_min_snr.__doc__ != ''
    assert hasattr(pf_, 'ping_max_len_mult')
    assert isinstance(pf_.ping_max_len_mult, float)
    assert PingFinder.ping_max_len_mult.__doc__ != ''
    assert hasattr(pf_, 'ping_min_len_mult')
    assert isinstance(pf_.ping_min_len_mult, float)
    assert PingFinder.ping_min_len_mult.__doc__ != ''
    assert hasattr(pf_, 'target_frequencies')
    assert isinstance(pf_.target_frequencies, list)
    assert PingFinder.target_frequencies.__doc__ != ''
    assert hasattr(pf_, 'start')
    assert pf_.start.__doc__ != ''
    assert hasattr(pf_, 'stop')
    assert pf_.stop.__doc__ != ''
    assert hasattr(pf_, 'sdr_type')
    assert pf_.stop.__doc__ != ''
