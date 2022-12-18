'''Test network monitoring
'''

import time
from unittest.mock import Mock
from uuid import uuid1

import nmcli
import pytest

from autostart.networking import NetworkMonitor as dut


def test_nonexistent_network():
    """Tests for a non-up network
    """
    monitor_interval = 1
    error_threshold = 5
    test_network_name = uuid1().hex
    with pytest.raises(RuntimeError):
        monitor = dut(
            network_profile=test_network_name,
            monitor_interval=monitor_interval,
            error_threshold=error_threshold
        )
    nmcli.connection.add(
        conn_type='wifi',
        name=test_network_name,
        options={
            'ssid': test_network_name
        }
    )
    monitor = dut(
        network_profile=test_network_name,
        monitor_interval=monitor_interval,
        error_threshold=error_threshold
    )

    mock = Mock()
    monitor.register_cb(monitor.Event.ON_NETWORK_LOSS, mock)

    monitor.start()
    time.sleep(error_threshold + monitor_interval * 2)
    mock.assert_called_once_with(monitor.Event.ON_NETWORK_LOSS)
    monitor.stop()
    nmcli.connection.delete(test_network_name)
