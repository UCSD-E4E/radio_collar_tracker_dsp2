import datetime
import json
import logging
import threading
import time
from typing import Any

import serial
from RCTComms.comms import (EVENTS, rctHeartBeatPacket, rctPingPacket,
                            rctVehiclePacket)


class UIBoard:
    def __init__(self, port="none", baud=115200, testMode=False):
        '''
        Store current status
        store most recent GPS and Compass info
        Store most recent ping?
        '''
        self.__log = logging.getLogger("UI Board")
        self.__log.info("Initialized on %s at %d baud, mode=%s",
            port, baud, str(testMode))

        self._system_state = 0
        self._sdr_state = 0
        self._sensor_state = 0
        self._storage_state = 0
        self._switch = 0

        self.__sensorCallbacks = {}
        self.__sensorCallbacks[EVENTS.DATA_VEHICLE] = []
        self.__sensorCallbacks[EVENTS.DATA_PING] = []

        self.lat = None
        self.lon = None
        self.timestamp = None

        self.port = port
        self.baud = baud
        self.testMode = testMode

        self.run = False
        self.listener = threading.Thread(target=self.uibListener, name='UIB Listener')
        self.recentLoc = None

        #self.sender = threading.Thread(target=self.doHeartbeat)

        #self.sender.start()

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
        self.__log.warning("System state set to %d", state)

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
        self.__log.warning("SDR state set to %d", state)

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
        self.__log.warning("Sensor state set to %d", state)

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
        self.__log.warning("Storage state set to %d", state)

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

    def sendStatus(self, packet: rctHeartBeatPacket):
        '''
        Function to send Status to the UI Board
        '''
        with serial.Serial(port=self.port, baudrate=self.baud) as ser:
            # ser.write(packet.to_bytes())
            output = {
                'STR': packet.storageState,
                'SYS': packet.systemState,
                'SDR': packet.sdrState
            }
            ser.write(json.dumps(output).encode())


    def uibListener(self):
        '''
        Continuously listens to uib serial port for Sensor Packets
        '''
        if self.testMode:
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
                    self.handleSensorPacket(packet)
                    self.recentLoc = [lat, lon, 0]
                except Exception as e:
                    print(str(e))
        else:
            with serial.Serial(port=self.port, baudrate=self.baud, timeout=2) as ser:
                while self.run:
                    try:
                        ret = ser.readline().decode("utf-8")
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

                            yearString = "20" + dat[4:6]
                            day = datetime.date(int(yearString), int(dat[2:4]), int(dat[0:2]))
                            tim = datetime.time(int(tme[0:2]), int(tme[2:4]), int(tme[4:6]))
                            date = datetime.datetime.combine(day, tim)

                            packet = rctVehiclePacket(lat, lon, 0, hdg, date)

                            self.recentLoc = [lat, lon, 0]

                            self.handleSensorPacket(packet)

                        except Exception as e:
                            print(str(e))

    def sendPing(self, now, amplitude, frequency):
        if self.recentLoc is not None:
            packet = rctPingPacket(self.recentLoc[0], self.recentLoc[1], self.recentLoc[2], amplitude, frequency, now)
            try:
                for callback in self.__sensorCallbacks[EVENTS.DATA_PING]:
                    callback(ping=packet)
            except Exception as e:
                print("UI_BOARD_SINGLETON:\tCALLBACK_EXCEPTION")
                print(str(e))


    def handleSensorPacket(self, packet):
        '''
        Callback Function to receive and decode sensor packet
        '''
        print("SENSOR PACKET")

        try:
            for callback in self.__sensorCallbacks[EVENTS.DATA_VEHICLE]:
                callback(vehicle=packet)
        except Exception as e:
            print("UI_BOARD_SINGLETON:\tCALLBACK_EXCEPTION")
            print(str(e))
        

    def handleHeartbeatPacket(self, packet):
        '''
        Callback Function to receive heartbeat packet
        '''
        self.sendStatus(packet)

    def doHeartbeat(self):
        prevTime = datetime.datetime.now()
        #sendTarget = (self.target_ip, self.port)

        while self.run:
            try:
                now = datetime.datetime.now()
                if (now - prevTime).total_seconds() > 1:
                    heartbeatPacket = {}
                    heartbeatPacket['heartbeat'] = {}
                    heartbeatPacket['heartbeat']['time'] = time.mktime(now.timetuple())
                    heartbeatPacket['heartbeat']['id'] = 'mav'
                    status_string = "%d%d%d%d%d" % (self.system_state, 
                        self.sdr_state, self.sensor_state, 
                        self.storage_state, self.switch)
                    heartbeatPacket['heartbeat']['status'] = status_string
                    msg = json.dumps(heartbeatPacket)
                    #self.sock.sendto(msg.encode('utf-8'), sendTarget)
                    with serial.Serial(port=self.port, baudrate=self.baud, timeout=2) as ser:
                        ser.write(msg.encode('utf-8'))
                    prevTime = now

                if self.ping_file is not None:
                    line = self.ping_file.readline()
                    if line == '':
                        continue
                    if 'stop' in json.loads(line):
                        print('Got stop')
                    # 	break
                    with serial.Serial(port=self.port, baudrate=self.baud, timeout=2) as ser:
                        ser.write(line.encode('utf-8'))
            except Exception as e:
                print("Early Fail!")
                print(e)
                continue

    def __del__(self):
        #self.sender.join()
        if self.run:
            self.listener.join()
        self.run = False


    def stop(self):
        self.run = False
        #self.sender.join()
        self.listener.join()
        self.listener = threading.Thread(target=self.uibListener, name='UIB Listener')
        self.switch = 0

    def registerSensorCallback(self, event, callback):
        self.__sensorCallbacks[event].append(callback)

    def ready(self):
        return (self.sdr_state == 3) and (self.sensor_state == 3) and (self.storage_state == 4)
