'''Network Monitor Watchdog
'''
from __future__ import annotations

import logging
import threading
from enum import Enum, auto
from typing import Callable, Dict, List, Optional

import nmcli


class NetworkMonitor:
    """Class that monitors the current network status

    """
    class Event(Enum):
        """Callback Events
        """
        ON_NETWORK_LOSS = auto()

    class Flag(Enum):
        """Internal flags
        """
        STOP_MONITOR = auto()
        NETWORK_SET = auto()

    EventCallback = Callable[[Event], None]
    CallbackMap = Dict[Event, List[EventCallback]]

    def __init__(self, network_profile: str = 'ubnt', *,
            monitor_interval: int = 1,
            error_threshold: int = 5):
        self.__profile_name = network_profile
        self.__log = logging.getLogger('NetworkMonitor')
        self.__monitor_interval = monitor_interval
        self.__error_threshold = error_threshold

        self.__callbacks: NetworkMonitor.CallbackMap = {
            evt: [] for evt in NetworkMonitor.Event
        }

        self.__flags: Dict[NetworkMonitor.Flag, threading.Event] = {
            flag: threading.Event() for flag in NetworkMonitor.Flag
        }
        if network_profile not in self.__profile_map():
            raise RuntimeError('Network profile not found')

        self.__thread: Optional[threading.Thread] = None

    def __profile_map(self) -> Dict[str, nmcli.data.connection.Connection]:
        return {c.name for c in nmcli.connection()}

    def __current_wifi(self) -> List[str]:
        return [device.ssid for device in nmcli.device.wifi() if device.in_use]

    def register_cb(self, event: Event, cb_: EventCallback) -> None:
        """Registers the specified callback to the specified event

        Args:
            event (Event): Event to register to
            cb_ (Callable): Callback to register
        """
        self.__callbacks[event].append(cb_)
        self.__log.info('Registered %s to %s', cb_, event)

    def execute_cb(self, event: Event) -> None:
        """Executes the specified event callbacks

        Args:
            event (Event): Event to execute
        """
        for cb_ in self.__callbacks[event]:
            cb_(event)

    def remove_cb(self, event: Event, cb_: EventCallback) -> None:
        """Removes the specified callback from the event

        Args:
            event (Event): Event to remove from
            cb_ (Callable): Callback to remove
        """
        self.__callbacks[event].remove(cb_)
        self.__log.info('Removed %s from %s', cb_, event)

    def start(self):
        """Starts the monitoring thread
        """
        if self.__thread is not None:
            return
        self.__flags[self.Flag.STOP_MONITOR].clear()
        self.__thread = threading.Thread(target=self.monitor, name='NetworkMonitor')
        self.__thread.start()

    def stop(self):
        """Stops the monitoring thread
        """
        if self.__thread is None:
            return
        self.__flags[self.Flag.STOP_MONITOR].set()
        self.__thread.join(timeout=self.__monitor_interval * 2)
        self.__thread = None


    def monitor(self):
        """Monitors for network connection and tries to reconnect if lost
        """
        error_counter = 0
        error_status = False
        while not self.__flags[self.Flag.STOP_MONITOR].is_set():
            if self.__profile_name not in self.__current_wifi():
                # not connected
                self.__flags[self.Flag.NETWORK_SET].clear()
                try:
                    nmcli.connection.up(self.__profile_name, wait=self.__monitor_interval)
                except Exception: # pylint: disable=broad-except
                    self.__log.warning('Failing to connect to %s', self.__profile_name)
                    error_counter += 1
                    if error_counter >= self.__error_threshold and not error_status:
                        error_status = True
                        self.__log.warning('Failed to connect to %s', self.__profile_name)
                        self.execute_cb(self.Event.ON_NETWORK_LOSS)
            else:
                error_status = False
                self.__flags[self.Flag.NETWORK_SET].set()
