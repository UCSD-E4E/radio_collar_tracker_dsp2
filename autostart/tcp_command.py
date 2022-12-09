#!/usr/bin/env python3

import datetime
import glob
import json
import os
import select
import socket
import subprocess
import sys
import threading
import time
import traceback
from curses.ascii import CR
from enum import IntEnum
from pathlib import Path
from re import I

import yaml
from RCTComms.comms import (EVENTS, mavComms, rctACKCommand, rctBinaryPacket,
                            rctBinaryPacketFactory, rctExceptionPacket,
                            rctFrequenciesPacket, rctGETFCommand,
                            rctGETOPTCommand, rctHeartBeatPacket,
                            rctOptionsPacket, rctSETFCommand, rctSETOPTCommand,
                            rctSTARTCommand, rctSTOPCommand, rctUPGRADECommand,
                            rctUpgradeStatusPacket)
from RCTComms.transport import RCTTCPClient, RCTTCPServer

from autostart.UIB_instance import UIBoard


class COMMS_STATES(IntEnum):
    disconnected = 0
    connected = 1

class RCTOpts(object):
    def __init__(self, *, config_path: Path = Path('/usr/local/etc/rct_config')):
        self._configFile = config_path
        self.options = ['DSP_pingWidth',
                'DSP_pingMin',
                'DSP_pingMax',
                'DSP_pingSNR',
                'SDR_gain',
                'GPS_mode',
                'GPS_device',
                'GPS_baud',
                'TGT_frequencies',
                'SYS_autostart',
                'SYS_outputDir',
                'SDR_samplingFreq',
                'SDR_centerFreq']
        self._params = {}
        self.loadParams()

    def get_var(self, var):
        retval = []
        with open(self._configFile) as var_file:
            config = yaml.safe_load(var_file)
            retval= config[var]
        return retval


    def loadParams(self):
        with open(self._configFile) as var_file:
            config = yaml.safe_load(var_file)
            for option in config:
                self._params[option] = config[option]

    def getOption(self, option: str):
        return self._params[option]
    

    def setOption(self, option, param):
        if option == "DSP_pingWidth":
            assert(isinstance(param, float))
            assert(param > 0)
        elif option == "DSP_pingSNR":
            assert(isinstance(param, float))
            assert(param > 0)
        elif option == "DSP_pingMax":
            assert(isinstance(param, float))
            assert(param > 1)
        elif option == "DSP_pingMin":
            assert(isinstance(param, str))
            assert(param < 1)
            assert(param > 0)
        elif option == "GPS_mode":
            assert(isinstance(param, str))
            assert(param == 'true' or param == 'false')
        elif option == "GPS_device":
            assert(isinstance(param, str))
        elif option == "GPS_baud":
            assert(isinstance(param, str))
            assert(param > 0)
        elif option == "SYS_autostart":
            assert(isinstance(param, str))
            assert(param == 'true' or param == 'false')
        elif option == "SYS_outputDir":
            assert(isinstance(param, str))
        elif option == "SDR_samplingFreq":
            assert(isinstance(param, int))
            assert(param > 0)
        elif option == "SDR_centerFreq":
            assert(isinstance(param, int))
            assert(param > 0)
        elif option == "SDR_gain":
            assert(isinstance(param, float))

        self._params[option] = param

    def setOptions(self, options: dict):
        # Error check first before committing
        for key, value in options.items():
            print("Option: ")
            print(key)
            print(value)
            if key == "DSP_pingWidth":
                self._params[key] = value
                assert(isinstance(value, float))
            elif key == "DSP_pingSNR":
                self._params[key] = value
                assert(isinstance(value, float))
                assert(value > 0)
            elif key == "DSP_pingMax":
                self._params[key] = value
                assert(isinstance(value, float))
                assert(value > 1)
            elif key == "DSP_pingMin":
                self._params[key] = value
                assert(isinstance(value, float))
                assert(value < 1)
                assert(value > 0)
            elif key == "GPS_mode":
                self._params[key] = value
                assert(isinstance(value, str))
                assert(value == 'true' or value == 'false')
            elif key == "GPS_device":
                self._params[key] = value
                assert(isinstance(value, str))
            elif key == "GPS_baud":
                self._params[key] = value
                assert(isinstance(value, int))
                assert(value > 0)
            elif key == "TGT_frequencies":
                self._params[key] = value
            elif key == "SYS_autostart":
                self._params[key] = value
                assert(isinstance(value, str))
                assert(value == 'true' or value == 'false')
            elif key == "SYS_outputDir":
                self._params[key] = value
                assert(isinstance(value, str))
            elif key == "SDR_samplingFreq":
                self._params[key] = value
                assert(isinstance(value, int))
                assert(value > 0)
            elif key == "SDR_centerFreq":
                self._params[key] = value
                assert(isinstance(value, int))
                assert(value > 0)
            elif key == "SDR_gain":
                self._params[key] = value



    def writeOptions(self):
        backups = glob.glob("/usr/local/etc/*.bak")
        if len(backups) > 0:
            backup_numbers = [os.path.basename(path).split('.')[0].lstrip('/usr/local/etc/rct_config') for path in backups]
            backup_numbers = [int(number) for number in backup_numbers if number != '']
            nextNumber = max(backup_numbers) + 1
        else:
            nextNumber = 1

        os.rename('/usr/local/etc/rct_config', '/usr/local/etc/rct_config%d.bak' % nextNumber)

        with open(self._configFile, 'w') as var_file:
            yaml.dump(self._params, var_file)

    def getAllOptions(self):
        return self._params

    def getCommsOptions(self):
        return self._params


class CommandListener(object):
    """docstring for CommandListener"""
    def __init__(self,
            UIboard: UIBoard,
            port: int, *,
            config_path: Path = Path('/usr/local/etc/rct_config')):
        super(CommandListener, self).__init__()
        self.sock = RCTTCPServer(port)
        self.port = mavComms(self.sock)
        self.portAddr = port

        self.ping_file = None
        self.num = None
        self.newRun = False
        self._run = True
        
        self.state = COMMS_STATES.disconnected
        self.sender = threading.Thread(target=self._sender)
        self.reconnect = threading.Thread(target=self._reconnectComms)

        self.startFlag = False
        self.UIBoard = UIboard
        self.UIBoard.switch = 0
        self.factory = rctBinaryPacketFactory()

        self.options = RCTOpts(config_path=config_path)

        self.setup()

        self.port.start()
        self.sender.start()

    def __del__(self):
        self._run = False
        self.sender.join()
        self.port.stop()
        del self.port
        self.UIBoard.run = False
        if self.ping_file is not None:
            self.ping_file.close()
            print('Closing file')


    def stop(self):
        self.port.stop()
        self._run = False
        self.sender.join()
        self.UIBoard.switch = 0


    def setRun(self, runDir, runNum):
        self.newRun = True
        if self.ping_file is not None:
            self.ping_file.close()
            print('Closing file')
        path = os.path.join(runDir, 'LOCALIZE_%06d' % (runNum))
        if os.path.isfile(path):
            self.ping_file = open(path)
            print("Set and open file to %s" % (os.path.join(runDir, 'LOCALIZE_%06d' % (runNum))))
        else:
            raise Exception("File non existent!")

    def getStartFlag(self):
        return self.startFlag

    def _sender(self):
        prevTime = datetime.datetime.now()

        self.port.port_open_event.wait()

        while (self.state == COMMS_STATES.connected):
            try:
                now = datetime.datetime.now()
                if (now - prevTime).total_seconds() > 1:
                    heartbeatPacket = rctHeartBeatPacket(self.UIBoard.system_state, 
                            self.UIBoard.sdr_state, self.UIBoard.sensor_state, 
                            self.UIBoard.storage_state, self.UIBoard.switch, now)

                    msg = heartbeatPacket
                    self.port.sendToGCS(msg)
                    self.UIBoard.handleHeartbeatPacket(msg)
                    prevTime = now
            except BrokenPipeError:
                print("broke pipe")
                self._run = False
                self.state = COMMS_STATES.disconnected
                self.startFlag = False
                self.UIBoard.switch = 0
                self.port.stop()
                if self.UIBoard.run:
                    self.UIBoard.stop()
                while self.sock.isOpen():
                    time.sleep(1)
                    print("still open")
                print("sock closed")
                self.reconnect.start()
            except Exception as e:
                print("Early Fail!")
                print(e)
                    
                time.sleep(1)
                continue

    def _reconnectComms(self):
        self.sender.join()
        self.sender = threading.Thread(target=self._sender)
        self.reconnect = threading.Thread(target=self._reconnectComms)

        self.port.start()
        while not self.sock.isOpen():
            time.sleep(1)
        self.state = COMMS_STATES.connected
        print("starting sender")
        self._run = True
        self.sender.start()


    def _gotStartCmd(self, packet: rctSTARTCommand, addr):
        if self.UIBoard.ready():
            self.startFlag = True
            self.UIBoard.switch = 1
            self.UIBoard.run = True
            self.UIBoard.listener.start()
            self._sendAck(0x07, True)
            print("Set start flag")
            self._sendAck(packet._pid, True)
        else:
            if not (self.UIBoard.storage_state == 4):
                print("Storage not ready!")
                print(self.UIBoard.storage_state)
            if not (self.UIBoard.sensor_state == 3):
                print("GPS not ready!")
                print(self.UIBoard.sensor_state)
            if not (self.UIBoard.sdr_state == 3):
                print("SDR not ready!")
                print(self.UIBoard.sdr_state)
            self._sendAck(packet._pid, True)

    def _gotStopCmd(self, packet: rctSTOPCommand, addr):
        self.startFlag = False
        self.UIBoard.switch = 0
        self.UIBoard.stop()
        self._sendAck(0x09, True)
        try:
            self.ping_file.close()
        except Exception as e:
            print(e)
        self.ping_file = None
        self._sendAck(packet._pid, True)

    def _gotSetFCmd(self, packet: rctSETFCommand, addr):
        if packet.frequencies is None:
            return
        freqs = packet.frequencies
        self.options.setOption('TGT_frequencies', freqs)
        self.options.writeOptions()
        packet = rctFrequenciesPacket(freqs)

        msg = packet
        self._sendAck(0x03, True)
        self.port.sendToGCS(msg)

    def _gotGetFCmd(self, packet: rctGETFCommand, addr):
        freqs = self.options.getOption('TGT_frequencies')
        packet = rctFrequenciesPacket(freqs)
        msg = packet
        self._sendAck(0x02, True)
        self.port.sendToGCS(msg)

    def _gotGetOptsCmd(self, packet: rctGETOPTCommand, addr):
        opts = self.options.getCommsOptions()

        print("Get Comms OPts: ", opts)
        
        msg = rctOptionsPacket(packet.scope, **opts)
        self._sendAck(0x04, True)
        self.port.sendToGCS(msg)


    def _gotWriteOptsCmd(self, packet, addr):
        if 'confirm' not in packet:
            return
        if packet['confirm'] == 'true':
            self.options.writeOptions()
            print("Writing params")
        else:
            # load from backup
            self.options.loadParams()
            print('Reloading params')


    def _gotSetOptsCmd(self, packet: rctSETOPTCommand, addr):
        opts = packet.options
        self.options.setOptions(opts)
        self.options.writeOptions()
        options = self.options.getCommsOptions()
        msg = rctOptionsPacket(packet.scope, **options)
        self._sendAck(0x05, True)
        self.port.sendToGCS(msg)
        self._sendAck(0x05, True)

    def _upgradeCmd(self, packet: rctUPGRADECommand, addr):
        #Upgrade Ready
        packet = rctUpgradeStatusPacket(0x00, "Upgrade Ready")
        msg = packet
        self.port.sendToGCS(msg)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = socket.gethostname()
        sock.settimeout(10)
        port = 9500
        sock.bind(('', port))
        byteCounter = 0
        sock.listen(1)
        try:
            conn, tcp_addr = sock.accept()

            with open('/tmp/upgrade.zip', 'wb') as archiveFile:
                frame = conn.recv(1024)
                byteCounter += len(frame)
                while frame:
                    archiveFile.write(frame)
                    frame = conn.recv(1024)
                    byteCounter += len(frame)
        except:
            return
        conn.close()
        print("Received %d bytes" % byteCounter)
        msgString = "Received %d bytes" % (byteCounter)
        statusPacket = rctUpgradeStatusPacket(0x01, msgString)
        msg = statusPacket
        self.port.sendToGCS(msg)

        try:
            retval = subprocess.call('unzip -u -o /tmp/upgrade.zip -d /tmp', shell=True)
            assert(retval == 0)
            msgString = "Unzipped"
            statusPacket.message = msgString
            msg = statusPacket
            self.port.sendToGCS(msg)
            print(msgString)


            retval = subprocess.call('./autogen.sh', shell=True, cwd='/tmp/radio_collar_tracker_drone-online_proc')
            assert(retval == 0)
            msgString = "autogen complete"
            msg = json.dumps(statusPacket)
            print(msgString)
            self.port.sendToGCS(msg)

            retval = subprocess.call('./configure', shell=True, cwd='/tmp/radio_collar_tracker_drone-online_proc')
            assert(retval == 0)
            msgString = "configure complete"
            statusPacket.message = msgString
            msg = statusPacket
            self.port.sendToGCS(msg)
            print(msgString)

            retval = subprocess.call('make', shell=True, cwd='/tmp/radio_collar_tracker_drone-online_proc')
            assert(retval == 0)
            msgString = "Make complete"
            statusPacket.message = msgString
            msg = statusPacket
            self.port.sendToGCS(msg)
            print(msgString)

            retval = subprocess.call('make install', shell=True, cwd='/tmp/radio_collar_tracker_drone-online_proc')
            assert(retval == 0)
            msgString = "Make installed"
            statusPacket.message = msgString
            msg = statusPacket
            self.port.sendToGCS(msg)
            print(msgString)

            msgString = 'upgrade_complete'
            statusPacket.message = msgString
            statusPacket.state = 0xFE
            msg = statusPacket
            print(msgString)
            self.port.sendToGCS(msg)

            print("I was run with: ")
            print(sys.argv)
            print(sys.argv[1:])
            os.execv(sys.argv[0], sys.argv)

        except Exception as e:
            packet = rctUpgradeStatusPacket(0xFF, str(e))

            msg = packet
            print(str(e))
            self.port.sendToGCS(msg)

    def _sendAck(self, id: int, result: bool):
        now = datetime.datetime.now()
        packet = rctACKCommand(id, result, now)
        self.port.sendToGCS(packet)
                        
        

    def setup(self):
        self.port.registerCallback(
            EVENTS.COMMAND_GETF, self._gotGetFCmd)
        self.port.registerCallback(
            EVENTS.COMMAND_SETF, self._gotSetFCmd)
        self.port.registerCallback(
            EVENTS.COMMAND_GETOPT, self._gotGetOptsCmd)
        self.port.registerCallback(
            EVENTS.COMMAND_SETOPT, self._gotSetOptsCmd)
        self.port.registerCallback(
            EVENTS.COMMAND_START, self._gotStartCmd)
        self.port.registerCallback(
            EVENTS.COMMAND_STOP, self._gotStopCmd)
        self.port.registerCallback(
            EVENTS.COMMAND_UPGRADE, self._upgradeCmd)
        self.UIBoard.registerSensorCallback(
            EVENTS.DATA_PING, self.port.sendPing)
        self.UIBoard.registerSensorCallback(
            EVENTS.DATA_VEHICLE, self.port.sendVehicle)