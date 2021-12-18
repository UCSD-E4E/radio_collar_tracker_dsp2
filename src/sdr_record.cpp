#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>
#include <pybind11/chrono.h>
#include "sdr_record.hpp"
#include <cstdio>
#include <syslog.h>
#include "sdr.hpp"
#include "sdr_test.hpp"
#include "dspv3.hpp"

#include <chrono>
#include <thread>

#define STRINGIFY(x) #x
#define MACRO_STRINGIFY(x) STRINGIFY(x)

namespace py = pybind11;

RCT::PingFinder::PingFinder(): gain(-1), sampling_rate(0), rx_frequency(0), 
    run_num(0), data_dir(""), test_data(""), ping_width_ms(36), ping_min_snr(4),
    ping_max_len_mult(1.5), ping_min_len_mult(0.75), sdr(nullptr), dsp(nullptr)
{

}

void RCT::PingFinder::start(void)
{
    if(test_config)
    {
        sdr = new RCT::SDR_TEST(test_data, run_flag);
    }
    else
    {
        sdr = new RCT::SDR(gain, sampling_rate, rx_frequency);
    }
    if(nullptr == sdr)
    {
        throw std::runtime_error("Unable to instantiate SDR instance");
    }

    dsp = new RCT::DSP_V3{sampling_rate,
                          rx_frequency,
                          target_frequencies,
                          ping_width_ms,
                          ping_min_snr,
                          ping_max_len_mult,
                          ping_min_len_mult};
    if(nullptr == dsp)
    {
        delete(sdr);
        throw std::runtime_error("Unable to instantiate DSP instance");
    }
    if(!test_config)
    {
        std::ostringstream buffer;
        buffer << "RAW_DATA_";
        buffer << std::setw(6) << std::setfill('0') << run_num;
        buffer << std::setw(1) << "_";
        buffer << std::setw(4) << "%06d";
        dsp->setOutputDir(data_dir, buffer.str()); 
    }

    sink = new RCT::PingSink();
    if(nullptr == sink)
    {
        delete(dsp);
        delete(sdr);
        throw std::runtime_error("Unable to instantiate Ping Sink instance");
    }
    for(auto &fn : callbacks)
    {
        sink->register_callback(fn);
    }
    
    dsp->startProcessing(sdr_queue, sdr_queue_mutex, sdr_var, ping_queue, 
        ping_queue_mutex, ping_var);
    sdr->startStreaming(sdr_queue, sdr_queue_mutex, sdr_var);
    sink->start(ping_queue, ping_queue_mutex, ping_var);
}

void RCT::PingFinder::register_callback(const pybind11::object &fn)
{
    callbacks.push_back(fn);
}

void RCT::PingFinder::_testThread(void)
{
    std::cout << "running" << std::endl;
    while(run_flag)
    {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

    }
    std::cout << "stopping" << std::endl;
    for(auto &it: callbacks)
    {
        std::cout << "Calling " << std::endl;
        it(std::chrono::system_clock::now(), (double) 0.00, (std::uint64_t) 1234);
        std::cout << "Finished Calling " << std::endl;
    }
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

    delete(sink);
    sink = nullptr;
    delete(dsp);
    dsp = nullptr;
    delete(sdr);
    sdr = nullptr;
    
    callbacks.clear();
}

std::unique_ptr<RCT::PingFinder> RCT::PingFinder::create(void)
{
    return std::unique_ptr<RCT::PingFinder>(new PingFinder());
}
PYBIND11_MODULE(radio_collar_tracker_dsp2, m) {
    py::class_<RCT::PingFinder>(m, "PingFinder")
        .def(py::init(&RCT::PingFinder::create))
        .def("start", &RCT::PingFinder::start)
        .def("stop", &RCT::PingFinder::stop)
        .def("register_callback", &RCT::PingFinder::register_callback)
        .def_readwrite("gain", &RCT::PingFinder::gain)
        .def_readwrite("sampling_rate", &RCT::PingFinder::sampling_rate)
        .def_readwrite("rx_frequency", &RCT::PingFinder::rx_frequency)
        .def_readwrite("run_num", &RCT::PingFinder::run_num)
        .def_readwrite("test_config", &RCT::PingFinder::test_config)
        .def_readwrite("data_dir", &RCT::PingFinder::data_dir)
        .def_readwrite("test_data", &RCT::PingFinder::test_data)
        .def_readwrite("ping_width_ms", &RCT::PingFinder::ping_width_ms)
        .def_readwrite("ping_min_snr", &RCT::PingFinder::ping_min_snr)
        .def_readwrite("ping_max_len_mult", &RCT::PingFinder::ping_max_len_mult)
        .def_readwrite("ping_min_len_mult", &RCT::PingFinder::ping_min_len_mult)
        .def_readwrite("target_frequencies", &RCT::PingFinder::target_frequencies)
    ;
    m.doc() = R"pbdoc(
        Pybind11 example plugin
        -----------------------

        .. currentmodule:: cmake_example

        .. autosummary::
           :toctree: _generate

    )pbdoc";

#ifdef VERSION_INFO
    m.attr("__version__") = MACRO_STRINGIFY(VERSION_INFO);
#else
    m.attr("__version__") = "dev";
#endif
}