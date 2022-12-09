import datetime
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
from typing import Any

import serial
import yaml
from RCTComms.comms import EVENTS, mavComms, rctBinaryPacketFactory
from RCTComms.transport import RCTTCPClient

from autostart.tcp_command import CommandListener
from autostart.UIB_instance import UIBoard
from RCTDSP2 import PingFinder

WAIT_COUNT = 60

output_dir = None
testDir = "../testOutput"

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
    def __init__(self,
            tcpport: int,
            test = False, *,
            config_path: Path = Path('/usr/local/etc/rct_config')):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        self.__config_path = config_path

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
        testGPS = self.get_var('GPS_mode')
        self.UIB_Singleton = UIBoard(serialPort, baud, testGPS)
        logging.debug("RCTRun init: created UIB")
        self.cmdListener = None
        self.test = test
        self.tcpport = tcpport

        self.serialPort = serialPort
        self.ping_finder = None
        self.delete_comms_thread = None


    def start(self):
        """Starts all RCTRun Threads
        """
        self.init_comms()
        self.init_threads()

    def init_threads(self):
        """System Initialization thread execution
        """
        self.init_sdr_thread = threading.Thread(target=self.initSDR,
            kwargs={'test':self.test})
        self.init_output_thread = threading.Thread(target=self.initOutput,
            kwargs={'test':self.test})
        self.init_gps_thread = threading.Thread(target=self.initGPS,
            kwargs={'test':self.test})
        self.init_sdr_thread.start()
        logging.debug("RCTRun init: started SDR thread")
        self.init_output_thread.start()
        logging.debug("RCTRun init: started output thread")
        self.init_gps_thread.start()
        logging.debug("RCTRun init: started GPS thread")

        self.doRun = True

        self.init_sdr_thread.join()
        self.init_output_thread.join()
        self.init_gps_thread.join()
        self.UIB_Singleton.system_state = RCT_STATES.wait_start.value

    def init_comms(self):
        """Sets up the connection configuration
        """
        if self.cmdListener is None:
            logging.debug("CommandListener initialized")
            self.cmdListener = CommandListener(
                UIboard=self.UIB_Singleton,
                port=self.tcpport,
                config_path=self.__config_path)
            logging.warning("CommandListener connected")
            self.cmdListener.port.registerCallback(EVENTS.COMMAND_START, self.startReceived)
            self.cmdListener.port.registerCallback(EVENTS.COMMAND_STOP, self.stop_run_cb)


    def stop_run_cb(self, packet, addr): # pylint: disable=unused-argument
        """Callback for the stop recording command
        """
        self.UIB_Singleton.system_state = RCT_STATES.wait_end.value
        if self.ping_finder is not None:
            self.ping_finder.stop()
        self.init_threads()


    def startReceived(self, packet, addr):
        self.run()


    def run(self):
        log = logging.getLogger('run')
        try:
            if self.cmdListener.startFlag:
                self.UIB_Singleton.system_state = RCT_STATES.start.value

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
                    self.UIB_Singleton.system_state = RCT_STATES.wait_end.value
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
        except Exception as exc:
            log.exception(exc)
            raise exc




        

    def initGPS(self, test = False):
        log = logging.getLogger('InitGPS')
        try:
            self.UIB_Singleton.sensor_state = GPS_STATES.get_tty

            GPSInitialized = False
            counter = 0
            tty_stream = None

            prev_gps = 0

            if self.UIB_Singleton.testMode:
                self.UIB_Singleton.sensor_state = GPS_STATES.rdy
                logging.debug(f"External Sensor State: {self.UIB_Singleton.sensor_state}")
                return

            while not GPSInitialized:
                if self.UIB_Singleton.sensor_state == GPS_STATES.get_tty:
                    tty_device = self.get_var('GPS_device')
                    tty_device = self.serialPort
                    tty_baud = self.get_var('GPS_baud')
                    if not test:
                        try:
                            tty_stream = serial.Serial(tty_device, tty_baud, timeout = 1)
                        except serial.SerialException as exc:
                            self.UIB_Singleton.sensor_state = GPS_STATES.fail
                            print("GPS fail: bad serial!")
                            print(exc)
                            continue
                        if tty_stream is None:
                            self.UIB_Singleton.sensor_state = GPS_STATES.fail
                            print("GPS fail: no serial!")
                            continue
                        else:
                            self.UIB_Singleton.sensor_state = GPS_STATES.get_msg
                    else:
                        self.UIB_Singleton.sensor_state = GPS_STATES.get_msg

                elif self.UIB_Singleton.sensor_state == GPS_STATES.get_msg:
                    if not test:
                        try:
                            line = tty_stream.readline().decode("utf-8")
                        except serial.serialutil.SerialException as exc:
                            self.UIB_Singleton.sensor_state = GPS_STATES.fail
                            print("GPS fail: no serial!")
                            continue
                        if line is not None and line != "":
                            msg = None
                            try:
                                msg = json.loads(line)
                                self.UIB_Singleton.sensor_state = GPS_STATES.rdy
                            except json.JSONDecodeError as exc:
                                self.UIB_Singleton.sensor_state = GPS_STATES.fail
                                print("GPS fail: bad message!")
                                self.UIB_Singleton.sensor_state = GPS_STATES.get_msg
                                continue
                        else:
                            self.UIB_Singleton.sensor_state = GPS_STATES.get_msg
                    else:
                        time.sleep(1)
                        self.UIB_Singleton.sensor_state = GPS_STATES.rdy
                elif self.UIB_Singleton.sensor_state == GPS_STATES.wait_recycle:
                    time.sleep(1)
                    if counter > WAIT_COUNT / 2:
                        self.UIB_Singleton.sensor_state = GPS_STATES.fail
                        print("GPS fail: bad state!")
                        continue
                    else:
                        self.UIB_Singleton.sensor_state = GPS_STATES.get_msg
                elif self.UIB_Singleton.sensor_state == GPS_STATES.fail:
                    time.sleep(10)
                    self.UIB_Singleton.sensor_state = GPS_STATES.get_tty
                else: 
                    self.UIB_Singleton.sensor_state = GPS_STATES.rdy
                    GPSInitialized = True
                    print("GPS: Initialized")
                    if not test:
                        try:
                            line = tty_stream.readline().decode("utf-8")
                        except serial.serialutil.SerialException as exc:
                            self.UIB_Singleton.sensor_state = GPS_STATES.fail
                            print("GPS fail: no serial!")
                            continue
                        if line is not None and line != "":
                            msg = None
                            try:
                                msg = json.loads(line)
                                GPSInitialized = True
                            except json.JSONDecodeError as exc:
                                self.UIB_Singleton.sensor_state = GPS_STATES.fail
                                print("GPS fail: bad message!")
                                print(exc)
                                self.UIB_Singleton.sensor_state = GPS_STATES.get_msg
                                continue
                    else:
                        time.sleep(1)
                    current_gps = datetime.datetime.now()
                    if prev_gps == 0:
                        continue
                    else:
                        if (current_gps - prev_gps).total_seconds() > 5:
                            self.UIB_Singleton.sensor_state = GPS_STATES.wait_recycle
                    prev_gps = current_gps
        except Exception as exc:
            log.exception(exc)
            raise exc

    def initSDR(self, test = False):
        log = logging.getLogger("SDR Init")
        initialized = False
        devicesFound = False
        usrpDeviceInitialized = False
        try:
            while not initialized:

                if devicesFound == False:
                    if not test:
                        self.UIB_Singleton.sdr_state = SDR_INIT_STATES.find_devices
                        uhd_find_dev_retval = subprocess.run([
                            '/usr/bin/uhd_find_devices',
                            '--args=\"type=b200\"'],
                            capture_output=True,
                            encoding='utf-8')
                        if uhd_find_dev_retval.returncode == 0:
                            devicesFound = True
                            self.UIB_Singleton.sdr_state = SDR_INIT_STATES.usrp_probe
                            log.info("Devices Found")
                        else:
                            log.error("Devices not found: %s", uhd_find_dev_retval.stdout)
                            time.sleep(2)
                            self.UIB_Singleton.sdr_state = SDR_INIT_STATES.wait_recycle
                elif usrpDeviceInitialized == False:
                    if not test:
                        uhd_usrp_probe_retval = subprocess.run([
                            '/usr/bin/uhd_usrp_probe',
                            '--args=\"type=b200\"',
                            '--init-only'],
                            capture_output=True,
                            encoding='utf-8',
                            env={
                                "HOME": "/tmp"
                            })
                        if uhd_usrp_probe_retval.returncode == 0:
                            log.info("USRP Initialized")
                            usrpDeviceInitialized = True
                            initialized = True
                            self.UIB_Singleton.sdr_state = SDR_INIT_STATES.rdy
                        else:
                            log.error("USRP Initialized: %s", uhd_usrp_probe_retval.stderr)
                            self.UIB_Singleton.sdr_state = SDR_INIT_STATES.fail
                            devicesFound = False
                            usrpDeviceInitialized = False
        except Exception as exc:
            log.exception(exc)
            raise exc

    def initOutput(self, test):
        global output_dir
        log = logging.getLogger('InitOutput')
        try:
            outputDirInitialized = False
            dirNameFound = False
            outputDirFound = False
            enoughSpace = False

            self.UIB_Singleton.storage_state = OUTPUT_DIR_STATES.get_output_dir

            while not outputDirInitialized:
                if not dirNameFound:
                    output_dir = self.get_var('SYS_outputDir')
                    if output_dir is not None:
                        dirNameFound = True
                        print("OUTPUTDIR_INIT:\trctConfig Directory:")
                        print("OUTPUTDIR_INIT:\t" + output_dir)
                        self.UIB_Singleton.storage_state = OUTPUT_DIR_STATES.check_output_dir
                elif not outputDirFound:
                    if test:
                        output_dir = testDir
                    if os.path.isdir(output_dir):
                        outputDirFound = True
                        self.UIB_Singleton.storage_state = OUTPUT_DIR_STATES.check_space
                    else:
                        time.sleep(10)
                        self.UIB_Singleton.storage_state = OUTPUT_DIR_STATES.wait_recycle
                elif not enoughSpace:
                    df = subprocess.Popen(['df', '-B1', output_dir], stdout=subprocess.PIPE)
                    output = df.communicate()[0].decode('utf-8')
                    device, size, used, available, percent, mountpoint = output.split('\n')[1].split()
                    if int(available) > 20 * 60 * 1500000 * 4:
                        enoughSpace = True
                        outputDirInitialized = True
                        self.UIB_Singleton.storage_state = OUTPUT_DIR_STATES.rdy
                    else:
                        dirNameFound = False
                        outputDirFound = False
                        enoughSpace = False
                        self.UIB_Singleton.storage_state = OUTPUT_DIR_STATES.fail
                        print("OUTPUTDIR_INIT:\tNOT ENOUGH STORAGE SPACE")
        except Exception as exc:
            log.exception(exc)
            raise exc


    def get_var(self, var: str) -> Any:
        """Retrieves a parameter from config

        Args:
            var (str): Parameter key

        Returns:
            Any: Key value
        """
        with open(self.__config_path, 'r', encoding='ascii') as handle:
            config = yaml.safe_load(handle)
        return config[var]

def main():
    app = RCTRun(tcpport=9000)
    app.start()

if __name__ == "__main__":
    main()
