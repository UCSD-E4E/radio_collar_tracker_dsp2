#ifndef __RTT_PING_SINK_H__
#define __RTT_PING_SINK_H__
#if USE_PYBIND11 == 1
#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl_bind.h>
#endif
#include "ping.hpp"

#include <condition_variable>
#include <mutex>
#include <queue>
#include <thread>
#include <vector>
namespace RCT
{
    class PingSink
    {
#if USE_PYBIND11 == 1
        std::vector<pybind11::object> callbacks;
#endif
        /**
         * Localizes the input pings using data from the gps_module
         * @param queue      Input queue
         * @param mutex      Input queue mutex
         * @param var        Input queue condition variable
         * @param gps_module GPS data source
         */
        void process(std::queue<PingPtr> &queue, std::mutex &mutex, std::condition_variable &var);

        /**
         * Internal state variable
         */
        volatile bool run;

        /**
         * Thread pointer for process
         */
        std::thread *localizer_thread;

        /**
         * handle to condition variable to wake thread
         */
        std::condition_variable *_input_cv;

        int ping_hwm;

    public:
        PingSink(void);
        ~PingSink();
#if USE_PYBIND11 == 1
        void register_callback(pybind11::object &fn);
#endif
        /**
         * Starts the PingLocalizer threads with the specified input queue for
         * pings and GPS module.
         * @param i_q		Input queue of PingPtr objects
         * @param i_m		Input queue mutex
         * @param i_v		Input queue condition variable
         * @param module	GPS Module to retrieve localization information from
         */
        void start(std::queue<PingPtr> &i_q, std::mutex &i_m, std::condition_variable &i_v);

        /**
         * Informs the PingLocalizer module to complete processing of queued
         * pings and exit.
         */
        void stop();
    };
} // namespace RCT
#endif