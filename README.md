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
    1.  `sudo apt-get install libboost-all-dev`
    2.	`git clone git://github.com/EttusResearch/uhd.git`
    3.	`cd uhd/host`
    4.	`git checkout v3.11.0.1`
    5.	`mkdir build`
    6.	`cd build`
    7.	`cmake -DENABLE_B100=OFF -DENABLE_X300=OFF -DENABLE_N230=OFF -DENABLE_USRP1=OFF -DENABLE_USRP2=OFF -DENABLE_OCTOCLOCK=OFF -DENABLE_RFNOC=OFF -DENABLE_MPMD=OFF -DENABLE_EXAMPLES=OFF -DENABLE_MANUAL=OFF -DENABLE_TESTS=OFF ../`
    8.	`make -j8`
    9.	`sudo make install`
    10.	`sudo ldconfig`
    11.	`sudo /usr/local/lib/uhd/utils/uhd_images_downloader.py -t b2xx*`
    12. `cd ../utils`
    13. `sudo cp uhd-usrp.rules /etc/udev/rules.d/`
    14. `sudo udevadm control --reload-rules`
    15. `sudo udevadm trigger`
