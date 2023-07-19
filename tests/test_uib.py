'''UI Board Test
'''
import json
import time
from threading import Event, Thread
from typing import Tuple

import pytest
from conftest import FakeUIBoard
from mock_serial import MockSerial
from serial import Serial

import autostart.UIB_instance as dut


def uib_send_heartbeat(port: Serial, stop_event: Event):
    """Sends heartbeat messages

    Args:
        port (Serial): Serial port
        stop_event (Event): Stop Event
    """
    while not stop_event.is_set():
        output = {
            'STR': 1,
            'SYS': 3,
            'SDR': 5
        }
        port.write(json.dumps(output).encode())
        time.sleep(1)

def uib_receive_status(port: Serial, stop_event: Event, expected_count: Tuple[int, int]):
    """UIB Receive Status Message

    Args:
        port (Serial): Serial Port
        stop_event (Event): Stop Event
        expected_count (Tuple[int, int]): Expected iterations
    """
    count = 0
    while not stop_event.is_set():
        port.timeout = 2
        line = port.readline().decode()
        data = json.loads(line)
        assert data is not None
        count += 1

    assert expected_count[0] <= count <= expected_count[1]

@pytest.mark.timeout(8)
def test_fake_uiboard():
    """Testing the fake UI Board
    """
    uib = FakeUIBoard()
    uib.start()
    stop_event = Event()
    stop_event.clear()
    with Serial(uib.serial_pty, baudrate=9600) as port:
        thread1 = Thread(
            target=uib_send_heartbeat,
            args=(port, stop_event),
            name='uib_send_hb')
        thread1.start()
        thread2 = Thread(
            target=uib_receive_status,
            args=(port, stop_event, (3, 6)),
            name='uib_rx')
        thread2.start()
        time.sleep(4)
        stop_event.set()
        thread2.join()
        thread1.join()
    uib.stop()


@pytest.fixture(name='ui_board_devices')
def create_ui_board() -> Tuple[dut.UIBoard, MockSerial]:
    """Creates a fake UI Board

    Returns:
        Tuple[dut.UIBoard, MockSerial]: _description_

    Yields:
        Iterator[Tuple[dut.UIBoard, MockSerial]]: _description_
    """
    mock_serial = MockSerial()
    device = dut.UIBoard(
        port=mock_serial.port,
        baud=9600,
        test_mode=False
    )
    yield device, mock_serial

def test_send_heartbeat(ui_board_devices: Tuple[dut.UIBoard, MockSerial]):
    """Tests sending a heartbeat

    Args:
        ui_board_devices (Tuple[dut.UIBoard, MockSerial]): _description_
    """
    ui_board = ui_board_devices[0]
    ui_board.send_heartbeat()
