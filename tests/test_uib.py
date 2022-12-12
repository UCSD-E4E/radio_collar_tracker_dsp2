'''UI Board Test
'''
import datetime as dt
import json
import time
from threading import Event, Thread
from typing import Optional, Tuple

import numpy as np
import pytest
import utm
from mock_serial import MockSerial
from RCTComms.comms import rctHeartBeatPacket
from serial import Serial
from virtualserialports import VirtualSerialPorts

import autostart.UIB_instance as dut


class FakeUIBoard:
    """Creates a fake UI Board for testing
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, *,
            lat: float = 32.884041,
            lon: float = -117.235153,
            hdg: float = 45,
            step: float = 5,
            vcc: int = 5000,
            fix: int = 1,
            sat: int = 7):
        self.__ports = VirtualSerialPorts(num_ports=2, loopback=False)

        self.serial_pty = self.__ports.slave_names[0].as_posix()
        self.__port = self.__ports.slave_names[1]

        self.lat = lat
        self.lon = lon
        self.hdg = hdg
        hdg = np.deg2rad(hdg)
        rot_mat = np.array([[np.cos(hdg), -np.sin(hdg)],
                            [np.sin(hdg), np.cos(hdg)]])
        step_vec = np.array([0, step])
        self.step = np.matmul(rot_mat, step_vec)
        self.vcc = vcc
        self.fix = fix
        self.sat = sat
        self.__sendthread: Optional[Thread] = None
        self.__stop_event = Event()

    def start(self):
        """Starts the fake UI Board
        """
        self.__ports.run()
        self.__stop_event.clear()
        self.__sendthread = Thread(target=self.__send, name='MockUIBoardSend')
        self.__sendthread.start()

    def stop(self):
        """Stops the fake UI Board
        """
        self.__stop_event.set()
        self.__sendthread.join()
        self.__sendthread = None
        self.__ports.stop()

    def __send(self):
        seq = 0
        with Serial(port=self.__port.as_posix(), baudrate=9600) as port:
            while True:
                # do stuff
                now = dt.datetime.now()
                tme = now.strftime('%H%M%S')
                dte = now.strftime('%d%m%y')

                output_str = ("{\"seq\": %d, \"lat\": %ld, \"lon\": %ld, \"hdg\": %d," # pylint: disable=consider-using-f-string
                    " \"tme\": \"%s\", \"run\": \"%s\", \"fix\": %d, \"sat\": %d, "
                    "\"dat\": \"%s\"}\n" % (seq, int(self.lat * 1e7), int(self.lon * 1e7),
                    self.hdg, tme, 'false', int(self.fix), self.sat, dte))

                port.write(output_str.encode('ascii'))

                east, north, zonenum, zone = utm.from_latlon(self.lat, self.lon)
                new_coord = np.array([east, north]) + self.step

                self.lat, self.lon = utm.to_latlon(
                    easting=new_coord[0],
                    northing=new_coord[1],
                    zone_number=zonenum,
                    zone_letter=zone)
                seq += 1
                try:
                    if self.__stop_event.wait(timeout=1):
                        break
                except TimeoutError:
                    continue

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
        testMode=False
    )
    yield device, mock_serial

def test_send_heartbeat(ui_board_devices: Tuple[dut.UIBoard, MockSerial]):
    """Tests sending a heartbeat

    Args:
        ui_board_devices (Tuple[dut.UIBoard, MockSerial]): _description_
    """
    ui_board = ui_board_devices[0]
    packet = rctHeartBeatPacket(
        systemState=2,
        sdrState=3,
        sensorState=3,
        storageState=4,
        switchState=1
    )
    ui_board.handleHeartbeatPacket(packet=packet)
