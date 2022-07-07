#ifndef __SDR_H__
#define __SDR_H__

#include "iq_data.hpp"
#include "AbstractSDR.hpp"
#include <uhd.h>
#include <string>
#include <queue>
#include <mutex>
#include <thread>
#include <condition_variable>

namespace RCT{
	/**
	 * Concrete SDR class for interfacing with the USRP B200mini for the Radio
	 * Telemetry Tracker.
	 */
	class USRP final : public AbstractSDR{
	private:
		/**
		 * USRP object
		 */
		uhd_usrp_handle usrp;

		/**
		 * Device arguments
		 */
		std::string device_args;

		/**
		 * Subdevice (Daughterboard)
		 */
		std::string subdev;

		/**
		 * Antenna specification
		 */
		std::string ant;

		/**
		 * Clock reference
		 */
		std::string ref;

		/**
		 * UHD data format
		 */
		std::string cpu_format;

		/**
		 * SDR Data transfer format
		 */
		std::string wire_format;

		/**
		 * Input channel selection
		 */
		size_t channel;

		/**
		 * Built-in LNA gain
		 */
		double if_gain;

		/**
		 * SDR Sampling Frequency
		 */
		long int rx_rate;

		/**
		 * SDR Center Frequency
		 */
		long int rx_freq;

		/**
		 * Streaming thread - this thread is responsible for receiving and 
		 * repacking data from UHD.
		 */
		void streamer();

		/**
		 * Pointer to the output queue to put data
		 */
		std::queue<std::complex<double>*>* output_queue;

		/**
		 * Output queue mutex
		 */
		std::mutex* output_mutex;

		/**
		 * Output queue condition variable
		 */
		std::condition_variable* output_var;

		/**
		 * Streamer thread
		 */
		std::thread* stream_thread;

		/**
		 * UHD Stream handle
		 */
		uhd_rx_streamer_handle rx_streamer;

		/**
		 * UHD Error parser
		 * @param  err UHD Error value
		 * @return     String representation of error
		 */
		std::string uhd_strerror(uhd_error err);

		/**
		 * Run flag
		 */
		volatile bool run = false;

		/**
		 * Start time of first sample in ms since Unix Epoch.
		 */
		std::size_t _start_ms;

	protected:
		/**
		 * Default constructor
		 */
		USRP();
	public:
		/**
		 * Constructs this SDR with the specified parameters.
		 * @param gain	LNA Gain in dB
		 * @param rate	Sampling Frequency in Hz
		 * @param freq	Center Frequency in Hz
		 */
		USRP(double gain, long int rate, long int freq);

		/**
		 * Deconstructor - this correctly deinitializes the SDR.
		 */
		~USRP();

		/**
		 * Sets the transfer buffer size.
		 * @param buff_size Transfer buffer size for output queue
		 */
		void setBufferSize(size_t buff_size);

		/**
		 * Gets the current buffer size.
		 * @return Transfer buffer size for output queue.
		 */
		int getBufferSize();

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
		void startStreaming(std::queue<std::complex<double>*>& queue, 
			std::mutex& mutex, std::condition_variable& cond_far);

		/**
		 * Method to stop the streaming of this SDR.  This method shall not
		 * return until all streaming threads have completed and returned.  When
		 * this method is called, the AbstractSDR shall immediately receive the
		 * last data frame and enqueue it, then exit.
		 */
		void stopStreaming();

		/**
		 * Returns the local timestamp of the first sample streamed in ms since
		 * the Unix epoch.  If AbstractSDR::startStreaming has not yet been 
		 * called, this method has no defined behavior.
		 * @return Timestamp of first sample streamed in ms since Unix epoch.
		 */
		const size_t getStartTime_ms() const;
	};
}

#endif