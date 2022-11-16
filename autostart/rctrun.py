import glob
import json
import logging
import logging.handlers
import os
import re
import subprocess
import threading
import time
from enum import Enum, IntEnum
from pathlib import Path

import serial
import yaml
from radio_collar_tracker_dsp2 import PingFinder
from RCTComms.comms import EVENTS, mavComms, rctBinaryPacketFactory
from RCTComms.transport import RCTTCPClient

from autostart.tcp_command import CommandListener
from autostart.UIB_instance import UIBoard

WAIT_COUNT = 60

stop_threads = False

output_dir = None
testDir = "../testOutput"
testGPS = False

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
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        if os.getuid() == 0:
            log_dest = Path('/var/log/rct.log')
        else:
            log_dest = Path('/tmp/rct.log')
        log_file_handler = logging.handlers.RotatingFileHandler(log_dest, maxBytes=5*1024*1024, backupCount=5)
        log_file_handler.setLevel(logging.DEBUG)

        root_formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
        log_file_handler.setFormatter(root_formatter)
        root_logger.addHandler(log_file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARN)

        error_formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
        console_handler.setFormatter(error_formatter)
        root_logger.addHandler(console_handler)
        logging.Formatter.converter = time.gmtime

        logging.debug("Started Payload")

        baud = int(self.get_var('GPS_baud'))
        serialPort = self.get_var('GPS_device')
        self.UIB_Singleton = UIBoard(serialPort, baud, testGPS)
        logging.debug("RCTRun init: created UIB")
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


        self.init_comms_thread.start()
        logging.debug("RCTRun init: started comms thread")
        self.init_SDR_thread.start()
        logging.debug("RCTRun init: started SDR thread")
        self.init_output_thread.start()
        logging.debug("RCTRun init: started output thread")
        self.init_gps_thread.start()
        logging.debug("RCTRun init: started GPS thread")

        self.doRun = True

        self.init_SDR_thread.join()
        self.init_output_thread.join()
        self.init_gps_thread.join()

    def initComms(self):
        if self.cmdListener is None:
            self.cmdListener = CommandListener(self.UIB_Singleton, self.tcpport)
            logging.debug("CommandListener initialized")
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
                    run_num = int(re.sub("[^0-9]", "", sorted(meta_files)[-1].replace(output_dir, ''))) + 1
                    logging.debug("Run Num:")
                    logging.debug(run_num)
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

            if True:
                logging.debug("Enterring start pingFinder")
                self.ping_finder = PingFinder()
                logging.debug("Enterring start pingFinder1")
                self.ping_finder.gain = self.cmdListener.options.getOption("SDR_gain")
                logging.debug("Enterring start pingFinder2")
                self.ping_finder.sampling_rate = self.cmdListener.options.getOption("SDR_samplingFreq")
                logging.debug("Enterring start pingFinder3")
                self.ping_finder.center_frequency = self.cmdListener.options.getOption("SDR_centerFreq")
                logging.debug("Enterring start pingFinder4")
                self.ping_finder.run_num = run_num
                logging.debug("Enterring start pingFinder5")
                self.ping_finder.enable_test_data = False
                logging.debug("Enterring start pingFinder6")
                self.ping_finder.output_dir = self.cmdListener.options.getOption("SYS_outputDir")
                logging.debug("Enterring start pingFinder7")
                self.ping_finder.ping_width_ms = self.cmdListener.options.getOption("DSP_pingWidth")
                logging.debug("Enterring start pingFinder8")
                self.ping_finder.ping_min_snr = self.cmdListener.options.getOption("DSP_pingSNR")
                logging.debug("Enterring start pingFinder9")
                self.ping_finder.ping_max_len_mult = self.cmdListener.options.getOption("DSP_pingMax")
                logging.debug("Enterring start pingFinder10")
                self.ping_finder.ping_min_len_mult = self.cmdListener.options.getOption("DSP_pingMin")
                logging.debug("Enterring start pingFinder11")
                self.ping_finder.target_frequencies = self.cmdListener.options.getOption("TGT_frequencies")

                self.ping_finder.register_callback(self.UIB_Singleton.sendPing)

                self.ping_finder.start()
                logging.debug("Started pingFinder")




        

    def initGPS(self, test = False):

        self.UIB_Singleton.sensorState = GPS_STATES.get_tty

        GPSInitialized = False
        counter = 0
        msg_counter = 0
        tty_stream = None

        prev_gps = 0

        if testGPS:
            self.UIB_Singleton.sensorState = GPS_STATES.rdy
            logging.debug("Sensor State:")
            logging.debug(self.UIB_Singleton.sensorState)
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
                    uhd_find_dev_retval = subprocess.call(['/usr/bin/uhd_find_devices', '--args=\"type=b200\"'], stdout=devnull, stderr=devnull)
                    if uhd_find_dev_retval == 0:
                        devicesFound = True
                        self.UIB_Singleton.sdrState = SDR_INIT_STATES.usrp_probe
                        print("SDR: Devices Found")
                    else:
                        time.sleep(1)
                        self.UIB_Singleton.sdrState = SDR_INIT_STATES.wait_recycle
            elif usrpDeviceInitialized == False:
                if not test:
                    uhd_usrp_probe_retval = subprocess.call(['/usr/bin/uhd_usrp_probe', '--args=\"type=b200\"', '--init-only'], stdout=devnull, stderr=devnull)
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
        

def main():
    global stop_threads
    logging.basicConfig(filename='example.log', filemode='w', level=logging.DEBUG)
    logging.debug("starting in main")
    stop_threads = False
    RCTRun(tcpport=9000)

if __name__ == "__main__":
    main()
