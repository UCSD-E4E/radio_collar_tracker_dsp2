#include "sdr_generator.hpp"

#include <cmath>
#include <complex>
#include <functional>
#include <iostream>
#include <random>
#include <sys/time.h>
#include <syslog.h>
#include <unistd.h>

using namespace std::complex_literals;

namespace RCT
{
    SdrGenerator::SdrGenerator(double gain, uint32_t rate, uint32_t freq)
        : gain(gain * BASE_AMPLITUDE), rate(rate), freq(freq)
    {
    }
    std::size_t SdrGenerator::getRxBufferSize(void)
    {
        return this->RX_BUFFER_SIZE;
    }
    std::size_t SdrGenerator::getBitDepth(void)
    {
        return this->BIT_DEPTH;
    }
    void SdrGenerator::startStreaming(std::queue<std::complex<double> *> &queue,
                                      std::mutex &mutex,
                                      std::condition_variable &cond_var)
    {
        syslog(LOG_INFO, "SDR Generator starting threads");

        this->run = true;
        this->time_ref = 0;
        this->thread = new std::thread(
            &SdrGenerator::_process, this, std::ref(queue), std::ref(mutex), std::ref(cond_var));
    }

    void SdrGenerator::_process(std::queue<std::complex<double> *> &queue,
                                std::mutex &mutex,
                                std::condition_variable &cond_var)
    {
        std::random_device rd{};
        std::mt19937 gen{rd()};
        std::normal_distribution<double> noise_gen{0, this->NOISE_AMPLITUDE};

        // i = a * cos(2 pi * f * t)
        // q = a * sin(2 pi * f * t)

        struct timeval starttime;
        struct timeval stoptime;
        double time_step = 1.0 / this->rate;
        gettimeofday(&starttime, NULL);
        this->start_ms = starttime.tv_sec * 1e3 + starttime.tv_usec * 1e-3;

        this->sample_counter = 0;

        while (this->run)
        {
            std::complex<double> *buffer = new std::complex<double>[this->RX_BUFFER_SIZE];
            for (std::size_t idx = 0; idx < this->RX_BUFFER_SIZE;
                 idx++, this->time_ref += time_step, this->sample_counter += 1)
            {
                if (fmod(this->time_ref, this->PING_PERIOD_S) < this->PING_WIDTH_S)
                {
                    buffer[idx] =
                        this->gain * cos(M_PI * 2 * this->TX_FREQ * this->time_ref) +
                        1.0i * this->gain * sin(M_PI * 2 * this->TX_FREQ * this->time_ref);
                }
                else
                {
                    buffer[idx] = noise_gen(gen) + 1.0i * noise_gen(gen);
                }
            }

            std::unique_lock<std::mutex> olock(mutex);
            queue.push(buffer);
            olock.unlock();
            cond_var.notify_all();
            gettimeofday(&stoptime, NULL);
            this->stop_ms = stoptime.tv_sec * 1e3 + stoptime.tv_usec * 1e-3;
            int64_t us_sleep = (this->time_ref - (this->stop_ms - this->start_ms) * 1e-3) * 1e6;
            if (us_sleep > 0)
            {
                usleep(us_sleep);
            }
        }
        gettimeofday(&stoptime, NULL);
        this->stop_ms = stoptime.tv_sec * 1e3 + stoptime.tv_usec * 1e-3;

        std::cout << "Generator emitted " << this->sample_counter << " samples, "
                  << (double)this->sample_counter / this->rate << " seconds of data in "
                  << (this->stop_ms - this->start_ms) * 1e-3 << " seconds" << std::endl;
    }

    void SdrGenerator::stopStreaming(void)
    {
        this->run = false;
        this->thread->join();
        delete this->thread;
    }
    const std::size_t SdrGenerator::getStartTime_ms(void) const
    {
        return this->start_ms;
    }
} // namespace RCT