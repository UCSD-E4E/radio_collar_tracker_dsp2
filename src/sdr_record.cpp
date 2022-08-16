#if USE_PYBIND11 == 1
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>
#include <pybind11/chrono.h>
#endif
#include "sdr_record.hpp"
#include <cstdio>
#include <syslog.h>
#include "sdr.hpp"
#include "sdr_test.hpp"
#include "dspv3.hpp"
#include "product.hpp"

#include <chrono>
#include <thread>
#include <iostream>

#define STRINGIFY(x) #x
#define MACRO_STRINGIFY(x) STRINGIFY(x)

#if USE_PYBIND11 == 1
namespace py = pybind11;
#endif

RCT::PingFinder::PingFinder(): gain(-1), sampling_rate(0), center_frequency(0), 
    run_num(0), output_dir(""), test_data_path(""), ping_width_ms(36), ping_min_snr(4),
    ping_max_len_mult(1.5), ping_min_len_mult(0.75), sdr(nullptr), dsp(nullptr)
{

}

void RCT::PingFinder::start(void)
{
    if(enable_test_data)
    {
        sdr = new RCT::SDR_TEST(test_data_path, run_flag);
    }
    else
    {
        if(sdr_type == SDR_TYPE_USRP)
            sdr = new RCT::USRP(gain, sampling_rate, center_frequency);
        else if(sdr_type == SDR_TYPE_AIRSPY)
            sdr = new RCT::AirSpy(gain, sampling_rate, center_frequency);
        else if(sdr_type == SDR_TYPE_HACKRF)
            sdr = new RCT::HackRF(gain, sampling_rate, center_frequency);
        else
            throw std::runtime_error("Unknown SDR");
    }
    if(nullptr == sdr)
    {
        throw std::runtime_error("Unable to instantiate SDR instance");
    }

    dsp = new RCT::DSP_V3{sampling_rate,
                          center_frequency,
                          target_frequencies,
                          ping_width_ms,
                          ping_min_snr,
                          ping_max_len_mult,
                          ping_min_len_mult,
                          sdr->getRxBufferSize(),
                          sdr->getBitDepth()};
    if(nullptr == dsp)
    {
        delete(sdr);
        throw std::runtime_error("Unable to instantiate DSP instance");
    }
    if(!enable_test_data)
    {
        std::ostringstream buffer;
        buffer << "RAW_DATA_";
        buffer << std::setw(6) << std::setfill('0') << run_num;
        buffer << std::setw(1) << "_";
        buffer << std::setw(4) << "%06d";
        dsp->setOutputDir(output_dir, buffer.str()); 
    }

    sink = new RCT::PingSink();
    if(nullptr == sink)
    {
        delete(dsp);
        delete(sdr);
        throw std::runtime_error("Unable to instantiate Ping Sink instance");
    }
    #if USE_PYBIND11 == 1
    for(auto &fn : callbacks)
    {
        sink->register_callback(fn);
    }
    #endif
    
    dsp->startProcessing(sdr_queue, sdr_queue_mutex, sdr_var, ping_queue, 
        ping_queue_mutex, ping_var);
    sdr->startStreaming(sdr_queue, sdr_queue_mutex, sdr_var);
    sink->start(ping_queue, ping_queue_mutex, ping_var);

    // run_flag = true;
    // test_thread = new std::thread(&RCT::PingFinder::_testThread, this);
}

#if USE_PYBIND11 == 1
void RCT::PingFinder::register_callback(const pybind11::object &fn)
{
    callbacks.push_back(fn);
}
#endif

void RCT::PingFinder::_testThread(void)
{
    std::cout << "running" << std::endl;
    while(run_flag)
    {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

    }
    std::cout << "stopping" << std::endl;
    #if USE_PYBIND11 == 1
    for(auto &it: callbacks)
    {
        std::cout << "Calling " << std::endl;
        (it)(std::chrono::system_clock::now(), (double) 0.00, (std::uint64_t) 1234);
        std::cout << "Finished Calling " << std::endl;
    }
    #endif
}

void RCT::PingFinder::stop(void)
{
    if(nullptr == sdr)
    {
        throw std::runtime_error("SDR not initialized");
    }
    sdr->stopStreaming();
    if(nullptr == dsp)
    {
        throw std::runtime_error("DSP not initialized");
    }
    dsp->stopProcessing();
    if(nullptr == sink)
    {
        throw std::runtime_error("Ping Sink not initialized");
    }
    sink->stop();

    // run_flag = false;
    // test_thread->join();
    // delete(test_thread);
    // test_thread = nullptr;

    delete(sink);
    sink = nullptr;
    delete(dsp);
    dsp = nullptr;
    delete(sdr);
    sdr = nullptr;
    
    #if USE_PYBIND11 == 1
    callbacks.clear();
    #endif
}

std::unique_ptr<RCT::PingFinder> RCT::PingFinder::create(void)
{
    return std::unique_ptr<RCT::PingFinder>(new PingFinder());
}

#if USE_PYBIND11 == 1
PYBIND11_MODULE(radio_collar_tracker_dsp2, m) {
    auto pf = py::class_<RCT::PingFinder>(m, "PingFinder", "Ping Finder class. "
        " This class processes SDR data to detect pings and return them via "
        "callbacks");
    pf.def(py::init(&RCT::PingFinder::create), "Creates a new PingFinder "
        "object.  This only creates the object, it does not initialize the "
        "underlying resources");
    pf.def("start", &RCT::PingFinder::start, "Starts the PingFinder.  This "
        "initializes the underlying SDR and signal processing threads.  All "
        "parameters must be set prior to invocation of this method.");
    pf.def("stop", &RCT::PingFinder::stop, "Stops the PingFinder.  This stops "
        "and releases the underlying SDR and signal processing threads.  It "
        "will also clear the current callback registrations.");
    pf.def("register_callback", &RCT::PingFinder::register_callback);
    pf.def_readwrite("gain", &RCT::PingFinder::gain, "Sets the internal gain "
        "of the SDR");
    pf.def_readwrite("sampling_rate", &RCT::PingFinder::sampling_rate, "Sets "
        "the sampling rate of the SDR");
    pf.def_readwrite("center_frequency", &RCT::PingFinder::center_frequency, 
        "Sets the center frequency of the SDR");
    pf.def_readwrite("run_num", &RCT::PingFinder::run_num, "Set the current "
        "run number");
    pf.def_readwrite("output_dir", &RCT::PingFinder::output_dir, "Sets the "
        "output directory.  This is the directory in which the RAW_DATA* files "
        "will be placed");
    pf.def_readwrite("enable_test_data", &RCT::PingFinder::enable_test_data,
        "Switch to enable or disable test data.  If set to true, uses test "
        "data instead of an SDR.  Test data is pulled from test_data_path");
    pf.def_readwrite("test_data_path", &RCT::PingFinder::test_data_path, 
        "Sets the test data directory.  If enable_test_data is set, "
        "PingFinder will use the RAW_DATA* files in this directory.");
    pf.def_readwrite("ping_min_snr", &RCT::PingFinder::ping_min_snr, "Sets "
        "the minimum ping SNR to be accepted");
    pf.def_readwrite("ping_width_ms", &RCT::PingFinder::ping_width_ms, "Sets "
        "the nominal ping width in milliseconds");
    pf.def_readwrite("ping_max_len_mult", &RCT::PingFinder::ping_max_len_mult,
        "Sets the max multiplier of the ping width");
    pf.def_readwrite("ping_min_len_mult", &RCT::PingFinder::ping_min_len_mult,
        "Sets the min multipler of the ping width");
    pf.def_readwrite("target_frequencies", &RCT::PingFinder::target_frequencies,
        "Sets the target frequencies");
    pf.def_readwrite("sdr_type", &RCT::PingFinder::sdr_type,
        "Sets the target SDR");
    
    m.doc() = R"pbdoc(
        Radio Collar Tracker DSP Module
        -----------------------

        This module provides an interface to the RCT DSP C++ code

    )pbdoc";


#ifdef VERSION_INFO
    m.attr("__version__") = MACRO_STRINGIFY(VERSION_INFO);
#else
    m.attr("__version__") = "dev";
#endif
}
#endif