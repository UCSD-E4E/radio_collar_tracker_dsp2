FROM ubuntu:24.04
WORKDIR /root/radio_collar_tracker_dsp2
COPY . /root/radio_collar_tracker_dsp2
RUN add-apt-repository ppa:ettusresearch/uhd && apt update && apt install -y fftw-dev libboost-all-dev libuhd-dev uhd-host libairspy-dev libhackrf-dev python3 python3-dev python3-pip python3-venv cmake build-essential
RUN python3 -m venv .venv
RUN .venv/bin/python -m pip install .
