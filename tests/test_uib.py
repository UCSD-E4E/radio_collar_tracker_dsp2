'''UI Board Test
'''
import datetime as dt
import json
import os
import pty
from threading import Event, Thread
from typing import Optional, Tuple

import numpy as np
import pytest
import utm
from mock_serial import MockSerial
from RCTComms.comms import rctHeartBeatPacket
from serial import Serial

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
        master, slave = pty.openpty()
        self.serial_pty = os.ttyname(slave)
        self.__portnum = master
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
        self.__stop_event.clear()
        self.__sendthread = Thread(target=self.__send)
        self.__sendthread.start()

    def stop(self):
        """Stops the fake UI Board
        """
        self.__stop_event.set()
        self.__sendthread.join()

    def __send(self):
        while True:
            # do stuff
            now = dt.datetime.now()
            tme = now.strftime('%H%M%S')
            dte = now.strftime('%d%m%y')

            output_str = ("{\"lat\": %ld, \"lon\": %ld, \"hdg\": %d," # pylint: disable=consider-using-f-string
                " \"tme\": \"%s\", \"run\": \"%s\", \"fix\": %d, \"sat\": %d, "
                "\"dat\": \"%s\"}\n" % (int(self.lat * 1e7), int(self.lon * 1e7),
                self.hdg, tme, 'false', int(self.fix), self.sat, dte))

            os.write(self.__portnum, output_str.encode('ascii'))

            east, north, zonenum, zone = utm.from_latlon(self.lat, self.lon)
            new_coord = np.array([east, north]) + self.step

            self.lat, self.lon = utm.to_latlon(
                easting=new_coord[0],
                northing=new_coord[1],
                zone_number=zonenum,
                zone_letter=zone)
            try:
                if self.__stop_event.wait(timeout=1):
                    break
            except TimeoutError:
                continue

@pytest.mark.timeout(4)
def test_fake_uiboard():
    uib = FakeUIBoard()
    uib.start()
    port = Serial(uib.serial_pty, baudrate=9600)
    line = port.readline().decode()
    data = json.loads(line)
    assert data is not None
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
