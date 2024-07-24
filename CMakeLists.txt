cmake_minimum_required(VERSION 3.16)
project(${SKBUILD_PROJECT_NAME} 
    VERSION ${SKBUILD_PROJECT_VERSION}
    LANGUAGES CXX)

set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(rct_dsp2
    src/sdr_record.cpp
    src/usrp.cpp
    src/iq_data.cpp
    src/dspv3.cpp
    src/sdr_test.cpp
    src/sdr_generator.cpp
    src/ping_sink.cpp
    src/airspy.cpp
    src/hackrf.cpp
    src/utils.cpp
    )

find_package(Boost QUIET REQUIRED COMPONENTS program_options system thread)

target_link_libraries(rct_dsp2
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

target_compile_definitions(rct_dsp2
                           PRIVATE VERSION_INFO=${PROJECT_VERSION}
                           USE_PYBIND11=1)
install(TARGETS rct_dsp2 DESTINATION .)

add_executable(pingFinderTest
    src/sdr_record.cpp
    src/usrp.cpp
    src/iq_data.cpp
    src/dspv3.cpp
    src/sdr_test.cpp
    src/sdr_generator.cpp
    src/ping_sink.cpp
    src/airspy.cpp
    src/test_PingFinder.cpp
    src/hackrf.cpp
    src/utils.cpp
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