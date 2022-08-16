# Setup
1. Get `fftw3`
    1. `wget http://www.fftw.org/fftw-3.3.8.tar.gz`
    2. `tar -xzf fftw-3.3.8.tar.gz`
    3. `cd fftw-3.3.8`
    4. `./bootstrap.sh`
    5. `./configure --enable-threads --enable-generic-simd128 --enable-generic-simd256 --enable-shared`
    6. `make -j`
    7. `sudo make install`
    8. `sudo ldconfig`
2. Install `libboost`
    1.  Try `sudo apt-get install libboost-all-dev`
    2.  You must install libboost 1.65. If unable, follow the instructions below
    3.  `wget https://boostorg.jfrog.io/artifactory/main/release/1.78.0/source/boost_1_78_0.tar.bz2`
    4.  `tar --bzip2 -xf ./boost_1_78_0.tar.bz2`
    4.  `./bootstrap.sh --prefix=/usr/local`
    5.  `sudo ./b2 install -j`
3. Install `uhd`
    1.  `sudo apt-get install python3-pip python3-mako libusb-1.0-0-dev cmake build-essential`
    2.  `sudo python3 -m pip install six requests pyserial`
    3.	`git clone https://github.com/EttusResearch/uhd.git`
    4.	`cd uhd/host`
    5.	`git checkout v4.2.0.1`
    6.	`mkdir build`
    7.	`cd build`
    8.	`cmake -DENABLE_B100=OFF -DENABLE_X300=OFF -DENABLE_USRP1=OFF -DENABLE_USRP2=OFF -DENABLE_OCTOCLOCK=OFF -DENABLE_MPMD=OFF -DENABLE_EXAMPLES=OFF -DENABLE_MANUAL=OFF -DENABLE_TESTS=OFF ../`
    9.	`make -j`
    10.	`sudo make install`
    11.	`sudo ldconfig`
    12.	`sudo python3 /usr/local/lib/uhd/utils/uhd_images_downloader.py -t b2xx*`
    13. `cd ../utils`
    14. `sudo cp uhd-usrp.rules /etc/udev/rules.d/`
    15. `sudo udevadm control --reload-rules`
    16. `sudo udevadm trigger`
4. Install `libairspy`
    1.  `sudo apt-get install build-essential cmake libusb-1.0-0-dev pkg-config`
    2.  `git clone https://github.com/airspy/airspyone_host.git`
    3.  `mkdir airspyone_host/build`
    4.  `cd airspyone_host/build`
    5.  `cmake ../ -DINSTALL_UDEV_RULES=ON`
    6.  `make -j`
    7.  `sudo make install`
    8.  `sudo ldconfig`
5.  Install `libhackrf`
    1.  `sudo apt-get install build-essential cmake libusb-1.0-0-dev pkg-config libfftw3-dev`
    2.  `git clone https://github.com/greatscottgadgets/hackrf.git`
    3.  `mkdir hackrf/host/build`
    4.  `cd hackrf/host/build`
    5.  `cmake ../`
    6.  `make -j`
    7.  `sudo make install`
    8.  `sudo ldconfig`
4. Install build dependencies
    1. `sudo apt-get install python3 python3-dev cmake build-essential`
    2. `python3 -m pip install git+https://github.com/UCSD-E4E/radio_collar_tracker_comms`
    3. `git submodule update --init --recursive`
    3. `python3 -m pip install .`
5. Configure service
    1. `sudo cp rctrun.service /lib/systemd/system/rctrun.service`
    2. `sudo chmod 644 /lib/systemd/system/rctrun.service`
    3. `sudo systemctl daemon-reload`
    4. `sudo systemctl enable rctrun.service`

---
# Setup for Rasberry-Pi4
Requirements:
    1. `python 3.9`
1. Get `fftw3`
    1. `wget http://www.fftw.org/fftw-3.3.8.tar.gz`
    2. `tar -xzf fftw-3.3.8.tar.gz`
    3. `cd fftw-3.3.8`
    4. `./bootstrap.sh`
    5. `./configure --enable-threads --enable-generic-simd128 --enable-generic-simd256 --enable-shared`
    6. `make -j`
    7. `sudo make install`
    8. `sudo ldconfig`
2. Install `libboost`
    1.  Try `sudo apt-get install libboost-all-dev`
    2.  You must install libboost 1.65. If unable, follow the instructions below
    3.  `wget https://boostorg.jfrog.io/artifactory/main/release/1.78.0/source/boost_1_78_0.tar.bz2`
    4.  `tar --bzip2 -xf ./boost_1_78_0.tar.bz2`
    4.  `./bootstrap.sh --prefix=/usr/local`
    5.  `sudo ./b2 install -j`
2. Install `uhd`
    1.  `cd ~`
    2.  `sudo apt-get install python-pip python-mako libusb-1.0-0-dev cmake build-essential`
    3.  `sudo python -m pip install six requests pyserial`
    4.	`git clone git://github.com/EttusResearch/uhd.git`
    5.	`cd uhd/host`
    6.	`git checkout v4.2.0.1`
    7.	`mkdir build`
    8.	`cd build`
    9.	`cmake -DENABLE_B100=OFF -DENABLE_X300=OFF -DENABLE_USRP1=OFF -DENABLE_USRP2=OFF -DENABLE_OCTOCLOCK=OFF -DENABLE_MPMD=OFF -DENABLE_EXAMPLES=OFF -DENABLE_MANUAL=OFF -DENABLE_TESTS=OFF -DNEON_SIMD_ENABLE=OFF ../`
    10.  `make -j`
    11. `sudo make install`
    12.	`sudo ldconfig`
    13.	`sudo /usr/local/lib/uhd/utils/uhd_images_downloader.py -t b2xx*`
    14. `cd ../utils`
    15. `sudo cp uhd-usrp.rules /etc/udev/rules.d/`
    16. `sudo udevadm control --reload-rules`
    17. `sudo udevadm trigger`
4. Install `libairspy`
    1.  `sudo apt-get install build-essential cmake libusb-1.0-0-dev pkg-config`
    2.  `git clone https://github.com/airspy/airspyone_host.git`
    3.  `mkdir airspyone_host/build`
    4.  `cd airspyone_host/build`
    5.  `cmake ../ -DINSTALL_UDEV_RULES=ON`
    6.  `make -j`
    7.  `sudo make install`
    8.  `sudo ldconfig`
5.  Install `libhackrf`
    1.  `sudo apt-get install build-essential cmake libusb-1.0-0-dev pkg-config libfftw3-dev`
    2.  `git clone https://github.com/greatscottgadgets/hackrf.git`
    3.  `mkdir hackrf/host/build`
    4.  `cd hackrf/host/build`
    5.  `cmake ../`
    6.  `make -j`
    7.  `sudo make install`
    8.  `sudo ldconfig`
4. Install build dependencies
    1. `sudo apt-get install python3 python3-dev cmake build-essential`
    2. `python3 -m pip install git+https://github.com/UCSD-E4E/radio_collar_tracker_comms`
    3. `git submodule update --init --recursive`
    3. `python3 -m pip install .`
4. Configure service
    1.  `sudo cp rctrun.service /lib/systemd/system/rctrun.service`
    2.  `sudo chmod 644 /lib/systemd/system/rctrun.service`
    3.  `sudo systemctl daemon-reload`
    4.  `sudo systemctl enable rctrun.service`
