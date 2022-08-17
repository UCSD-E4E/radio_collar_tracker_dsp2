from mimetypes import init
import threading
import subprocess
import time
import os
import serial
import datetime
import json
import glob
import re
import select
from radio_collar_tracker_dsp2 import PingFinder
from enum import Enum, IntEnum
import yaml

from RCTComms.comms import (mavComms, rctBinaryPacketFactory, EVENTS)
from RCTComms.transport import RCTTCPClient
from RCTComms.stcomms import SETALARMCommand
from tcp_command import CommandListener
from UIB_instance import UIBoard
from ..tests.test_sleeptimer_comms import activateSleepTimer

WAIT_COUNT = 60

stop_threads = False

output_dir = None
testDir = "../testOutput"
testGPS = True

class GPS_STATES(IntEnum):
	get_tty = 0
	get_msg = 1
	wait_recycle = 2
	rdy = 3
	fail = 4

class SDR_INIT_STATES(IntEnum):
	find_devices = 0
	wait_recycle = 1
	usrp_probe = 2
	rdy = 3
	fail = 4

class OUTPUT_DIR_STATES(IntEnum):
	get_output_dir = 0
	check_output_dir = 1
	check_space = 2
	wait_recycle = 3
	rdy = 4
	fail = 5

class RCT_STATES(Enum):
	init		=	0
	wait_init	=	1
	wait_start	=	2
	start		=	3
	wait_end	=	4
	finish		=	5
	fail		=	6



class RCTRun:
    def __init__(self, tcpport: int, test = False):
        baud = int(self.get_var('GPS_baud'))
        serialPort = self.get_var('GPS_device')
        self.UIB_Singleton = UIBoard(serialPort, baud, testGPS)
        self.cmdListener = None
        self.test = test
        self.tcpport = tcpport

        self.serialPort = serialPort
        self.ping_finder = None
        self.delete_comms_thread = None

        self.init_comms_thread = threading.Thread(target=self.initComms)
        self.init_SDR_thread = threading.Thread(target=self.initSDR, kwargs={'test':test})
        self.init_output_thread = threading.Thread(target=self.initOutput, kwargs={'test':test})
        self.init_gps_thread = threading.Thread(target=self.initGPS, kwargs={'test':test})

        self.initSleepTimer()

        self.init_comms_thread.start()
        self.init_SDR_thread.start()
        self.init_output_thread.start()
        self.init_gps_thread.start()

        self.doRun = True

        self.init_SDR_thread.join()
        self.init_output_thread.join()
        self.init_gps_thread.join()
        self.init_sleeptimer_thread.join()

    def initSleepTimer(self):
        try:
            self.timerSerial = self.get_var('sleep_timer')
            self.timerBaud = int(self.get_var('sleep_timer_baud'))
            startTime = datetime.datetime.strptime(self.get_var('timer_start_time'), "%H:%M:%S")
            stopTime = datetime.datetime.strptime(self.get_var('timer_stop_time'), "%H:%M:%S")
            sampleRate = datetime.datetime.strptime(self.get_var('sampling_rate'), "%H:%M:%S")
        except:
            print("sleep timer parameters could not be read from config file")
        if self.timerSerial is None or self.timerBaud is None:
            print("sleep timer serial settings were not specified")
            return
        if startTime is not None and stopTime is not None:
            # Calculate msecs turned off
            timeOff = (startTime - stopTime).total_seconds() * 1000
            if timeOff < 0:
                timeOff += 24 * 60 * 60 * 1000
            # Calculate msecs until shut off time
            timeToSleep = (stopTime - datetime.datetime.now()).total_seconds()
            if (timeToSleep < 0):
                timeToSleep += 24 * 60 * 60
            threading.Timer(timeToSleep, self.activateSleepTimer, [timeOff])
        if sampleRate is not None:
            #sample for 30 seconds, sleep between samples
            runningTime = datetime.datetime.strptime("00:00:30", "%H:%M:%S")
            sleepTime = (sampleRate - runningTime).total_seconds() * 1000
            threading.Timer(runningTime, activateSleepTimer, [sleepTime])
            


    def initComms(self):
        if self.cmdListener is None:
            self.cmdListener = CommandListener(self.UIB_Singleton, self.tcpport)
            self.cmdListener.port.registerCallback(EVENTS.COMMAND_START, self.startReceived)
            self.cmdListener.port.registerCallback(EVENTS.COMMAND_STOP, self.stopRun)


    def stopRun(self, packet, addr):
        self.doRun = False
        if self.ping_finder is not None:
            self.ping_finder.stop()

    def startReceived(self, packet, addr):
        self.run()


    def run(self):
        if self.cmdListener.startFlag:

            if not self.test:
                meta_files = glob.glob(os.path.join(output_dir, 'RUN_*'))
                if len(meta_files) > 0:
                    run_num = int(re.sub("[^0-9]", "", sorted(meta_files)[-1])) + 1
                else:
                    run_num = 1
            run_dir = os.path.join(output_dir, 'RUN_%06d' % (run_num))
            if not self.test:
                os.makedirs(run_dir)
            else:
                try:
                    os.makedirs(run_dir)
                except:
                    pass

            localize_file = os.path.join(run_dir, 'LOCALIZE_%06d' % (run_num))
            with open(localize_file, 'w') as file:
                file.write("")
                
            self.cmdListener.setRun(run_dir, run_num)
            time.sleep(1)

            #TODO add dynamic sdr_record

            if not self.test:
                self.ping_finder = PingFinder()
                self.ping_finder.gain = self.cmdListener.options.getOption("gain")
                self.ping_finder.sampling_rate = self.cmdListener.options.getOption("sampling_freq")
                self.ping_finder.center_frequency = self.cmdListener.options.getOption("center_freq")
                self.ping_finder.run_num = run_num
                self.ping_finder.enable_test_data = False
                self.ping_finder.output_dir = self.cmdListener.options.getOption("output_dir")
                self.ping_finder.ping_width_ms = self.cmdListener.options.getOption("ping_width_ms")
                self.ping_finder.ping_min_snr = self.cmdListener.options.getOption("ping_min_snr")
                self.ping_finder.ping_max_len_mult = self.cmdListener.options.getOption("ping_max_len_mult")
                self.ping_finder.ping_min_len_mult = self.cmdListener.options.getOption("ping_min_len_mult")
                self.ping_finder.target_frequencies = self.cmdListener.options.getOption("frequencies")

                self.ping_finder.register_callback(self.UIB_Singleton.sendPing)

                self.ping_finder.start()




        

    def initGPS(self, test = False):

        self.UIB_Singleton.sensorState = GPS_STATES.get_tty

        GPSInitialized = False
        counter = 0
        msg_counter = 0
        tty_stream = None

        prev_gps = 0

        if testGPS:
            self.UIB_Singleton.sensorState = GPS_STATES.rdy
            return

        while not GPSInitialized:
            if self.UIB_Singleton.sensorState == GPS_STATES.get_tty:
                tty_device = self.get_var('GPS_device')
                tty_device = self.serialPort
                tty_baud = self.get_var('GPS_baud')
                if not test:
                    try:
                        tty_stream = serial.Serial(tty_device, tty_baud, timeout = 1)
                    except serial.SerialException as e:
                        self.UIB_Singleton.sensorState = GPS_STATES.fail
                        print("GPS fail: bad serial!")
                        print(e)
                        continue
                    if tty_stream is None:
                        self.UIB_Singleton.sensorState = GPS_STATES.fail
                        print("GPS fail: no serial!")
                        continue
                    else:
                        self.UIB_Singleton.sensorState = GPS_STATES.get_msg
                else:
                    self.UIB_Singleton.sensorState = GPS_STATES.get_msg

            elif self.UIB_Singleton.sensorState == GPS_STATES.get_msg:
                if not test:
                    try:
                        line = tty_stream.readline().decode("utf-8")
                    except serial.serialutil.SerialException as e:
                        self.UIB_Singleton.sensorState = GPS_STATES.fail
                        print("GPS fail: no serial!")
                        continue
                    if line is not None and line != "":
                        msg = None
                        try:
                            msg = json.loads(line)
                            self.UIB_Singleton.sensorState = GPS_STATES.rdy
                        except json.JSONDecodeError as e:
                            self.UIB_Singleton.sensorState = GPS_STATES.fail
                            print("GPS fail: bad message!")
                            self.UIB_Singleton.sensorState = GPS_STATES.get_msg
                            continue
                    else:
                        self.UIB_Singleton.sensorState = GPS_STATES.get_msg
                else:
                    time.sleep(1)
                    self.UIB_Singleton.sensorState = GPS_STATES.rdy
            elif self.UIB_Singleton.sensorState == GPS_STATES.wait_recycle:
                time.sleep(1)
                if counter > WAIT_COUNT / 2:
                    self.UIB_Singleton.sensorState = GPS_STATES.fail
                    print("GPS fail: bad state!")
                    continue
                else:
                    self.UIB_Singleton.sensorState = GPS_STATES.get_msg
            elif self.UIB_Singleton.sensorState == GPS_STATES.fail:
                time.sleep(10)
                self.UIB_Singleton.sensorState = GPS_STATES.get_tty
            else: 
                self.UIB_Singleton.sensorState = GPS_STATES.rdy
                GPSInitialized = True
                print("GPS: Initialized")
                if not test:
                    try:
                        line = tty_stream.readline().decode("utf-8")
                    except serial.serialutil.SerialException as e:
                        self.UIB_Singleton.sensorState = GPS_STATES.fail
                        print("GPS fail: no serial!")
                        continue
                    if line is not None and line != "":
                        msg = None
                        try:
                            msg = json.loads(line)
                            GPSInitialized = True
                        except json.JSONDecodeError as e:
                            self.UIB_Singleton.sensorState = GPS_STATES.fail
                            print("GPS fail: bad message!")
                            print(e)
                            self.UIB_Singleton.sensorState = GPS_STATES.get_msg
                            continue
                else:
                    time.sleep(1)
                current_gps = datetime.datetime.now()
                if prev_gps == 0:
                    continue
                else:
                    if (current_gps - prev_gps).total_seconds() > 5:
                        self.UIB_Singleton.sensorState = GPS_STATES.wait_recycle
                prev_gps = current_gps


    def initSDR(self, test = False):

        initialized = False
        devicesFound = False
        usrpDeviceInitialized = False
        devnull = open('/dev/null', 'w')

        while not initialized:
            global stop_threads
            if stop_threads:
                break

            if devicesFound == False:
                if not test:
                    self.UIB_Singleton.sdrState = SDR_INIT_STATES.find_devices
                    uhd_find_dev_retval = subprocess.call(['/usr/local/bin/uhd_find_devices', '--args=\"type=b200\"'], stdout=devnull, stderr=devnull)
                    if uhd_find_dev_retval == 0:
                        devicesFound = True
                        self.UIB_Singleton.sdrState = SDR_INIT_STATES.usrp_probe
                        print("SDR: Devices Found")
                    else:
                        time.sleep(1)
                        self.UIB_Singleton.sdrState = SDR_INIT_STATES.wait_recycle
            elif usrpDeviceInitialized == False:
                if not test:
                    uhd_usrp_probe_retval = subprocess.call(['/usr/local/bin/uhd_usrp_probe', '--args=\"type=b200\"', '--init-only'], stdout=devnull, stderr=devnull)
                    if uhd_usrp_probe_retval == 0:
                        print("SDR: USRP Initialized")
                        usrpDeviceInitialized = True
                        initialized = True
                        self.UIB_Singleton.sdrState = SDR_INIT_STATES.rdy
                    else:
                        self.UIB_Singleton.sdrState = SDR_INIT_STATES.fail
                        devicesFound = False
                        usrpDeviceInitialized = False
         

    def initOutput(self, test):
        global output_dir

        outputDirInitialized = False
        dirNameFound = False
        outputDirFound = False
        enoughSpace = False

        self.UIB_Singleton.storageState = OUTPUT_DIR_STATES.get_output_dir

        while not outputDirInitialized:
            if not dirNameFound:
                output_dir = self.get_var('SYS_outputDir')
                if output_dir is not None:
                    dirNameFound = True
                    print("OUTPUTDIR_INIT:\trctConfig Directory:")
                    print("OUTPUTDIR_INIT:\t" + output_dir)
                    self.UIB_Singleton.storageState = OUTPUT_DIR_STATES.check_output_dir
            elif not outputDirFound:
                if test:
                    output_dir = testDir
                if os.path.isdir(output_dir):
                    outputDirFound = True
                    self.UIB_Singleton.storageState = OUTPUT_DIR_STATES.check_space
                else:
                    time.sleep(10)
                    self.UIB_Singleton.storageState = OUTPUT_DIR_STATES.wait_recycle
            elif not enoughSpace:
                df = subprocess.Popen(['df', '-B1', output_dir], stdout=subprocess.PIPE)
                output = df.communicate()[0].decode('utf-8')
                device, size, used, available, percent, mountpoint = output.split('\n')[1].split()
                if int(available) > 20 * 60 * 1500000 * 4:
                    enoughSpace = True
                    outputDirInitialized = True
                    self.UIB_Singleton.storageState = OUTPUT_DIR_STATES.rdy
                else:
                    dirNameFound = False
                    outputDirFound = False
                    enoughSpace = False
                    self.UIB_Singleton.storageState = OUTPUT_DIR_STATES.fail
                    print("OUTPUTDIR_INIT:\tNOT ENOUGH STORAGE SPACE")



    def get_var(self, var: str):
        var_file = open('/usr/local/etc/rct_config')
        config = yaml.safe_load(var_file)
        return config[var]
        

    def activateSleepTimer(self, timeOff):
        global stop_threads
        stop_threads = True
        packet = SETALARMCommand(timeOff)
        with serial.Serial(port=self.timerSerial, baudrate=self.timerBaud) as ser:
            ser.write(packet.to_bytes)
        
def main():
    global stop_threads
    stop_threads = False
    RCTRun(tcpport=9000)

if __name__ == "__main__":
    main()