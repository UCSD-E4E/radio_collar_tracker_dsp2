import datetime
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

import serial
from RCTComms.comms import EVENTS, rctPingPacket, rctVehiclePacket

from autostart.states import (GPS_STATES, OUTPUT_DIR_STATES, RCT_STATES,
                              SDR_INIT_STATES)


class UIBoard:
    def __init__(self, port="none", baud=115200, test_mode=False):
        '''
        Store current status
        store most recent GPS and Compass info
        Store most recent ping?
        '''
        self.__log = logging.getLogger("UI Board")
        self.__log.info("Initialized on %s at %d baud, mode=%s",
            port, baud, str(test_mode))

        self._system_state = 0
        self._sdr_state = 0
        self._sensor_state = 0
        self._storage_state = 0
        self._switch = 0

        self.__sensor_callbacks: Dict[EVENTS, List[Callable]]= {
            evt:[] for evt in EVENTS
        }

        self.lat = None
        self.lon = None
        self.timestamp = None

        self.test_mode = test_mode
        self.__port: Optional[serial.Serial] = None
        self.__device = port
        self.__baud = baud

        self.run = False
        self.listener = threading.Thread(target=self.uib_listener, name='UIB Listener')
        self.recentLoc = None
        self.gps_ready = threading.Event()

    @property
    def system_state(self) -> int:
        """System state indicator

        Returns:
            int: System state
        """
        return self._system_state

    @system_state.setter
    def system_state(self, state: Any) -> None:
        if not isinstance(state, int):
            raise RuntimeError("Illegal type")
        self._system_state = state
        self.__log.warning("System state set to %s", RCT_STATES(state).name)

    @property
    def sdr_state(self) -> int:
        """Software Defined Radio state indicator

        Returns:
            int: Software Defined Radio state
        """
        return self._sdr_state

    @sdr_state.setter
    def sdr_state(self, state: Any) -> None:
        if not isinstance(state, int):
            raise RuntimeError("Illegal type")
        self._sdr_state = state
        self.__log.warning("SDR state set to %s", SDR_INIT_STATES(state).name)

    @property
    def sensor_state(self) -> int:
        """External sensor state indicator

        Returns:
            int: External sensors state
        """
        return self._sensor_state

    @sensor_state.setter
    def sensor_state(self, state: Any) -> None:
        if not isinstance(state, int):
            raise RuntimeError('Illegal type')
        self._sensor_state = state
        self.__log.warning("Sensor state set to %s", GPS_STATES(state).name)

    @property
    def storage_state(self) -> int:
        """Storage state indicator

        Returns:
            int: Storage state
        """
        return self._storage_state

    @storage_state.setter
    def storage_state(self, state: Any) -> None:
        if not isinstance(state, int):
            raise RuntimeError('Illegal type')
        self._storage_state = state
        self.__log.warning("Storage state set to %s", OUTPUT_DIR_STATES(state).name)

    @property
    def switch(self) -> int:
        """Run switch state indicator

        Returns:
            int: Run switch
        """
        return self._switch

    @switch.setter
    def switch(self, state: Any) -> None:
        if not isinstance(state, int):
            raise RuntimeError('Illegal type')
        self._switch = state
        self.__log.warning("Switch state set to %d", state)

    def send_heartbeat(self):
        """Sends a heartbeat packet to the UI Board
        """
        if self.test_mode:
            return
        output = {
            'STR': self.storage_state,
            'SYS': self.system_state,
            'SDF': self.sdr_state
        }
        self.__port.write(json.dumps(output).encode())

    def __init_gps(self):
        if self.test_mode:
            self.sensor_state = GPS_STATES.rdy
            self.__log.debug('External Sensor State: %s', self.sensor_state)

        self.gps_ready.clear()

        self.sensor_state = GPS_STATES.get_tty
        while self.__port is None:
            try:
                self.__port = serial.Serial(self.__device, baudrate=self.__baud)
            except Exception as exc: # pylint: disable=broad-except
                self.__log.exception('Failed to create serial handle: %s', exc)
                self.sensor_state = GPS_STATES.fail
                time.sleep(1)

        self.sensor_state = GPS_STATES.get_msg
        while True:
            try:
                self.__port.timeout = 1
                line = self.__port.readline().decode(encoding='utf-8')
                if line is None or line == '':
                    raise TimeoutError
                json.loads(line)
                break
            except serial.SerialException as exc:
                self.__log.exception('Failed to read from serial: %s', exc)
                self.sensor_state = GPS_STATES.fail
                continue
            except TimeoutError:
                self.__log.exception('Failed to receive data')
                self.sensor_state = GPS_STATES.fail
                continue
            except json.JSONDecodeError as exc:
                self.__log.exception('Bad message: %s', line)
                self.sensor_state = GPS_STATES.fail
                continue

        self.sensor_state = GPS_STATES.rdy
        self.gps_ready.set()

    def uib_listener(self):
        '''
        Continuously listens to uib serial port for Sensor Packets
        '''
        self.__init_gps()
        if self.test_mode:
            lon = -117.23679
            lat = 32.88534
            while self.run:
                time.sleep(1)
                try:
                    lon += 1e-4
                    lat += 1e-4
                    hdg = 0
                    date = datetime.datetime.now()
                    packet = rctVehiclePacket(lat, lon, 0, hdg, date)
                    print(packet.lat, packet.lon)
                    self.handle_sensor_packet(packet)
                    self.recentLoc = [lat, lon, 0]
                except Exception as e:
                    print(str(e))
        else:
            self.__port.timeout = 1
            while self.run:
                try:
                    ret = self.__port.readline().decode("utf-8")
                except serial.SerialException as exc:
                    self.__log.exception(exc)
                    continue
                if ret is not None and ret != "":
                    try:
                        reading = json.loads(ret)
                    except json.JSONDecodeError:
                        self.__log.exception("Malformed UIB Location message")
                        continue
                    try:
                        lat = reading["lat"] / 1e7
                        lon = reading["lon"] / 1e7
                        hdg = reading["hdg"]
                        tme = reading["tme"]
                        dat = reading["dat"]

                        year_string = "20" + dat[4:6]
                        day = datetime.date(int(year_string), int(dat[2:4]), int(dat[0:2]))
                        tim = datetime.time(int(tme[0:2]), int(tme[2:4]), int(tme[4:6]))
                        date = datetime.datetime.combine(day, tim)

                        packet = rctVehiclePacket(
                            lat=lat,
                            lon=lon,
                            alt=0,
                            hdg=hdg,
                            timestamp=date)

                        self.recentLoc = [lat, lon, 0]

                        self.handle_sensor_packet(packet)

                    except Exception: # pylint: disable=broad-except
                        self.__log.exception('Failed to process sensor packet')

    def send_ping(self, now, amplitude, frequency):
        if self.recentLoc is not None:
            packet = rctPingPacket(self.recentLoc[0], self.recentLoc[1], self.recentLoc[2], amplitude, frequency, now)
            try:
                for callback in self.__sensor_callbacks[EVENTS.DATA_PING]:
                    callback(ping=packet)
            except Exception as exc: # pylint: disable=broad-except
                self.__log.exception('Ping Callback Exception: %s', exc)


    def handle_sensor_packet(self, packet):
        '''
        Callback Function to receive and decode sensor packet
        '''
        try:
            for callback in self.__sensor_callbacks[EVENTS.DATA_VEHICLE]:
                callback(vehicle=packet)
        except Exception as exc: # pylint: disable=broad-except
            self.__log.exception('Sensor Packet callback exception: %s', exc)

    def __del__(self):
        self.run = False
        self.listener.join()

    def register_callback(self, event: EVENTS, callback: Callable):
        self.__sensor_callbacks[event].append(callback)
        self.__log.debug("Registered %s", callback)

    def ready(self):
        return (self.sdr_state == 3) and (self.sensor_state == 3) and (self.storage_state == 4)
