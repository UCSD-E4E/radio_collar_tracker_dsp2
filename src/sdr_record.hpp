#ifndef __SDR_RECORD_H__
#define __SDR_RECORD_H__

#include "AbstractSDR.hpp"
#include "dsp.hpp"
#include "ping.hpp"

#include <complex>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <mutex>
#include <queue>
#include <thread>
#include <vector>
#if USE_PYBIND11 == 1
#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl_bind.h>
#endif
#include "ping_sink.hpp"
#include "product.hpp"

namespace RCT
{
    class PingFinder
    {
    protected:
        /**
         * SDR data queue.  This connects the RTT::SDR and RTT::DSP_V3 classes.
         */
        std::queue<std::complex<double> *> sdr_queue;

        /**
         * RTT::SDR_RECORD::sdr_queue mutex
         */
        std::mutex sdr_queue_mutex;
        /**
         * sRTT::SDR_RECORD::dr_queue condition variable
         */
        std::condition_variable sdr_var;

        /**
         * Ping queue.  This connects the RTT::DSP_V3 and RTT::PingLocalizer
         * classes.
         */
        std::queue<PingPtr> ping_queue;
        /**
         * RTT::SDR_RECORD::ping_queue mutex
         */
        std::mutex ping_queue_mutex;
        /**
         * RTT::SDR_RECORD::ping_queue condition variable
         */
        std::condition_variable ping_var;

        /**
         * Software Defined Radio handle
         */
        RCT::AbstractSDR *sdr;
        /**
         * Digital Signal Processing stage
         */
        RCT::DSP *dsp;

        RCT::PingSink *sink;

        /**
         * Synchronization and wake variable - this signals the main run loop
         * when to start shutting down the component modules.
         */
        std::condition_variable run_var;
        /**
         * Synchronization and wake mutex for run loop
         */
        std::mutex run_mutex;

        std::thread *test_thread;

        void _testThread(void);
#if USE_PYBIND11 == 1
        std::vector<pybind11::object> callbacks;
#endif

    public:
        double gain;
        std::uint32_t sampling_rate = 2000000;
        std::uint32_t center_frequency = 100000000;
        std::uint32_t run_num = 0;
        bool enable_test_data = false;
        std::string output_dir;
        std::string test_data_path;
        std::uint32_t ping_width_ms;
        double ping_min_snr;
        double ping_max_len_mult;
        double ping_min_len_mult;
        std::vector<size_t> target_frequencies;
        std::uint32_t sdr_type = USE_SDR_TYPE;
        /**
         * Internal state variable
         */
        volatile bool run_flag = false;

        PingFinder();

#if USE_PYBIND11 == 1
        void register_callback(const pybind11::object &fn);
#endif
        void start(void);
        void stop(void);
        void set_dsp_object(RCT::DSP &processor);

        static std::unique_ptr<PingFinder> create(void);
    };
}; // namespace RCT
#endif