# Setup
This requires Ubuntu 20.04 or later.

```
sudo apt-get update
sudo apt-get install -y fftw-dev libboost-all-dev libuhd-dev uhd-host libairspy-dev libhackrf-dev python3 python3-dev python3-pip python3-venv cmake build-essential
python3 -m pip install git+https://github.com/UCSD-E4E/radio_collar_tracker_comms
git submodule update --init --recursive`
python3 -m pip install .
sudo cp rctrun.service /lib/systemd/system/rctrun.service
sudo chmod 644 /lib/systemd/system/rctrun.service
sudo systemctl daemon-reload
sudo systemctl enable rctrun.service
```

# Developer Notes
## Threading
All threads should use `autostart.utils.InstrumentedThread`, which is a wrapper
of `threading.Thread`.  This wrapper provides support for capturing exceptions
raised from the thread into the log, which is critical for headless systems.
