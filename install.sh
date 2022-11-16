#!/bin/bash
sudo apt-get install -y libboost-all-dev python3-pip python3-mako python3-venv libusb-1.0-0-dev cmake build-essential pkg-config libfftw3-dev python3-dev
sudo python3 -m pip install six requests pyserial
git clone --depth 1 https://github.com/airspy/airspyone_host.git /tmp/airspyone_host
git clone --depth 1 https://github.com/greatscottgadgets/hackrf.git /tmp/hackrf
git clone --depth 1 https://github.com/UCSD-E4E/radio_collar_tracker_comms /tmp/radio_collar_tracker_comms
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

sudo add-apt-repository ppa:ettusresearch/uhd
sudo apt-get update
sudo apt-get install libuhd-dev uhd-host
sudo uhd_images_downloader -t b2xx*

cd $(cwd)
python3 -m venv .venv
source .venv/bin/activate
cd /tmp/radio_collar_tracker_comms
python -m pip install .
cd $(cwd)
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

sudo cp $(cwd)/rct_config_sample /usr/local/etc/rct_config