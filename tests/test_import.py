'''Testing imports
'''
from importlib.metadata import version

import rct_dsp2

def test_version():
    """Tests the version matching
    """
    assert version('rct_dsp2') == rct_dsp2.__version__

def test_import():
    """Testing RCT DSP2 members
    """
    assert hasattr(rct_dsp2.PingFinder, '__init__')
    pf_ = rct_dsp2.PingFinder()
    assert pf_ is not None
    assert hasattr(pf_, 'gain')
    assert isinstance(pf_.gain, float)
    assert rct_dsp2.PingFinder.gain.__doc__ != ''
    assert hasattr(pf_, 'sampling_rate')
    assert isinstance(pf_.sampling_rate, int)
    assert rct_dsp2.PingFinder.sampling_rate.__doc__ != ''
    assert hasattr(pf_, 'center_frequency')
    assert isinstance(pf_.center_frequency, int)
    assert rct_dsp2.PingFinder.center_frequency.__doc__ != ''
    assert hasattr(pf_, 'run_num')
    assert isinstance(pf_.run_num, int)
    assert rct_dsp2.PingFinder.run_num.__doc__ != ''
    assert hasattr(pf_, 'enable_test_data')
    assert isinstance(pf_.enable_test_data, bool)
    assert rct_dsp2.PingFinder.enable_test_data.__doc__ != ''
    assert hasattr(pf_, 'output_dir')
    assert isinstance(pf_.output_dir, str)
    assert rct_dsp2.PingFinder.output_dir.__doc__ != ''
    assert hasattr(pf_, 'test_data_path')
    assert isinstance(pf_.test_data_path, str)
    assert rct_dsp2.PingFinder.test_data_path.__doc__ != ''
    assert hasattr(pf_, 'ping_width_ms')
    assert isinstance(pf_.ping_width_ms, int)
    assert rct_dsp2.PingFinder.ping_width_ms.__doc__ != ''
    assert hasattr(pf_, 'ping_min_snr')
    assert isinstance(pf_.ping_min_snr, float)
    assert rct_dsp2.PingFinder.ping_min_snr.__doc__ != ''
    assert hasattr(pf_, 'ping_max_len_mult')
    assert isinstance(pf_.ping_max_len_mult, float)
    assert rct_dsp2.PingFinder.ping_max_len_mult.__doc__ != ''
    assert hasattr(pf_, 'ping_min_len_mult')
    assert isinstance(pf_.ping_min_len_mult, float)
    assert rct_dsp2.PingFinder.ping_min_len_mult.__doc__ != ''
    assert hasattr(pf_, 'target_frequencies')
    assert isinstance(pf_.target_frequencies, list)
    assert rct_dsp2.PingFinder.target_frequencies.__doc__ != ''
    assert hasattr(pf_, 'start')
    assert pf_.start.__doc__ != ''
    assert hasattr(pf_, 'stop')
    assert pf_.stop.__doc__ != ''
    assert hasattr(pf_, 'sdr_type')
    assert pf_.stop.__doc__ != ''

    assert rct_dsp2.SDR_TYPE_USRP
    assert rct_dsp2.SDR_TYPE_AIRSPY
    assert rct_dsp2.SDR_TYPE_HACKRF
    assert rct_dsp2.SDR_TYPE_FILE
    assert rct_dsp2.SDR_TYPE_GENERATOR
