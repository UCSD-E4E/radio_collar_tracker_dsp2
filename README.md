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
4. Configure service
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
    6. `make -j4`
    7. `sudo make install`
    8. `sudo ldconfig`
2. Install `boost`
    1.  `cd ~`
    2.  `wget https://versaweb.d1.sourceforge.net/project/boost/boost_1_65_0.tar.bz2`
    3.  `tar --bzip2 -xf ./boost_1_65_0.tar.bz2`
    4.  `sudo ./bootstrap.ah --prefix=/usr/local`
    5.  `sudo ./b2 install`
2. Install `uhd`
    1.  `cd ~`
    2.  `sudo apt-get install python-pip python-mako libusb-1.0-0-dev cmake build-essential`
    3.  `sudo python -m pip install six requests pyserial`
    4.	`git clone git://github.com/EttusResearch/uhd.git`
    5.	`cd uhd/host`
    6.	`git checkout v3.11.0.1`
    7.	`mkdir build`
    8.	`cd build`
    9.	`cmake -DENABLE_B100=OFF -DENABLE_X300=OFF -DENABLE_N230=OFF -DENABLE_USRP1=OFF -DENABLE_USRP2=OFF -DENABLE_OCTOCLOCK=OFF -DENABLE_RFNOC=OFF -DENABLE_MPMD=OFF -DENABLE_EXAMPLES=OFF -DENABLE_MANUAL=OFF -DENABLE_TESTS=OFF -DBOOST_ROOT=/usr/local -DCMAKE_CXX_FLAGS:STRING="-march=armv7-a -mfloat-abi=hard -mfpu=neon -mtune-cortex-a72 -Wno-psabi" -DCAKE_C_FLAGS:STRING="-march=armv7-a -mfloat-abi=hard -mfpu-neon -mtune=cortex-a72 -g" ../`
    10.  `make -j4`
    11. `sudo make install`
    12.	`sudo ldconfig`
    13.	`sudo /usr/local/lib/uhd/utils/uhd_images_downloader.py -t b2xx*`
    14. `cd ../utils`
    15. `sudo cp uhd-usrp.rules /etc/udev/rules.d/`
    16. `sudo udevadm control --reload-rules`
    17. `sudo udevadm trigger`
3. Install build dependencies
    1.  `cd ~`
    2.  `python3 -m pip install git+https://github.com/UCSD-E4E/radio_collar_tracker_comms`
    3.  `git clone https://github.com/UCSD-E4E/radio_collar_tracker_dsp2.git`
    4.  `cd extern`
    5.  `git clone https://github.com/pybind/pybind11.git`
    6.  `cd pybind11`
    7.  `git checkout acae930123`
    8.  `cd ../..`
    9.  `python3 -m pip install .`
4. Configure service
    1.  `sudo cp rctrun.service /lib/systemd/system/rctrun.service`
    2.  `sudo chmod 644 /lib/systemd/system/rctrun.service`
    3.  `sudo systemctl daemon-reload`
    4.  `sudo systemctl enable rctrun.service`
