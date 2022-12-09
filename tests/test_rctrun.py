"""RCTRun Test
"""
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Tuple

import pytest
import yaml
from test_uib import FakeUIBoard

from autostart.rctrun import RCTRun


@pytest.fixture(name='test_env')
def create_test_env() -> Tuple[Path]:
    """Creates a test environment

    Returns:
        Tuple[Path]: Path object of test config

    Yields:
        Iterator[Tuple[Path]]: _description_
    """
    ui_board = FakeUIBoard()
    ui_board.start()
    with TemporaryDirectory() as tmp_output_dir:
        config = {
            'DSP_pingMax': 1.5,
            'DSP_pingMin': 0.5,
            'DSP_pingSNR': 0.1,
            'DSP_pingWidth': 27,
            'GPS_baud': 9600,
            'GPS_device': ui_board.serial_pty,
            'GPS_mode': False,
            'SDR_centerFreq': 173500000,
            'SDR_gain': 20.0,
            'SDR_samplingFreq': 1500000,
            'SYS_autostart': False,
            'SYS_outputDir': tmp_output_dir,
            'TGT_frequencies': [173964000]
        }
        with NamedTemporaryFile(mode="w+") as handle:
            yaml.safe_dump(config, handle)
            yield (Path(handle.name),)
    ui_board.stop()

@pytest.mark.timeout(10)
def test_initialization(test_env: Tuple[Path]):
    """Tests that the initialization occurs without throwing errors

    Args:
        test_env (Tuple[Path]): Test Environment
    """
    app = RCTRun(
        tcpport=9000,
        config_path=test_env[0]
    )
    app.start()
