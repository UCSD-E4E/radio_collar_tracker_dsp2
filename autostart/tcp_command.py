#!/usr/bin/env python3

from curses.ascii import CR
import socket
import os
import json
import datetime
import time
import threading
import select
import subprocess
import sys
import glob
import traceback
from autostart.UIB_instance import UIBoard
from enum import IntEnum
import errno
from RCTComms.comms import (mavComms, rctBinaryPacketFactory, rctHeartBeatPacket, rctFrequenciesPacket, rctBinaryPacket, rctExceptionPacket, 
    rctOptionsPacket, rctUpgradeStatusPacket, rctSETOPTCommand, rctUPGRADECommand, rctSETFCommand, rctGETFCommand, rctGETOPTCommand, rctSTARTCommand,
    rctSTOPCommand, rctACKCommand, EVENTS)
from RCTComms.transport import RCTTCPClient, RCTTCPServer

class COMMS_STATES(IntEnum):
    disconnected = 0
    connected = 1

class RCTOpts(object):
    def __init__(self):
        self._configFile = '/usr/local/etc/rct_config'
        self.options = ['ping_width_ms',
                'ping_min_snr',
                'ping_max_len_mult',
                'ping_min_len_mult',
                'gain',
                'gps_mode',
                'gps_target',
                'gps_baud',
                'frequencies',
                'autostart',
                'output_dir',
                'sampling_freq',
                'center_freq']
        #self._params = {key:self.get_var(key) for key in self.options}
        self._params = {}
        self.loadParams()

    def get_var(self, var):
        retval = []
        with open(self._configFile) as var_file:
            for line in var_file:
                if line.split('=')[0].strip() == var:
                    retval.append(line.split('=')[1].strip().strip('"').strip("'"))
        return retval


    def loadParams(self):
        #self._params = {key:self._get_var(key) for key in self.options}
        with open(self._configFile) as var_file:
            for line in var_file:
                newVar = line.split('=')[0].strip()
                if newVar in self.options:
                    self._params[newVar] = line.split('=')[1].strip().strip('"').strip("'")

    def getOption(self, option):
        if option == 'frequencies':
            return [int(self._params[option])]
        return self._params[option]

    def setOption(self, option, param):
        if option == 'ping_width_ms':
            assert(isinstance(param, str))
            test = float(param)
            assert(test > 0)
        elif option == 'ping_min_snr':
            assert(isinstance(param, str))
            test = float(param)
            assert(test > 0)
        elif option == 'ping_max_len_mult':
            assert(isinstance(param, str))
            test = float(param)
            assert(test > 1)
        elif option == 'ping_min_len_mult':
            assert(isinstance(param, str))
            test = float(param)
            assert(test < 1)
            assert(test > 0)
        elif option == 'gps_mode':
            assert(isinstance(param, str))
            assert(param == 'true' or param == 'false')
        elif option == 'gps_target':
            assert(isinstance(param, str))
        elif option == 'gps_baud':
            assert(isinstance(param, str))
            test = int(param)
            assert(param > 0)
        elif option == 'frequencies':
            assert(isinstance(param, list))
            assert(all(isinstance(freq, int) and freq > 0 for freq in param))
        elif option == 'autostart':
            assert(isinstance(param, str))
            assert(param == 'true' or param == 'false')
        elif option == 'output_dir':
            assert(isinstance(param, str))
        elif option == 'sampling_freq':
            assert(isinstance(param, str))
            test = int(param)
            assert(test > 0)
        elif option == 'center_freq':
            assert(isinstance(param, str))
            test = int(param)
            assert(test > 0)
        self._params[option] = param

    def setOptions(self, options):
        # Error check first before committing
        for key, value in options.items():
            print("Option: ")
            print(key)
            print(value)
            if key == 'ping_width_ms':
                assert(isinstance(value, str))
                test = float(value)
                assert(test > 0)
            elif key == 'ping_min_snr':
                assert(isinstance(value, str))
                test = float(value)
                assert(test > 0)
            elif key == 'ping_max_len_mult':
                assert(isinstance(value, str))
                test = float(value)
                assert(test > 1)
            elif key == 'ping_min_len_mult':
                assert(isinstance(value, str))
                test = float(value)
                assert(test < 1)
                assert(test > 0)
            elif key == 'gps_mode':
                assert(isinstance(value, str))
                assert(value == 'true' or value == 'false')
            elif key == 'gps_target':
                assert(isinstance(value, str))
            elif key == 'gps_baud':
                assert(isinstance(value, str))
                test = int(value)
                assert(value > 0)
            elif key == 'frequencies':
                assert(isinstance(self._params, list))
                assert(all(isinstance(freq, int) and freq > 0 for freq in self._params))
            elif key == 'autostart':
                assert(isinstance(value, str))
                assert(value == 'true' or value == 'false')
            elif key == 'output_dir':
                assert(isinstance(value, str))
            elif key == 'sampling_freq':
                assert(isinstance(value, str))
                test = int(value)
                assert(test > 0)
            elif key == 'center_freq':
                assert(isinstance(value, str))
                test = int(value)
                assert(test > 0)


        for key, value in options.items():
            if isinstance(value, list):
                self._params[key] = value
            else:
                self._params[key] = [value]

    def writeOptions(self):
        #backups = glob.glob("&INSTALL_PREFIX/etc/*.bak")
        backups = glob.glob("*.bak")
        if len(backups) > 0:
            backup_numbers = [os.path.basename(path).split('.')[0].lstrip('rct_config') for path in backups]
            backup_numbers = [int(number) for number in backup_numbers if number != '']
            nextNumber = max(backup_numbers) + 1
        else:
            nextNumber = 1

        #os.rename('&INSTALL_PREFIX/etc/rct_config', '&INSTALL_PREFIX/etc/rct_config%d.bak' % nextNumber)
        os.rename('rct_config', 'rct_config%d.bak' % nextNumber)

        with open(self._configFile, 'w') as var_file:
            for key, value in list(self._params.items()):
                for val in value:
                    opt = '%s=%s\n' % (key, val)
                    print(opt.strip())
                    var_file.write(opt)

    def getAllOptions(self):
        return self._params

    def getCommsOptions(self):
        commsOpts = {}
        for key in self._params:
            if key == 'ping_width_ms':
                commsOpts["DSP_pingWidth"] = self._params[key]
            if key == 'ping_min_snr':
                commsOpts["DSP_pingSNR"] = self._params[key]
            if key == 'ping_max_len_mult':
                commsOpts["DSP_pingMax"] = self._params[key]
            if key == 'ping_min_len_mult':
                commsOpts["DSP_pingMin"] = self._params[key]
            if key == 'gps_mode':
                commsOpts["GPS_mode"] = self._params[key]
            if key == 'gps_target':
                commsOpts["GPS_device"] = self._params[key]
            if key == 'gps_baud':
                commsOpts["GPS_baud"] = self._params[key]
            if key == 'frequencies':
                commsOpts["frequencies"] = self._params[key]
            if key == 'autostart':
                commsOpts["SYS_autostart"] = self._params[key]
            if key == 'output_dir':
                commsOpts["SYS_outputDir"] = self._params[key]
            if key == 'sampling_freq':
                commsOpts["SDR_samplingFreq"] = self._params[key]
            if key == 'center_freq':
                commsOpts["SDR_centerFreq"] = self._params[key]
            if key == 'gain':
                commsOpts['SDR_gain'] = self._params[key]

        return commsOpts


class CommandListener(object):
    """docstring for CommandListener"""
    def __init__(self, UIboard: UIBoard, port):
        super(CommandListener, self).__init__()
        self.sock = RCTTCPServer(port)
        self.port = mavComms(self.sock)
        self.portAddr = port

        self.ping_file = None
        self.num = None
        self.newRun = False
        self._run = True
        
        self.state = COMMS_STATES.connected
        self.sender = threading.Thread(target=self._sender)
        self.reconnect = threading.Thread(target=self._reconnectComms)
        #self.receiver = threading.Thread(target=self._listener)
        self.startFlag = False
        self.UIBoard = UIboard
        self.UIBoard.switch = 0
        self.factory = rctBinaryPacketFactory()

        self._options = RCTOpts()

        self.setup()

        self.port.start()
        self.sender.start()
        #self.receiver.start()

    def __del__(self):
        self._run = False
        self.sender.join()
        #self.receiver.join()
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

        while (self.state == COMMS_STATES.connected):
            try:
                now = datetime.datetime.now()
                if (now - prevTime).total_seconds() > 1:
                    heartbeatPacket = rctHeartBeatPacket(self.UIBoard.systemState, 
                            self.UIBoard.sdrState, self.UIBoard.sensorState, 
                            self.UIBoard.storageState, self.UIBoard.switch, now)

                    msg = heartbeatPacket
                    self.port.sendToGCS(msg)
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
            print("Set start flag")
            self._sendAck(0x07, True)
        else:
            if not (self.UIBoard.storageState == 4):
                print("Storage not ready!")
                print(self.UIBoard.storageState)
            if not (self.UIBoard.sensorState == 3):
                print("GPS not ready!")
                print(self.UIBoard.sensorState)
            if not (self.UIBoard.sdrState == 3):
                print("SDR not ready!")
                print(self.UIBoard.sdrState)
            self._sendAck(0x07, True)

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

    def _gotSetFCmd(self, packet: rctSETFCommand, addr):
        if packet.frequencies is None:
            return
        freqs = packet.frequencies
        self._options.setOption('frequencies', freqs)
        self._options.writeOptions()
        packet = rctFrequenciesPacket(freqs)

        msg = packet
        self.port.sendToGCS(msg)

    def _gotGetFCmd(self, packet: rctGETFCommand, addr):
        freqs = self._options.getOption('frequencies')
        packet = rctFrequenciesPacket(freqs)
        msg = packet
        self.port.sendToGCS(msg)

    def _gotGetOptsCmd(self, packet: rctGETOPTCommand, addr):
        opts = self._options.getCommsOptions()

        print(opts)
        
        packet = rctOptionsPacket(scope=255, kwargs=opts)
        msg = packet
        self.port.sendToGCS(msg)


    def _gotWriteOptsCmd(self, packet, addr):
        if 'confirm' not in packet:
            return
        if packet['confirm'] == 'true':
            self._options.writeOptions()
            print("Writing params")
        else:
            # load from backup
            self._options.loadParams()
            print('Reloading params')


    def _gotSetOptsCmd(self, packet: rctSETOPTCommand, addr):
        opts = packet.options
        self._options.setOptions(opts)
        options = self._options.getAllOptions()
        packet = rctOptionsPacket(255, options)
        msg = packet
        self.port.sendToGCS(msg)

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

    def _processCommand(self, packet, addr):
        commands = {
            'test': lambda: None,
            'start': self._gotStartCmd,
            'stop': self._gotStopCmd,
            'setF': self._gotSetFCmd,
            'getF': self._gotGetFCmd,
            'getOpts': self._gotGetOptsCmd,
            'setOpts': self._gotSetOptsCmd,
            'writeOpts': self._gotWriteOptsCmd,
            'upgrade': self._upgradeCmd
        }

        print('Got action: %s' % (packet['action']))

        try:
            commands[packet['action']](packet, addr)
        except Exception as e:
            print(e)
            packet = rctExceptionPacket(str(e), "   ")
            msg = packet
            print(str(e))
            self.port.sendToGCS(msg)

    def _sendAck(self, id: int, result: bool):
        now = datetime.datetime.now()
        packet = rctACKCommand(id, result, now)
        self.port.sendToGCS(packet)

    def _listener(self):
        
        while self._run:
            ready = select.select([self.sock], [], [], 1)
            if ready[0]:
                data, addr = self.port.receive(1024)
                
                packets = self.factory.parseBytes(data)
                id = None
                if len(packets) > 0 and (self.state == COMMS_STATES.disconnected):
                    self.state = COMMS_STATES.connected
                for packet in packets:
                    if packet.matches(0x05, 0x02):
                        id = 0x02
                        self._gotGetFCmd(packet, addr)
                    elif packet.matches(0x05, 0x03):
                        id = 0x03
                        self._gotSetFCmd(packet, addr)
                    elif packet.matches(0x05, 0x04):
                        id = 0x04
                        self._gotGetOptsCmd(packet, addr)
                    elif packet.matches(0x05, 0x05):
                        id = 0x05
                        self._gotSetOptsCmd(packet, addr)
                    elif packet.matches(0x05, 0x07):
                        id = 0x07
                        self._gotStartCmd(packet, addr)
                    elif packet.matches(0x05, 0x09):
                        id = 0x09
                        self._sendAck(id)
                        self._gotStopCmd(packet, addr)
                    elif packet.matches(0x05, 0x0B):
                        id = 0x0B
                        self._sendAck(id)
                        self._upgradeCmd(packet, addr)
                        
        

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