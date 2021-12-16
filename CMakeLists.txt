cmake_minimum_required(VERSION 3.4...3.18)
project(radio_collar_tracker_dsp2)
add_subdirectory(extern/pybind11)

pybind11_add_module(radio_collar_tracker_dsp2 src/main.cpp)

target_compile_definitions(radio_collar_tracker_dsp2
                           PRIVATE VERSION_INFO=${EXAMPLE_VERSION_INFO})