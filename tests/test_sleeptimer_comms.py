from RCTComms.stcomms import SETALARMCommand 
import serial
import time
import threading


def activateSleepTimer():
    timeOff = 1 * 60 * 60 * 1000 #time asleep in msec (1 hr)
    timerSerial = 'serial'
    timerBaud = 'baud'
    packet = SETALARMCommand(timeOff)
    with serial.Serial(port=timerSerial, baudrate=timerBaud) as ser:
        ser.write(packet.to_bytes)     
   
def main():
    iter = 0
    for i in range(iter):
        # waiting for sleeptimer to turn ON system
        while GPIO.input(7) != 1:
            time.sleep(0.5)
        # wait some time to avoid alarm overlap
        time.sleep(10)
        # log date and time
        push = (time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])        #print time with date and time up to milliseconds
        with open("/home/pi/data_log.txt", "a") as file:
            file.write(push + "ON\n")
        #activate alarm 
        activateSleepTimer()
        push = (time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])        #print time with date and time up to milliseconds
        with open("/home/pi/data_log.txt", "a") as file:
            file.write(push + "ON\n")
        # waiting for sleeptimer to turn OFF system
        while GPIO.input(7) != 0:
            time.sleep(0.5)
        # log date and time
        push = (time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])     #print time with date and time up to milliseconds
        with open("/home/pi/data_log.txt", "a") as file:
            file.write(push + "OFF\n")
    

if __name__ == "__main__":
    main()