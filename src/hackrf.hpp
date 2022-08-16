#ifndef __RCT_HACKRF_H__
#define __RCT_HACKRF_H__

#include "AbstractSDR.hpp"

#include <cstdint>
#include <thread>

#include "libhackrf/hackrf.h"

namespace RCT{
    class HackRF final : public AbstractSDR
    {
        private:
            hackrf_device* device;
            /**
             * @brief Output Queue
             * 
             */
            std::queue<std::complex<double>*>* output_queue;
            
            /**
             * @brief Output queue mutex
             * 
             */
            std::mutex* output_mutex;

            /**
             * @brief Output queue condition variable
             * 
             */
            std::condition_variable* output_var;

            /**
             * @brief Run flag
             * 
             */
            volatile bool _run;

            /**
             * @brief Streamer thread handle
             * 
             */
            std::thread* stream_thread;

            std::size_t _start_ms;

            uint64_t sampling_rate;
        protected:
            HackRF();
            size_t total_rx_samples;
        public:
            /**
             * @brief Construct a new Hack RF object
             * 
             * @param gain 
             * @param rate 
             * @param freq 
             */
            HackRF(double gain, uint64_t rate, uint64_t freq);

            /**
             * @brief Destroy the Hack RF object
             * 
             */
            ~HackRF();

            /**
             * @brief Start the streaming threads for this SDR
             * 
             * This shall initiate the streaming action of the software defined
             * radio.  Each frame of data shall be of length rx_buffere_size, and
             * be enqueued into the specified queue.
             * 
             * @param queue std::queue of arrays of std::complex<double>.  This
             *              object should be owned by the owner of the AbstractSDR
             *              object.  This AbstractSDR object shall only push 
             *              elements to this queue; no other object shall push 
             *              objects to this queue.
             * @param mutex std::mutex object for the queue. THis object should be
             *              owned by the owner of the AbstractSDR object.
             * @param cond_var std::condition_variable for the queue.  This object
             *                 should be owned by the owner of the AbstractSDR 
             *                 object.
             */
            void startStreaming(std::queue<std::complex<double>*>& queue, 
                std::mutex& mutex, std::condition_variable& cond_var);

            /**
             * @brief Stops the streaming of this SDR
             * 
             * This method shall not return until all streaming threads have
             * completed and returned.  When this method is called, the SDR shall
             * immediately receive the last data frame and enqueue it, then exit.
             * 
             */
            void stopStreaming();

            /**
             * @brief Get the local timestamp of the first sample streamed in ms
             * since the Unix epoch.
             * 
             * If AirSpy::startStreaming has not yet been called, this method has no
             * defined behavior.
             * 
             * @return const size_t Timestamp of first sample streamed in ms since
             *                      the Unix epoch.
             */
            const size_t getStartTime_ms() const;

            void rx_callback(hackrf_transfer* pData);

            std::size_t getRxBufferSize(void)
            {
                return 131072;
            }

            std::size_t getBitDepth(void)
            {
                return 8;
            }
    };
}

#endif