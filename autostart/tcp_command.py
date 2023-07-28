#!/usr/bin/env python3

import datetime
import json
import os
import socket
import subprocess
import sys
import time
from enum import IntEnum
from pathlib import Path
from typing import Any

from RCTComms.comms import (EVENTS, RctEngrCommand, mavComms, rctACKCommand,
                            rctBinaryPacketFactory, rctFrequenciesPacket,
                            rctGETFCommand, rctGETOPTCommand,
                            rctHeartBeatPacket, rctOptionsPacket,
                            rctSETFCommand, rctSETOPTCommand, rctSTARTCommand,
                            rctSTOPCommand, rctUPGRADECommand,
                            rctUpgradeStatusPacket)
from RCTComms.options import Options
from RCTComms.transport import RCTAbstractTransport

from autostart.options import RCTOpts
from autostart.UIB_instance import UIBoard
from autostart.utils import InstrumentedThread
from autostart.eng_cmd import handle_engr_cmd

class COMMS_STATES(IntEnum):
    disconnected = 0
    connected = 1



class CommandListener:
    """docstring for CommandListener"""
    def __init__(self,
            ui_board: UIBoard,
            transport: RCTAbstractTransport,
            *,
            config_path: Path = Path('/usr/local/etc/rct_config')):
        self.transport = transport
        self.port = mavComms(self.transport)

        self.ping_file = None
        self.num = None
        self.newRun = False
        self._run = True

        self.state = COMMS_STATES.disconnected
        self.sender = InstrumentedThread(target=self._sender,
                                         name='CommandListener_sender',
                                         daemon=True)
        self.reconnect = InstrumentedThread(target=self._reconnectComms,
                                            name='CommandListener_reconnect')

        self.startFlag = False
        self.UIBoard = ui_board
        self.UIBoard.switch = 0
        self.factory = rctBinaryPacketFactory()

        self.options = RCTOpts.get_instance(path=config_path)

        self.setup()

        self.port.start()
        self.sender.start()

    def __del__(self):
        self._run = False
        self.sender.join()
        self.port.stop()
        del self.port
        if self.ping_file is not None:
            self.ping_file.close()
            print('Closing file')


    def stop(self):
        self.port.stop()
        self._run = False
        self.sender.join()
        self.UIBoard.switch = 0


    def setRun(self, runDir: Path, runNum):
        self.newRun = True
        if self.ping_file is not None:
            self.ping_file.close()
            print('Closing file')
        path = runDir.joinpath(f'LOCALIZE_{runNum:06d}')

        if path.is_file():
            self.ping_file = open(path)
            print(f"Set and open file to {path.as_posix()}")
        else:
            raise Exception("File non existent!")

    def getStartFlag(self):
        return self.startFlag

    def _sender(self):
        prevTime = datetime.datetime.now()

        self.port.port_open_event.wait()

        heartbeat_period = self.options.get_option(Options.SYS_HEARTBEAT_PERIOD)
        while (self.port.isOpen()):
            try:
                now = datetime.datetime.now()
                if (now - prevTime).total_seconds() > heartbeat_period:
                    heartbeatPacket = rctHeartBeatPacket(self.UIBoard.system_state, 
                            self.UIBoard.sdr_state, self.UIBoard.sensor_state, 
                            self.UIBoard.storage_state, self.UIBoard.switch, now)

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
                while self.transport.isOpen():
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
        self.sender = InstrumentedThread(target=self._sender,
                                         name='CommandListener_sender',
                                         daemon=True)
        self.reconnect = InstrumentedThread(target=self._reconnectComms,
                                            name='CommandListener_sender')

        self.port.start()
        while not self.transport.isOpen():
            time.sleep(1)
        self.state = COMMS_STATES.connected
        print("starting sender")
        self._run = True
        self.sender.start()


    def _gotStartCmd(self, packet: rctSTARTCommand, addr):
        if self.UIBoard.ready():
            self.startFlag = True
            self.UIBoard.switch = 1
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
        self.options.set_option(Options.TGT_FREQUENCIES, freqs)
        self.options.writeOptions()
        packet = rctFrequenciesPacket(freqs)

        msg = packet
        self._sendAck(0x03, True)
        self.port.sendToGCS(msg)

    def _gotGetFCmd(self, packet: rctGETFCommand, addr):
        freqs = self.options.get_option(Options.TGT_FREQUENCIES)
        packet = rctFrequenciesPacket(freqs)
        msg = packet
        self._sendAck(0x02, True)
        self.port.sendToGCS(msg)

    def _gotGetOptsCmd(self, packet: rctGETOPTCommand, addr):
        opts = self.options.get_all_options()

        print("Get Comms Opts: ", opts)

        msg = rctOptionsPacket(packet.scope, opts)
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
        self.options.set_options(opts)
        self.options.writeOptions()
        options = self.options.get_all_options()
        msg = rctOptionsPacket(packet.scope, options)
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
        self.UIBoard.register_callback(
            EVENTS.DATA_PING, self.port.sendPing)
        self.UIBoard.register_callback(
            EVENTS.DATA_VEHICLE, self.port.sendVehicle)

    def _got_engr_cmd(self, packet: RctEngrCommand, addr: Any):
        handle_engr_cmd(packet.command_word, **packet.args)
