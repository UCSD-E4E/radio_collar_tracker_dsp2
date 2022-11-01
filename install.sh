#!/bin/bash
sudo apt-get install -y libboost-all-dev python3-pip python3-mako python3-venv libusb-1.0-0-dev cmake build-essential pkg-config libfftw3-dev python3-dev
sudo python3 -m pip install six requests pyserial
git clone https://github.com/EttusResearch/uhd.git
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

cd uhd/host/build
git checkout v4.2.0.1
cmake -DENABLE_B100=OFF -DENABLE_X300=OFF -DENABLE_USRP1=OFF -DENABLE_USRP2=OFF -DENABLE_OCTOCLOCK=OFF -DENABLE_MPMD=OFF -DENABLE_EXAMPLES=OFF -DENABLE_MANUAL=OFF -DENABLE_TESTS=OFF ../
make -j
sudo make install
sudo ldconfig
sudo python3 /usr/local/lib/uhd/utils/uhd_images_downloader.py -t b2xx*
sudo cp ../utils/uhd-usrp.rules /etc/udev/rules.d
sudo udevadm control --reload-rules
sudo udevadm trigger
cd ../../..

cd radio_collar_tracker_dsp2
python3 -m venv .venv
source .venv/bin/activate
cd ../radio_collar_tracker_comms
git checkout communications_HG
python -m pip install .
cd ../radio_collar_tracker_dsp2
git submodule update --init --recursive
python -m pip install .

sudo echo "[Unit]" > /lib/systemd/system/rctrun.service
sudo echo "Description=RCT OBC Runner" >> /lib/systemd/system/rctrun.service
sudo echo "Requires=network-online.target local-fs.target" >> /lib/systemd/system/rctrun.service
sudo echo "" >> /lib/systemd/system/rctrun.service
sudo echo "[Service]" >> /lib/systemd/system/rctrun.service
sudo echo "Type=idle" >> /lib/systemd/system/rctrun.service
rctrun_path=$(which rctrun)
sudo echo "ExecStart=$rctrun_path" >> /lib/systemd/system/rctrun.service
sudo echo "" >> /lib/systemd/system/rctrun.service
sudo echo "[Install]" >> /lib/systemd/system/rctrun.service
sudo echo "WantedBy=multi-user.target" >> /lib/systemd/system/rctrun.service
sudo chmod 644 /lib/systemd/system/rctrun.service
sudo systemctl daemon-reload
sudo systemctl enable rctrun.service

