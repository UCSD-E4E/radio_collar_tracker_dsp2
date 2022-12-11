"""RCTRun Test
"""
import socket
import time
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Tuple

import pytest
import yaml
from RCTComms.comms import gcsComms
from RCTComms.transport import RCTTCPClient
from test_uib import FakeUIBoard

from autostart.rctrun import RCTRun


@pytest.fixture(name='test_port')
def get_next_free_port() -> int:
    """Retrieves the next free port

    Returns:
        int: Next free port
    """
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

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
def test_initialization(test_env: Tuple[Path], test_port: int):
    """Tests that the initialization occurs without throwing errors

    Args:
        test_env (Tuple[Path]): Test Environment
    """
    app = RCTRun(
        tcpport=test_port,
        config_path=test_env[0]
    )
    app.start()
    app.stop()

@pytest.mark.timeout(15)
def test_connect(test_env: Tuple[Path], test_port: int):
    """Tests GCS connection

    Args:
        test_env (Tuple[Path]): Test Environment
        test_port (int): Test Port
    """
    port = test_port
    app = RCTRun(
        tcpport=port,
        config_path=test_env[0]
    )
    app.start()

    transport = RCTTCPClient(port, '127.0.0.1')
    gcs_mock = gcsComms(transport)
    gcs_mock.start()
    time.sleep(5)
    gcs_mock.stop()
    app.stop()
