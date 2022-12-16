'''Virtual Serial Port Module
'''
import os
import pty
import tty
from contextlib import ExitStack
from pathlib import Path
from selectors import EVENT_READ
from selectors import DefaultSelector as Selector
from threading import Event, Thread
from typing import Optional


class VirtualSerialPorts:
    """Virtual Serial Ports
    """
    def __init__(self, num_ports: int, loopback: bool = False):
        self.fd_pairs = [pty.openpty() for _ in range(num_ports)]
        for master_fd, _ in self.fd_pairs:
            tty.setraw(master_fd)
            os.set_blocking(master_fd, False)
        self.__master_files = {fd[0]: open(fd[0], 'r+b', buffering=0) for fd in self.fd_pairs} # pylint: disable=consider-using-with
        self.slave_names = [Path(os.ttyname(fd[1])) for fd in self.fd_pairs]
        self.__run_thread: Optional[Thread] = None
        self.__run_event = Event()
        self.__loopback = loopback

    def __del__(self):
        for handle in self.__master_files.values():
            handle.close()

    def run(self):
        """Starts the port echoing
        """
        if self.__run_thread is None:
            self.__run_event.set()
            self.__run_thread = Thread(target=self.__port_manager, name='VirtualSerialPort')
            self.__run_thread.start()

    def __port_manager(self):
        with Selector() as selector, ExitStack() as stack:
            for fd_, handle in self.__master_files.items():
                stack.enter_context(handle)
                selector.register(fd_, EVENT_READ)

            while self.__run_event.is_set():
                for key, events in selector.select(timeout=1):
                    if not events & EVENT_READ:
                        continue

                    data = self.__master_files[key.fileobj].read()

                    for fd_, handle in self.__master_files.items():
                        if self.__loopback or fd_ != key.fileobj:
                            handle.write(data)

    def stop(self):
        """Stops the port echoing
        """
        if self.__run_thread is not None:
            self.__run_event.clear()
            self.__run_thread.join()
            self.__run_thread = None

    def __enter__(self):
        self.run()

    def __exit__(self, exc, exp, exv):
        self.stop()
