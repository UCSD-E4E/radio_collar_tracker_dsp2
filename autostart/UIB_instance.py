import datetime
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import serial
import smbus
from RCTComms.comms import EVENTS, rctPingPacket, rctVehiclePacket

from autostart.states import (GPS_STATES, OUTPUT_DIR_STATES, RCT_STATES,
                              SDR_INIT_STATES)
from autostart.utils import InstrumentedThread


class I2CUIBoard:
    def __init__(self, port="none", baud=115200, test_mode=False):
        '''
        Store current status
        store most recent GPS and Compass info
        Store most recent ping?
        '''
        self.__log = logging.getLogger("UI Board")
        # Get I2C bus
        self.bus = None

        self._system_state = 0
        self._sdr_state = 0
        self._sensor_state = 0
        self._storage_state = 0
        self._switch = 0
        # I2C parameters
        self.i2c_address = 0x1E  # HMC5983 I2C device address
        self.i2c_read = 0x3D  # HMC5983 I2C device read
        self.i2c_write = 0x3C # HMC5983 I2C device write

        self.__sensor_callbacks: Dict[EVENTS, List[Callable]]= {
            evt:[] for evt in EVENTS
        }

        self.lat = None
        self.lon = None
        self.timestamp = None

        self.test_mode = test_mode
        self.__port: port
        # grab the current directory then the number for i2c-X
        self.__port_num = int(self.__port.split("/")[-1].split("-")[-1])
       
        self.run = True
        self.gps_ready = threading.Event()
        self.listener = InstrumentedThread(target=self.uib_listener,
                                         name='UIB Listener',
                                         daemon=True)
        self.listener.start()
        self.recentLoc = None
        self.__last_timestamp: Optional[datetime.datetime] = None

        self.__monitor = InstrumentedThread(target=self.__monitor_fn,
                                          name='UIB Monitor',
                                          daemon=True)
        self.__monitor.start()

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
        self.__log.info("System state set to %s", RCT_STATES(state).name)

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
        # TODO: CHANGED
        if self.test_mode:
            return
        output = {
            'STR': self.storage_state,
            'SYS': self.system_state,
            'SDF': self.sdr_state
        }
        message = json.dumps(output).encode()
        message_len = len(json.dumps(output).encode())        
        # Break the data into chunks
        data_chunks = [message[i:i+31] for i in range(0, message_len, 31)]
        for chunk in data_chunks:
            try:
                self.bus.write_i2c_block_data(self.i2c_address, self.i2c_write, chunk)
            except Exception as exc:
                self.__log.exception('Failed to write to I2C')
                raise(exc)     

    def __init_gps(self):
        
        if self.test_mode:
            self.sensor_state = GPS_STATES.rdy
            self.__log.debug('External Sensor State: %s', self.sensor_state)
            return

        self.gps_ready.clear()

        self.sensor_state = GPS_STATES.get_tty

        while self.bus is None:
            try:
                self.bus = smbus.SMBus(self.__port_num)
            except Exception as exc: # pylint: disable=broad-except
                self.__log.error(f"Failed to open SMBus on port\
                                  i2c-{self.__port_num}: {str(exc)}")
                self.bus = None
                time.sleep(1)

        self.sensor_state = GPS_STATES.get_msg
        data = [] 
        while True:
            try:
                # TODO: CHANGED
                byte = self.bus.read_byte_data(self.i2c_address, self.i2c_read)
                if byte == 0x0A: # this represents the '\n' character
                    line_bytes = bytes(data) 
                    line = line_bytes.decode("utf-8")
                    if line is None or line == '':
                        self.__log.error("__init_gps: Received empty line")
                        continue
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as exc:
                        self.__log.exception('Bad message: %s', line)
                        self.sensor_state = GPS_STATES.fail
                        continue
                    break
                elif byte != 0x0A: 
                    data.append(byte)
                    continue
            except Exception as exc: 
                self.__log.exception(f"Error reading byte: {str(exc)}")
                continue  
        self.sensor_state = GPS_STATES.rdy
        self.__log.info('GPS Ready')
        self.gps_ready.set()

    def parse_uib_message(self, msg: str) -> \
            Tuple[float, float, float, datetime.datetime]:
        """Parses the UIB position message

        Raises:
            exc: json.JSONDecodeError if the message is malformed

        Returns:
            Tuple[float, float, float, datetime.datetime]: Lat, Lon, Heading,
            and timestamp
        """
        try:
            reading = json.loads(msg)
        except json.JSONDecodeError as exc:
            self.__log.exception('Malformed UIB Location message')
            raise exc
        lat = reading["lat"] / 1e7
        lon = reading["lon"] / 1e7
        hdg = reading["hdg"]
        tme = reading["tme"]
        dat = reading["dat"]

        year_string = "20" + dat[4:6]
        day = datetime.date(year=int(year_string),
                            month=int(dat[2:4]),
                            day=int(dat[0:2]))
        tim = datetime.time(hour=int(tme[0:2]),
                            minute=int(tme[2:4]),
                            second=int(tme[4:6]))
        date = datetime.datetime.combine(day, tim)
        return (lat, lon, hdg, date)

    def uib_listener(self):
        '''
        Continuously listens to uib I2C address for Sensor Packets
        '''
        # TODO: CHANGED
        self.__init_gps()
        lon = -117.23679
        lat = 32.88534
        while self.run:
            if self.test_mode:
                time.sleep(1)
                lon += 1e-4
                lat += 1e-4
                hdg = 0
                date = datetime.datetime.now()
            else:
                data = [] 
                while True:
                    byte = self.bus.read_byte_data(self.i2c_address, self.i2c_read)
                    if byte == 0x0A: # this represents the '\n' character
                        message_bytes = bytes(data)
                        message = message_bytes.decode("utf-8")
                        try:
                            lat, lon, hdg, date = self.parse_uib_message(message)
                            self.gps_ready.set()

                            packet = rctVehiclePacket(lat=lat,
                                                    lon=lon,
                                                    alt=0,
                                                    hdg=hdg,
                                                    timestamp=date)
                            self.recentLoc = [lat, lon, 0]

                            self.handle_sensor_packet(packet)
                            self.__last_timestamp = date
                            break
                        except json.JSONDecodeError:
                            continue

                    if byte != 0x0A: 
                        data.append(byte)
            
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
        self.__monitor.join()

    def register_callback(self, event: EVENTS, callback: Callable):
        self.__sensor_callbacks[event].append(callback)
        self.__log.debug("Registered %s", callback)

    def ready(self):
        return (self.sdr_state == 3) and (self.sensor_state == 3) and (self.storage_state == 4)

    def __monitor_fn(self):
        while self.run:
            if self.gps_ready.wait(1):
                break
        while self.run:
            time.sleep(1)
            now = datetime.datetime.now()
            if not self.__last_timestamp:
                self.__log.warning('No timestamp!')
                continue
            if (now - self.__last_timestamp).total_seconds() > 3:
                self.__log.warning("Stale location!")