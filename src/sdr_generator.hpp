#ifndef __SDR_GENERATOR_H__
#define __SDR_GENERATOR_H__

#include "AbstractSDR.hpp"

#include <stdint.h>
#include <thread>

namespace RCT
{
    class SdrGenerator final : public AbstractSDR
    {
    private:
        double gain;
        uint64_t rate;
        uint64_t freq;
        volatile bool run;
        std::thread *thread;
        void _process(std::queue<std::complex<double> *> &o_q,
                      std::mutex &o_m,
                      std::condition_variable &o_v);
        const std::size_t RX_BUFFER_SIZE = 2048;
        const std::size_t BIT_DEPTH = 8;
        double time_ref;
        std::size_t start_ms;
        std::size_t stop_ms;
        std::size_t sample_counter;

    public:
        const double TX_FREQ = 1e3;
        const double BASE_AMPLITUDE = 1e-3;
        const double PING_WIDTH_S = 40e-3;
        const double PING_PERIOD_S = 1.2;
        const double NOISE_AMPLITUDE = 1e-5;
        SdrGenerator(double gain, uint32_t rate, uint32_t freq);
        std::size_t getRxBufferSize(void);
        std::size_t getBitDepth(void);
        void startStreaming(std::queue<std::complex<double> *> &queue,
                            std::mutex &mutex,
                            std::condition_variable &cond_var);
        void stopStreaming(void);
        const std::size_t getStartTime_ms() const;
    };
} // namespace RCT

#endif