'''Payload Test Support
'''
import datetime as dt
import logging
from pathlib import Path
from queue import Empty, Queue
from tempfile import NamedTemporaryFile, TemporaryDirectory
from threading import Event, Thread
from typing import Optional, Tuple

import numpy as np
import pytest
import utm
import yaml
from RCTComms.transport import RCTAbstractTransport
from serial import Serial
from virtualserialports import VirtualSerialPorts


class RCTQueueTransport(RCTAbstractTransport):
    """Queue based transport for testing
    """
    def __init__(self,
                 rx_q: 'Queue[bytes]',
                 tx_q: 'Queue[bytes]',
                 name: str) -> None:
        self.rx_q = rx_q
        self.tx_q = tx_q
        self.__open = False
        self.__log = logging.getLogger(name)
        self.__name = name
        super().__init__()

    def open(self) -> None:
        assert not self.__open
        self.__open = True

    def receive(self, buffer_len: int, timeout: int = None) -> Tuple[bytes, str]:
        assert self.__open
        try:
            data = self.rx_q.get(timeout=timeout)
            self.__log.info('Received %s', data)
        except Empty as exc:
            raise TimeoutError from exc
        return data, ''

    def send(self, data: bytes, dest) -> None:
        assert self.__open
        self.__log.info('Put %s', data)
        self.tx_q.put(data)

    def close(self) -> None:
        assert self.__open
        self.__open = False

    def isOpen(self) -> bool:
        return self.__open

    @property
    def port_name(self) -> str:
        return self.__name

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
                tme = now.strftime('%H%M%S.00')
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
            'GPS_mode': True,
            'SDR_centerFreq': 173500000,
            'SDR_gain': 20.0,
            'SDR_samplingFreq': 1500000,
            'SYS_autostart': False,
            'SYS_outputDir': tmp_output_dir,
            'TGT_frequencies': [173964000],
            'GCS_spec': 'serial:/dev/ttyUSB0?baud=57600',
            'SYS_heartbeat_period': 5,
        }
        with NamedTemporaryFile(mode='w+') as handle:
            yaml.safe_dump(config, handle)
            yield (Path(handle.name),)
    ui_board.stop()
