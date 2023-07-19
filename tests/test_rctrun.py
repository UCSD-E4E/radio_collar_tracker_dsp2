"""RCTRun Test
"""
import socket
import time
from pathlib import Path
from time import sleep
from typing import Tuple
from unittest.mock import Mock

import pytest
from RCTComms.comms import gcsComms, rctSTARTCommand, rctSTOPCommand
from RCTComms.transport import RCTTCPClient

from autostart.rctrun import RCT_STATES, RCTRun


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


@pytest.mark.timeout(10)
def test_initialization(test_env: Tuple[Path], test_port: int):
    """Tests that the initialization occurs without throwing errors

    Args:
        test_env (Tuple[Path]): Test Environment
    """
    app = RCTRun(
        config_path=test_env[0],
        allow_nonmount=True
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
        config_path=test_env[0],
        allow_nonmount=True
    )
    app.start()

    transport = RCTTCPClient(port, '127.0.0.1')
    gcs_mock = gcsComms(transport)
    gcs_mock.start()
    time.sleep(5)
    gcs_mock.stop()
    app.stop()

@pytest.fixture(name='running_system')
def create_running_system(test_env: Tuple[Path], test_port: int) -> Tuple[RCTRun, gcsComms]:
    """Sets up a running and connected system

    Args:
        test_env (Tuple[Path]): Test Environment
        test_port (int): Test Port

    Returns:
        Tuple[RCTRun, gcsComms]: MAV and GCS pair

    Yields:
        Iterator[Tuple[RCTRun, gcsComms]]: MAV and GCS pair
    """
    app = RCTRun(
        config_path=test_env[0],
        allow_nonmount=True
    )
    app.start()

    transport = RCTTCPClient(test_port, '127.0.0.1')
    gcs = gcsComms(transport)
    gcs.start()
    yield app, gcs
    gcs.stop()
    app.stop()

@pytest.mark.timeout(20)
def test_start_runner(running_system: Tuple[RCTRun, gcsComms]):
    """Tests starting and stopping run

    Args:
        running_system (Tuple[RCTRun, gcsComms]): MAV and GCS
    """
    mav, gcs = running_system
    gcs.sendPacket(rctSTARTCommand())
    time.sleep(1)
    assert mav.UIB_Singleton.system_state in [RCT_STATES.start.value, RCT_STATES.wait_end.value]
    gcs.sendPacket(rctSTOPCommand())
    with mav.events[mav.Event.STOP_RUN]:
        assert mav.events[mav.Event.STOP_RUN].wait(timeout=8)
    assert mav.flags[mav.Flags.INIT_COMPLETE].wait(timeout=8)
    assert mav.UIB_Singleton.system_state in [RCT_STATES.start.value, RCT_STATES.wait_end.value]

def test_uib_heartbeats(test_env: Tuple[Path]):
    config_path, = test_env
    dut = RCTRun(config_path=config_path,
                 allow_nonmount=True)
    dut.UIB_Singleton.send_heartbeat = Mock()
    dut.heartbeat_thread.start()
    dut.heartbeat_thread.join()
    sleep(5)
    assert dut.UIB_Singleton.send_heartbeat.assert_called_once()
