#ifndef __SDR_RECORD_H__
#define __SDR_RECORD_H__

#include <cstdint>
#include <complex>
#include <mutex>
#include <queue>
#include <vector>
#include "AbstractSDR.hpp"
#include "dsp.hpp"
#include <condition_variable>
#include "ping.hpp"
#include <thread>
#include <functional>
#include <pybind11/functional.h>
#include "ping_sink.hpp"

namespace RCT{
    class PingFinder
    {
    protected:
		/**
		 * Internal state variable
		 */
        volatile bool run_flag = true;
		/**
		 * SDR data queue.  This connects the RTT::SDR and RTT::DSP_V3 classes.
		 */
        std::queue<std::complex<double>*> sdr_queue;


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
		RCT::AbstractSDR* sdr;
		/**
		 * Digital Signal Processing stage
		 */
		RCT::DSP* dsp;

		RCT::PingSink* sink;


		/**
		 * Synchronization and wake variable - this signals the main run loop
		 * when to start shutting down the component modules.
		 */
		std::condition_variable run_var;
		/**
		 * Synchronization and wake mutex for run loop
		 */
		std::mutex run_mutex;


		void _testThread(void);
		std::vector<pybind11::object> callbacks;

    public:
        double gain;
        std::uint32_t sampling_rate;
        std::uint32_t rx_frequency;
        std::uint32_t run_num;
        bool test_config;
        std::string data_dir;
        std::string test_data;
        std::uint32_t ping_width_ms;
        double ping_min_snr;
        double ping_max_len_mult;
        double ping_min_len_mult;
        std::vector<size_t> target_frequencies;

        PingFinder();

		void register_callback(const pybind11::object &fn);
        void start(void);
        void stop(void);

        static std::unique_ptr<PingFinder> create(void);


    };
};
#endif