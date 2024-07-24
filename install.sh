#!/bin/bash
sudo add-apt-repository -y ppa:ettusresearch/uhd
sudo apt-get update
sudo apt-get install -y libboost-all-dev python3-pip python3-mako python3-venv libusb-1.0-0-dev cmake build-essential pkg-config libfftw3-dev python3-dev libuhd-dev uhd-host
sudo python3 -m pip install -U six requests pyserial wheel
if [ -d "/tmp/airspyone_host" ]
then
    rm -rf /tmp/airspyone_host
fi
if [ -d "/tmp/hackrf" ]
then
    rm -rf /tmp/hackrf
fi

git clone --depth 1 https://github.com/airspy/airspyone_host.git /tmp/airspyone_host
git clone --depth 1 https://github.com/greatscottgadgets/hackrf.git /tmp/hackrf
cwd=$(pwd)

mkdir /tmp/airspyone_host/build
mkdir /tmp/hackrf/host/build

cd /tmp/hackrf/host/build
cmake ../
make -j
sudo make install
sudo ldconfig

cd /tmp/airspyone_host/build
cmake ../ -DINSTALL_UDEV_RULES=ON
make -j
sudo make install
sudo ldconfig

sudo uhd_images_downloader -t b2xx*

cd "${cwd}"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U wheel
python -m pip install -U .
cd "${cwd}"
git submodule update --init --recursive
python -m pip install -U .
