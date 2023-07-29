import argparse
import logging
import logging.handlers
import os
import shutil
import subprocess
import sys
import threading
import time
from enum import Enum, auto
from pathlib import Path
from threading import Condition, Event
from typing import Callable, Dict, List, Optional

from RCTComms.comms import EVENTS
from RCTComms.transport import RCTTransportFactory

from autostart.networking import NetworkMonitor, NetworkProfileNotFound
from autostart.options import Options, RCTOpts
from autostart.states import OUTPUT_DIR_STATES, RCT_STATES, SDR_INIT_STATES
from autostart.tcp_command import CommandListener
from autostart.UIB_instance import UIBoard
from autostart.utils import InstrumentedThread
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
            test = False, *,
            config_path: Path = Path('/usr/local/etc/rct_config'),
            allow_nonmount: bool = False,
            service: bool = False):
        self.__options = RCTOpts.get_instance(config_path)

        if service and not self.__options.get_option(Options.SYS_AUTOSTART):
            raise RuntimeError('No Autostart from service')

        self.__config_path = config_path
        self.__allow_nonmount = allow_nonmount

        self.__callbacks: Dict[RCTRun.Event, List[Callable[[RCTRun.Event], None]]] = \
            {evt:[] for evt in RCTRun.Event}
        self.events: Dict[RCTRun.Event, Condition] = {evt: Condition() for evt in RCTRun.Event}

        self.flags = {evt: Event() for evt in RCTRun.Flags}

        self.__output_path: Optional[Path] = None

        self.__log = logging.getLogger('RCTRun')

        self.__log.debug("Started Payload")

        baud = int(self.__options.get_option(Options.GPS_BAUD))
        serialPort = self.__options.get_option(Options.GPS_DEVICE)
        testGPS = self.__options.get_option(Options.GPS_MODE)
        self.gcs_spec = self.__options.get_option(Options.GCS_SPEC)
        self.UIB_Singleton = UIBoard(serialPort, baud, testGPS)
        self.__log.debug("RCTRun init: created UIB")
        self.cmdListener = None
        self.test = test

        self.serialPort = serialPort
        self.ping_finder = None
        self.delete_comms_thread = None

        self.heatbeat_thread_stop = threading.Event()

        self.heartbeat_thread = InstrumentedThread(target=self.uib_heartbeat,
                                                 name='UIB Heartbeat',
                                                 daemon=True)
        self.init_sdr_thread: Optional[InstrumentedThread] = None
        self.init_output_thread: Optional[InstrumentedThread] = None
        self.init_gps_thread: Optional[InstrumentedThread] = None
        try:
            self.network_monitor = NetworkMonitor(
                network_profile=self.__options.get_option(Options.SYS_NETWORK),
                monitor_interval=int(self.__options.get_option(Options.SYS_WIFI_MONITOR_INTERVAL))
            )
        except KeyError:
            self.network_monitor = None
        except NetworkProfileNotFound:
            self.network_monitor = None
        

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
        self.check_for_external_update()
        self.init_comms()
        self.init_threads()
        self.heartbeat_thread.start()
        if self.network_monitor:
            self.network_monitor.start()

    def stop(self):
        self.cmdListener.stop()
        self.heatbeat_thread_stop.set()
        self.heartbeat_thread.join()
        if self.network_monitor:
            self.network_monitor.stop()

    def init_threads(self):
        """System Initialization thread execution
        """
        self.flags[self.Flags.INIT_COMPLETE].clear()
        self.init_sdr_thread = InstrumentedThread(target=self.initSDR,
                                                kwargs={'test':self.test},
                                                name='SDR Init')
        self.init_sdr_thread.start()
        self.__log.debug("RCTRun init: started SDR thread")
        self.init_output_thread = InstrumentedThread(target=self.initOutput,
                                                   kwargs={'test':self.test},
                                                   name='Output Init')
        self.init_output_thread.start()
        self.__log.debug("RCTRun init: started output thread")
        self.init_gps_thread = InstrumentedThread(target=self.initGPS,
                                                kwargs={'test':self.test},
                                                name='GPS Init')
        self.init_gps_thread.start()
        self.__log.debug("RCTRun init: started GPS thread")

        self.doRun = True

        self.init_sdr_thread.join()
        self.__log.debug('SDR init thread joined')
        self.init_output_thread.join()
        self.__log.debug('Output init thread joined')
        self.init_gps_thread.join()
        self.__log.debug('GPS init thread joined')
        self.UIB_Singleton.system_state = RCT_STATES.wait_start.value

        self.flags[self.Flags.INIT_COMPLETE].set()


    def uib_heartbeat(self):
        heartbeat_period = self.__options.get_option(Options.SYS_HEARTBEAT_PERIOD)
        self.__log.info('Sending heartbeats every %d seconds', heartbeat_period)
        while not self.heatbeat_thread_stop.is_set():
            if self.heatbeat_thread_stop.wait(timeout=heartbeat_period):
                break
            self.UIB_Singleton.send_heartbeat()

    def init_comms(self):
        """Sets up the connection configuration
        """
        if self.cmdListener is None:
            self.__log.debug("CommandListener initialized")
            transport = RCTTransportFactory.create_transport(self.gcs_spec)
            self.cmdListener = CommandListener(
                ui_board=self.UIB_Singleton,
                transport=transport,
                config_path=self.__config_path)
            self.__log.warning("CommandListener connected")
            self.cmdListener.port.registerCallback(EVENTS.COMMAND_START, self.startReceived)
            self.cmdListener.port.registerCallback(EVENTS.COMMAND_STOP, self.stop_run_cb)


    def stop_run_cb(self, packet, addr): # pylint: disable=unused-argument
        """Callback for the stop recording command
        """
        self.__log.info("Stop Run Callback")
        self.UIB_Singleton.system_state = RCT_STATES.wait_end.value
        if self.ping_finder is not None:
            self.ping_finder.stop()
        self.execute_cb(self.Event.STOP_RUN)
        self.init_threads()


    def startReceived(self, packet, addr):
        self.run()


    def run(self):
        self.execute_cb(self.Event.START_RUN)
        try:
            if self.cmdListener.startFlag:
                self.UIB_Singleton.system_state = RCT_STATES.start.value

                if not self.test:
                    run_dirs = list(self.__output_path.glob('RUN_*'))
                    if len(run_dirs) > 0:
                        run_num = int(sorted([run_dir.name for run_dir in run_dirs])[-1][4:]) + 1
                        self.__log.debug("Run Num:")
                        self.__log.debug(run_num)
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

                opts = self.cmdListener.options
                if True:
                    self.UIB_Singleton.system_state = RCT_STATES.wait_end.value
                    self.__log.debug("Enterring start pingFinder")
                    self.ping_finder = PingFinder()
                    self.__log.debug("Enterring start pingFinder1")
                    self.ping_finder.gain = opts.get_option(Options.SDR_GAIN)
                    self.__log.debug("Enterring start pingFinder2")
                    self.ping_finder.sampling_rate = opts.get_option(Options.SDR_SAMPLING_FREQ)
                    self.__log.debug("Enterring start pingFinder3")
                    self.ping_finder.center_frequency = opts.get_option(Options.SDR_CENTER_FREQ)
                    self.__log.debug("Enterring start pingFinder4")
                    self.ping_finder.run_num = run_num
                    self.__log.debug("Enterring start pingFinder5")
                    self.ping_finder.enable_test_data = False
                    self.__log.debug("Enterring start pingFinder6")
                    self.ping_finder.output_dir = run_dir.as_posix()
                    self.__log.debug("Enterring start pingFinder7")
                    self.ping_finder.ping_width_ms = int(opts.get_option(Options.DSP_PING_WIDTH))
                    self.__log.debug("Enterring start pingFinder8")
                    self.ping_finder.ping_min_snr = opts.get_option(Options.DSP_PING_SNR)
                    self.__log.debug("Enterring start pingFinder9")
                    self.ping_finder.ping_max_len_mult = opts.get_option(Options.DSP_PING_MAX)
                    self.__log.debug("Enterring start pingFinder10")
                    self.ping_finder.ping_min_len_mult = opts.get_option(Options.DSP_PING_MIN)
                    self.__log.debug("Enterring start pingFinder11")
                    self.ping_finder.target_frequencies = opts.get_option(Options.TGT_FREQUENCIES)

                    self.ping_finder.register_callback(self.UIB_Singleton.send_ping)

                    self.ping_finder.start()
                    self.__log.debug("Started pingFinder")
        except Exception as exc:
            self.__log.exception(exc)
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
                    output_dir = self.__options.get_option(Options.SYS_OUTPUT_DIR)
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

    def check_for_external_update(self):
        """Checks for external updates.

        This must only be called if we are searching into an external drive.

        We use output_dir/install - if there exist wheels, we install all of
        the wheels.  If there is an rct_config file, we install it.
        output_dir/install will then be deleted, and we restart.
        """
        output_dir = Path(self.__options.get_option(Options.SYS_OUTPUT_DIR))
        if not output_dir.is_dir():
            self.__log.warning('Invalid output dir')
            return

        if not output_dir.is_mount():
            self.__log.warning('Output dir is not a mount, not checking for '
                               'updates')
            return
        install_path = output_dir.joinpath('install')
        if not install_path.exists():
            self.__log.info('install not found, no updates')
            return
        if not install_path.is_dir():
            self.__log.warning('install is not a directory, failing update')
            return
        
        wheels = list(install_path.glob('*.whl'))
        config = list(install_path.glob('rct_config'))

        install_cmd = [sys.executable, '-m', 'pip', 'install', '--force-reinstall']
        install_cmd.extend(wheels)

        subprocess.run(install_cmd, check=True)
        shutil.copy(config, self.__config_path)

        shutil.rmtree(install_path)
        os.execv(sys.argv[0], sys.argv)



def configure_loggers():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    if os.getuid() == 0:
        log_dest = Path('/var/log/rct.log')
    else:
        log_dest = Path('/tmp/rct.log')
    log_file_handler = logging.handlers.RotatingFileHandler(log_dest,
                                                            maxBytes=5*1024*1024,
                                                            backupCount=5)
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

def main():
    configure_loggers()
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', type=Path)
    parser.add_argument('--no_mount', action='store_true')
    parser.add_argument('--service', action='store_true')
    args = parser.parse_args()

    kwargs = {
    }
    if args.config:
        kwargs['config_path'] = args.config
    kwargs['allow_nonmount'] = args.no_mount
    kwargs['service'] = args.service
    try:
        app = RCTRun(**kwargs)
        app.start()
    except Exception as exc:
        logging.exception('Unhandled fatal exception!')
        raise exc
    while True:
        # Wait for the system to end
        pass

if __name__ == "__main__":
    main()
