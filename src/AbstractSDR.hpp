#ifndef __ABSTRACT_SDR__
#define __ABSTRACT_SDR__

#include <queue>
#include <mutex>
#include <condition_variable>
#include <vector>
#include "iq_data.hpp"

namespace RCT{
	/**
	 * SDR interface.  This provides a common interface for all SDR devices as
	 * streaming modules.
	 */
	class AbstractSDR{
	public:
		/**
		 * Receive buffer size. This is the size of data that should be received
		 * at one time from the software defined radio.
		 */
		const static size_t rx_buffer_size = 2048;

		/**
		 * Method to start the streaming threads of this SDR.  This function
		 * shall initiate the streaming action of the software defined radio.
		 * Each frame of data shall be of length rx_buffer_size, and be enqueued
		 * into the specified queue.
		 *
		 * @param queue		std::queue of arrays of std::complex<double>.  This
		 *               	object should be owned by the owner of the 
		 *               	AbstractSDR object.  This AbstractSDR object shall
		 *               	only push elements to this queue; no other object
		 *               	shall push elements to this queue.
		 * @param mutex		std::mutex object for the queue.  This object should
		 *               	be owned by the owner of the AbstractSDR object.
		 * @param cond_var	std::condition_variable for the queue.  This object
		 *                 	should be owned by the owner of the AbstractSDR
		 *                 	object.
		 */
		virtual void startStreaming(std::queue<std::complex<double>*>& queue,
			std::mutex& mutex, std::condition_variable& cond_var) = 0;

		/**
		 * Method to stop the streaming of this SDR.  This method shall not
		 * return until all streaming threads have completed and returned.  When
		 * this method is called, the AbstractSDR shall immediately receive the
		 * last data frame and enqueue it, then exit.
		 */
		virtual void stopStreaming() = 0;

		/**
		 * Destructor.  This destructor shall deinitialize the underlying SDR
		 * hardware and clean up any resources this object owns.  After this
		 * method is called, the underlying SDR hardware shall be in a state
		 * in which any other user program can interact with it.
		 */
		virtual ~AbstractSDR() = default;

		/**
		 * Returns the local timestamp of the first sample streamed in ms since
		 * the Unix epoch.  If AbstractSDR::startStreaming has not yet been 
		 * called, this method has no defined behavior.
		 * @return Timestamp of first sample streamed in ms since Unix epoch.
		 */
		virtual const size_t getStartTime_ms() const = 0;
	};
}
#endif