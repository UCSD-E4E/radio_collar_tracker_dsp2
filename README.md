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
