cmake_minimum_required(VERSION 3.4...3.18)
project(radio_collar_tracker_dsp2)
add_subdirectory(extern/pybind11)

pybind11_add_module(radio_collar_tracker_dsp2
    src/sdr_record.cpp
    src/usrp.cpp
    src/iq_data.cpp
    src/dspv3.cpp
    src/sdr_test.cpp
    src/ping_sink.cpp
    src/airspy.cpp
    src/hackrf.cpp
    )

find_package(Boost QUIET REQUIRED COMPONENTS program_options system thread)


target_link_libraries(radio_collar_tracker_dsp2
    PUBLIC
        uhd
        fftw3
        fftw3_threads
        m
        Boost::system
        Boost::thread
        pthread
        airspy
        hackrf
    )

target_compile_definitions(radio_collar_tracker_dsp2
                           PRIVATE VERSION_INFO=${EXAMPLE_VERSION_INFO}
                           USE_PYBIND11=1)

add_executable(pingFinderTest
    src/sdr_record.cpp
    src/usrp.cpp
    src/iq_data.cpp
    src/dspv3.cpp
    src/sdr_test.cpp
    src/ping_sink.cpp
    src/airspy.cpp
    src/test_PingFinder.cpp
    src/hackrf.cpp
)

target_link_libraries(pingFinderTest
    PUBLIC
        uhd
        fftw3
        fftw3_threads
        m
        Boost::system
        Boost::thread
        pthread
        airspy
        hackrf
    )

target_compile_definitions(pingFinderTest
                           PRIVATE VERSION_INFO=${EXAMPLE_VERSION_INFO}
                           USE_PYBIND11=0)