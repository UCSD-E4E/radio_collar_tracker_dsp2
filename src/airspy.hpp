#ifndef __RCT_AIRSPY_H__
#define __RCT_AIRSPY_H__

#include "AbstractSDR.hpp"

#include <cstdint>

#include <libairspy/airspy.h>

namespace RCT{
    class AirSpy final : public AbstractSDR{
    private:
        struct airspy_device* device;
    protected:
        /**
         * @brief Construct a new Air Spy object
         * 
         * Default constructor
         */
        AirSpy();
    public:
        /**
         * @brief Construct a new Air Spy object with the specified parameters
         * 
         * @param gain 
         * @param rate 
         * @param freq 
         */
        AirSpy(double gain, uint64_t rate, uint64_t freq);

        /**
         * @brief Destroy the Air Spy object
         * 
         */
        ~AirSpy();

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
    };
}
#endif