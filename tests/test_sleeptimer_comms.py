from stcomms.stcomms import SETALARMCommand 
import serial
import threading
import datetime


def activateSleepTimer(timeOff):
    timerSerial = 'serial'
    timerBaud = 'baud'
    packet = SETALARMCommand(timeOff)
    with serial.Serial(port=timerSerial, baudrate=timerBaud) as ser:
        ser.write(packet.to_bytes)
   
def main():
    secsToSleep = 0
    msecsOff = 0
        
    threading.Timer(secsToSleep, activateSleepTimer(msecsOff))
             

if __name__ == "__main__":
    main()