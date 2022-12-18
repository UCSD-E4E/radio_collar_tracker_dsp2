import argparse
import datetime
import json
import logging
import logging.handlers
import os
import subprocess
import threading
import time
from enum import Enum, auto
from pathlib import Path
from threading import Condition, Event
from typing import Any, Callable, Dict, List, Optional

import serial
import yaml
from RCTComms.comms import EVENTS, mavComms, rctBinaryPacketFactory
from RCTComms.transport import RCTTCPClient

from autostart.networking import NetworkMonitor
from autostart.states import (GPS_STATES, OUTPUT_DIR_STATES, RCT_STATES,
                              SDR_INIT_STATES)
from autostart.tcp_command import CommandListener
from autostart.UIB_instance import UIBoard
from RCTDSP2 import PingFinder

WAIT_COUNT = 60

testDir = Path("../testOutput")

class RCTRun:
    class Event(Enum):
        """Callback events

        """
        START_RUN = auto()
        STOP_RUN = auto()

    class Flags(Enum):
        """Events
        """
        SDR_READY = auto()
        GPS_READY = auto()
        STORAGE_READY = auto()
        INIT_COMPLETE = auto()

    def __init__(self,
            tcpport: int,
            test = False, *,
            config_path: Path = Path('/usr/local/etc/rct_config'),
            allow_nonmount: bool = False):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        self.__config_path = config_path
        self.__allow_nonmount = allow_nonmount

        self.__callbacks: Dict[RCTRun.Event, List[Callable[[RCTRun.Event], None]]] = \
            {evt:[] for evt in RCTRun.Event}
        self.events: Dict[RCTRun.Event, Condition] = {evt: Condition() for evt in RCTRun.Event}

        self.flags = {evt: Event() for evt in RCTRun.Flags}

        self.__output_path: Optional[Path] = None

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

        self.heatbeat_thread_stop = threading.Event()
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.network_monitor = NetworkMonitor(
            network_profile=self.get_var('SYS_network')
        )

    def register_cb(self, event: Event, cb_: Callable[[Event], None]) -> None:
        """Registers a new callback for the specified event

        Args:
            event (Event): Event to register for
            cb_ (Callable[[Event], None]): Callback function
        """
        self.__callbacks[event].append(cb_)

    def execute_cb(self, event: Event) -> None:
        """Executes an event's callbacks

        Args:
            event (Event): Event to execute
        """
        with self.events[event]:
            self.events[event].notify_all()
        for cb_ in self.__callbacks[event]:
            cb_(event)

    def remove_cb(self, event: Event, cb_: Callable[[Event], None]) -> None:
        """Removes the specified callback from the specified event

        Args:
            event (Event): Event to remove from
            cb_ (Callable[[Event], None]): Callback to remove
        """
        self.__callbacks[event].remove(cb_)

    def start(self):
        """Starts all RCTRun Threads
        """
        self.init_comms()
        self.init_threads()
        self.heartbeat_thread = threading.Thread(target=self.uib_heartbeat, name='UIB Heartbeat')
        self.heartbeat_thread.start()
        self.network_monitor.start()

    def stop(self):
        self.cmdListener.stop()
        self.heatbeat_thread_stop.set()
        self.heartbeat_thread.join()
        self.network_monitor.stop()

    def init_threads(self):
        """System Initialization thread execution
        """
        self.flags[self.Flags.INIT_COMPLETE].clear()
        self.init_sdr_thread = threading.Thread(target=self.initSDR,
            kwargs={'test':self.test}, name='SDR Init')
        self.init_output_thread = threading.Thread(target=self.initOutput,
            kwargs={'test':self.test}, name='Output Init')
        self.init_gps_thread = threading.Thread(target=self.initGPS,
            kwargs={'test':self.test}, name='GPS Init')
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

        self.flags[self.Flags.INIT_COMPLETE].set()


    def uib_heartbeat(self):
        while not self.heatbeat_thread_stop.is_set():
            if self.heatbeat_thread_stop.wait(timeout=1):
                break
            else:
                self.UIB_Singleton.send_heartbeat()

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
        log = logging.getLogger('Stop Run Callback')
        log.info("Stop Run Callback")
        self.UIB_Singleton.system_state = RCT_STATES.wait_end.value
        if self.ping_finder is not None:
            self.ping_finder.stop()
        self.execute_cb(self.Event.STOP_RUN)
        self.init_threads()


    def startReceived(self, packet, addr):
        self.run()


    def run(self):
        log = logging.getLogger('run')
        self.execute_cb(self.Event.START_RUN)
        try:
            if self.cmdListener.startFlag:
                self.UIB_Singleton.system_state = RCT_STATES.start.value

                if not self.test:
                    run_dirs = list(self.__output_path.glob('RUN_*'))
                    if len(run_dirs) > 0:
                        run_num = int(sorted([run_dir.name for run_dir in run_dirs])[-1][4:]) + 1
                        logging.debug("Run Num:")
                        logging.debug(run_num)
                    else:
                        run_num = 1
                run_dir = self.__output_path.joinpath(f'RUN_{run_num:06d}')
                if not self.test:
                    run_dir.mkdir(parents=True, exist_ok=True)
                else:
                    try:
                        run_dir.mkdir(parents=True, exist_ok=True)
                    except:
                        pass

                localize_file = run_dir.joinpath(f'LOCALIZE_{run_num:06d}')
                localize_file.touch()
                    
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
                    self.ping_finder.output_dir = run_dir.as_posix()
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

                    self.ping_finder.register_callback(self.UIB_Singleton.send_ping)

                    self.ping_finder.start()
                    logging.debug("Started pingFinder")
        except Exception as exc:
            log.exception(exc)
            raise exc

    def initGPS(self, test = False):
        # pylint: disable=unused-argument
        self.flags[self.Flags.GPS_READY].clear()
        self.UIB_Singleton.gps_ready.wait()
        self.flags[self.Flags.GPS_READY].set()

    def initSDR(self, test = False):
        log = logging.getLogger("SDR Init")
        self.flags[self.Flags.SDR_READY].clear()
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
        self.flags[self.Flags.SDR_READY].set()

    def initOutput(self, test):
        log = logging.getLogger('InitOutput')
        self.flags[self.Flags.STORAGE_READY].clear()
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
                        self.__output_path = Path(output_dir)
                        dirNameFound = True
                        print("OUTPUTDIR_INIT:\trctConfig Directory:")
                        print("OUTPUTDIR_INIT:\t" + output_dir)
                        self.UIB_Singleton.storage_state = OUTPUT_DIR_STATES.check_output_dir
                elif not outputDirFound:
                    if test:
                        self.__output_path = testDir
                    valid_dir = True
                    if not self.__output_path.is_dir():
                        valid_dir = False
                        log.error("Output path is not a directory")
                    if not self.__allow_nonmount and not self.__output_path.is_mount():
                        valid_dir = False
                        log.error("Output path is not a mount, nonmount not permitted")
                    if valid_dir:
                        outputDirFound = True
                        self.UIB_Singleton.storage_state = OUTPUT_DIR_STATES.check_space
                    else:
                        time.sleep(10)
                        self.UIB_Singleton.storage_state = OUTPUT_DIR_STATES.wait_recycle
                elif not enoughSpace:
                    df = subprocess.Popen(['df', '-B1', self.__output_path.as_posix()], stdout=subprocess.PIPE)
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
        self.flags[self.Flags.STORAGE_READY].set()


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
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', type=Path)
    parser.add_argument('--no_mount', action='store_true')
    args = parser.parse_args()

    kwargs = {
        'tcpport': 9000
    }
    if args.config:
        kwargs['config_path'] = args.config
    kwargs['allow_nonmount'] = args.no_mount
    app = RCTRun(**kwargs)
    app.start()
    while True:
        pass

if __name__ == "__main__":
    main()
