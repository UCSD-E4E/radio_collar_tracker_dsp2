# Setup
This requires Ubuntu 24.04 or later.

```
sudo add-apt-repository ppa:ettusresearch/uhd
sudo apt-get update
sudo apt-get install -y fftw-dev libboost-all-dev libuhd-dev uhd-host libairspy-dev libhackrf-dev python3 python3-dev python3-pip python3-venv cmake build-essential
python -m pip install .
```

# Usage:
See examples in the examples folder