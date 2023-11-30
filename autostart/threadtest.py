import datetime
import json
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple



class I2CUIBoard:
    def __init__(self):
        '''
        Store current status
        store most recent GPS and Compass info
        Store most recent ping?
        '''
        self.port = None
        self.gps = None
        self.compass = None
        self.compass_int = 0
        self.ready = threading.Event()
        self.compass_data = None
        self.gps_data = None
    def __init_gps(self):
        if self.gps == None:
            self.gps = "GPS"

    def __init_compass(self):
        # TODO: New Function 
        if self.compass == None:
            self.compass = "COMPASS"


    def read_compass(self):
        header = f"header_{self.compass_int}"
        time.sleep(2)
        self.ready.wait()
        self.compass_data = header

    def read_gps(self):
        header = f"gps_{self.compass_int}"
        time.sleep(5)
        self.compass_int += 1
        self.ready.set()
        self.gps_data = header


    def uib_listener(self):
        '''
        Continuously listens to uib serial port for Sensor Packets
        '''
        self.__init_gps()
        self.__init_compass()
        while True:
            self.ready.clear()
            gps_thread = threading.Thread(target=self.read_gps)
            compass_thread = threading.Thread(target=self.read_compass)

            gps_thread.start()
            compass_thread.start()

            gps_thread.join()
            compass_thread.join()
            print(self.compass_data, self.gps_data)
            
i2c = I2CUIBoard()
i2c.uib_listener()