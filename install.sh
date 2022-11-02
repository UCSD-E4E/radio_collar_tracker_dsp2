#!/bin/bash
sudo add-apt-repository ppa:ettusresearch/uhd
sudo apt-get update
sudo apt-get install -y libboost-all-dev python3-pip python3-mako python3-venv libusb-1.0-0-dev cmake build-essential pkg-config libfftw3-dev python3-dev libuhd-dev uhd-host
sudo python3 -m pip install six requests pyserial

git clone https://github.com/airspy/airspyone_host.git
git clone https://github.com/greatscottgadgets/hackrf.git
git clone https://github.com/UCSD-E4E/radio_collar_tracker_comms
git clone https://github.com/UCSD-E4E/radio_collar_tracker_dsp2

mkdir uhd/host/build
mkdir airspyone_host/build
mkdir hackrf/host/build

cd hackrf/host/build
cmake ../
make -j
sudo make install
sudo ldconfig
cd ../../..

cd airspyone_host/build
cmake ../ -DINSTALL_UDEV_RULES=ON
make -j
sudo make install
sudo ldconfig
cd ../..

cd radio_collar_tracker_dsp2
python3 -m venv .venv
source .venv/bin/activate
cd ../radio_collar_tracker_comms
git checkout communications_HG
python -m pip install .
cd ../radio_collar_tracker_dsp2
git submodule update --init --recursive
python -m pip install .

echo "[Unit]" > /tmp/rctrun.service
echo "Description=RCT OBC Runner" >> /tmp/rctrun.service
echo "Requires=network-online.target local-fs.target" >> /tmp/rctrun.service
echo "" >> /tmp/rctrun.service
echo "[Service]" >> /tmp/rctrun.service
echo "Type=idle" >> /tmp/rctrun.service
rctrun_path=$(which rctrun)
echo "ExecStart=$rctrun_path" >> /tmp/rctrun.service
echo "" >> /tmp/rctrun.service
echo "[Install]" >> /tmp/rctrun.service
echo "WantedBy=multi-user.target" >> /tmp/rctrun.service
sudo cp /tmp/rctrun.service /lib/systemd/system/rctrun.service
sudo chmod 644 /lib/systemd/system/rctrun.service
sudo systemctl daemon-reload
sudo systemctl enable rctrun.service

