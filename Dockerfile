FROM ubuntu:24.04
WORKDIR /root/radio_collar_tracker_dsp2
COPY . /root/radio_collar_tracker_dsp2
RUN apt-get update && apt-get install -y software-properties-common
RUN add-apt-repository ppa:ettusresearch/uhd && apt-get update && apt-get install -y libuhd-dev uhd-host fftw-dev libboost-all-dev libairspy-dev libhackrf-dev python3 python3-dev python3-pip python3-venv cmake build-essential
RUN python3 -m venv .venv
RUN .venv/bin/python -m pip install .
RUN find / -name "uhd_images_downloader"
RUN /usr/bin/uhd_images_downloader
ENTRYPOINT [ "/bin/bash" ]