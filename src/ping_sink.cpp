#include "ping_sink.hpp"

#include "utils.hpp"

#include <chrono>
#include <cstdint>
#include <iostream>
#if USE_PYBIND11 == 1
#include <pybind11/chrono.h>
#endif

void RCT::PingSink::process(std::queue<RCT::PingPtr> &queue,
                            std::mutex &mutex,
                            std::condition_variable &var)
{
    ping_hwm = 0;
    while (run)
    {
        std::unique_lock<std::mutex> inputLock(mutex);
        if (queue.empty())
        {
            var.wait_for(inputLock, std::chrono::milliseconds(100));
        }
        if (!queue.empty())
        {
            RCT::PingPtr pingPtr;
            updated_hwm(queue, ping_hwm);
            pingPtr = queue.front();
#if USE_PYBIND11 == 1
            for (auto &cb : callbacks)
            {
                std::chrono::system_clock::time_point now{
                    std::chrono::milliseconds{pingPtr->time_ms}};
                double amplitude = pingPtr->amplitude;
                std::uint64_t frequency = pingPtr->frequency;
                pybind11::gil_scoped_acquire acquire;
                cb(now, amplitude, frequency);
                pybind11::gil_scoped_release release;
            }
#endif
            queue.pop();
        }
    }
}

void RCT::PingSink::start(std::queue<RCT::PingPtr> &queue,
                          std::mutex &mutex,
                          std::condition_variable &var)
{
    ping_hwm = 0;
    _input_cv = &var;
    run = true;
    localizer_thread = new std::thread(
        &RCT::PingSink::process, this, std::ref(queue), std::ref(mutex), std::ref(var));
}

void RCT::PingSink::stop(void)
{
    run = false;
    _input_cv->notify_all();
    localizer_thread->join();
    delete localizer_thread;

    std::cout << "Ping High Water Mark: " << ping_hwm << std::endl;
}

RCT::PingSink::PingSink(void) : ping_hwm(0)
{
}

RCT::PingSink::~PingSink(void)
{
}

#if USE_PYBIND11 == 1
void RCT::PingSink::register_callback(pybind11::object &fn)
{
    callbacks.push_back(fn);
}
#endif