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
    1.	`git clone git://github.com/EttusResearch/uhd.git`
    2.	`cd uhd/host`
    3.	`git checkout v3.11.0.1`
    4.	`mkdir build`
    5.	`cd build`
    6.	`cmake -DENABLE_B100=OFF -DENABLE_X300=OFF -DENABLE_N230=OFF -DENABLE_USRP1=OFF -DENABLE_USRP2=OFF -DENABLE_OCTOCLOCK=OFF -DENABLE_RFNOC=OFF -DENABLE_MPMD=OFF -DENABLE_EXAMPLES=OFF -DENABLE_MANUAL=OFF -DENABLE_TESTS=OFF ../`
    7.	`make -j8`
    8.	`sudo make install`
    9.	`sudo ldconfig`
    10.	`sudo /usr/local/lib/uhd/utils/uhd_images_downloader.py -t b2xx*`
    11. `cd ../utils`
    12. `sudo cp uhd-usrp.rules /etc/udev/rules.d/`
    13. `sudo udevadm control --reload-rules`
    14. `sudo udevadm trigger`