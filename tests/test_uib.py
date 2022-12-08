'''UI Board Test
'''
from typing import Tuple

import pytest
from mock_serial import MockSerial
from RCTComms.comms import rctHeartBeatPacket

import autostart.UIB_instance as dut


@pytest.fixture(name='ui_board_devices')
def create_ui_board() -> Tuple[dut.UIBoard, MockSerial]:
    mock_serial = MockSerial()
    device = dut.UIBoard(
        # port=mock_serial.port,
        port='/dev/ttyACM0',
        baud=9600,
        testMode=False
    )
    yield device, mock_serial

def test_send_heartbeat(ui_board_devices: Tuple[dut.UIBoard, MockSerial]):
    ui_board, mock_serial = ui_board_devices
    i = 1
    packet = rctHeartBeatPacket(
        systemState=2,
        sdrState=3,
        sensorState=3,
        storageState=4,
        switchState=1
    )
    ui_board.handleHeartbeatPacket(packet=packet)
