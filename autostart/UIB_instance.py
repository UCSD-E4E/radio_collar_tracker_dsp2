import datetime
import serial
import threading
import time
import json
import traceback
from RCTComms.comms import (rctHeartBeatPacket, rctVehiclePacket, rctPingPacket, EVENTS)


class UIBoard:
    def __init__(self, port="none", baud=115200):
        '''
        Store current status
        store most recent GPS and Compass info
        Store most recent ping?
        '''
        self.systemState = 0
        self.sdrState = 0
        self.sensorState = 0
        self.storageState = 0
        self.switch = 0

        self.__sensorCallbacks = {}
        self.__sensorCallbacks[EVENTS.DATA_VEHICLE] = []
        self.__sensorCallbacks[EVENTS.DATA_PING] = []

        self.lat = None
        self.lon = None
        self.timestamp = None

        self.port = port
        self.baud = baud

        self.run = False
        self.listener = threading.Thread(target=self.uibListener)
        self.recentLoc = None
        #self.sender = threading.Thread(target=self.doHeartbeat)

        #self.sender.start()

        #Sensor packet is baked into the c++
        #No longer baked into c++



    def sendStatus(self, packet: rctHeartBeatPacket):
        '''
        Function to send Status to the UI Board
        '''
        with serial.Serial(port=self.port, baudrate=self.baud) as ser:
            ser.write(packet.to_bytes)


    def uibListener(self):
        '''
        Continuously listens to uib serial port for Sensor Packets
        '''
        with serial.Serial(port=self.port, baudrate=self.baud, timeout=2) as ser:
            while self.run:
                ret = ser.readline().decode("utf-8")
                if ret is not None and ret != "":
                    reading = json.loads(ret)
                    try:
                        lat = reading["lat"] / 1e7
                        lon = reading["lon"] / 1e7
                        hdg = reading["hdg"]
                        tme = reading["tme"]
                        dat = reading["dat"]

                        yearString = "20" + dat[4:6]
                        day = datetime.date(int(yearString), int(dat[2:4]), int(dat[0:2]))
                        time = datetime.time(int(tme[0:2]), int(tme[2:4]), int(tme[4:6]))
                        date = datetime.datetime.combine(day, time)

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
                    status_string = "%d%d%d%d%d" % (self.systemState, 
                        self.sdrState, self.sensorState, 
                        self.storageState, self.switch)
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
        self.listener = threading.Thread(target=self.uibListener)
        self.switch = 0

    def registerSensorCallback(self, event, callback):
        self.__sensorCallbacks[event].append(callback)

    def ready(self):
        return (self.sdrState == 3) and (self.sensorState == 3) and (self.storageState == 4)
