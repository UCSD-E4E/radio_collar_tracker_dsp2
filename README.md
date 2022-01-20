# Setup
1. Get `fftw3`
    1. `wget http://www.fftw.org/fftw-3.3.8.tar.gz`
    2. `tar -xzf fftw-3.3.8.tar.gz`
    3. `cd fftw-3.3.8`
    4. `./bootstrap.sh`
    5. `./configure --enable-threads --enable-generic-simd128 --enable-generic-simd256 --enable-shared`
    6. `make -j10`
    7. `sudo make install`
    8. `sudo ldconfig`
2. Install `uhd`
    1.  `sudo apt-get install libboost-all-dev python-pip python-mako libusb-1.0-0-dev cmake build-essential`
    2.  `sudo python -m pip install six requests enum pyserial`
    3.	`git clone git://github.com/EttusResearch/uhd.git`
    4.	`cd uhd/host`
    5.	`git checkout v3.11.0.1`
    6.	`mkdir build`
    7.	`cd build`
    8.	`cmake -DENABLE_B100=OFF -DENABLE_X300=OFF -DENABLE_N230=OFF -DENABLE_USRP1=OFF -DENABLE_USRP2=OFF -DENABLE_OCTOCLOCK=OFF -DENABLE_RFNOC=OFF -DENABLE_MPMD=OFF -DENABLE_EXAMPLES=OFF -DENABLE_MANUAL=OFF -DENABLE_TESTS=OFF ../`
    9.	`make -j8`
    10.	`sudo make install`
    11.	`sudo ldconfig`
    12.	`sudo /usr/local/lib/uhd/utils/uhd_images_downloader.py -t b2xx*`
    13. `cd ../utils`
    14. `sudo cp uhd-usrp.rules /etc/udev/rules.d/`
    15. `sudo udevadm control --reload-rules`
    16. `sudo udevadm trigger`
3. Install build dependencies
    1. `sudo apt-get install python3.7 python3.7-dev cmake build-essential`
    2. `python3.7 -m pip install git+https://github.com/UCSD-E4E/radio_collar_tracker_comms`
    3. `python3.7 -m pip install .`
