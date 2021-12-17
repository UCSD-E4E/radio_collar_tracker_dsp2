#ifndef __RTT_DSP_H__
#define __RTT_DSP_H__

#include <queue>
#include "iq_data.hpp"
#include <mutex>
#include <condition_variable>
#include "ping.hpp"

namespace RCT{


	/**
	 * DSP Interface class.  This class is responsible for identifying and
	 * measuring the pings present in the input signal.
	 */
	class DSP{
	public:

		virtual ~DSP(){
			
		}

		/**
		 * This must be a non-blocking function that starts a thread which 
		 * processes the incoming data and detects the pings in that data, and 
		 * sends it along out the outputQueue queue.
		 * 
		 * @param	inputQueue	a std::queue<RTT::IQdata> reference for incoming 
		 *                   	data
		 * @param	inputMutex	a std::mutex for the input queue
		 * @param	inputVar	a std::condition_variable for the input queue
		 * @param	outputQueue	a std::queue<RTT::Ping*> for detected pings
		 * @param	outputMutex	a std::mutex for the output queue
		 * @param	outputVar	a std::condition_variable for the output queue
		 * @param	ndie		a pointer to a bool that is true when the 
		 * 						program should be running, and false when the 
		 * 						program should be shutting down
		 */
		virtual void startProcessing(
			std::queue<std::complex<double>*>& inputQueue, 
			std::mutex& inputMutex, std::condition_variable& inputVar,
			std::queue<PingPtr>& outputQueue, std::mutex& outputMutex, 
			std::condition_variable& outputVar) = 0;

		/**
		 * Method to stop the processing of this DSP.  This method shall not
		 * return until all processing threads have completed and returned.  When
		 * this method is called, the DSP shall continue to process all enqueued
		 * data frames until the input queue is empty, then return.
		 */
		virtual void stopProcessing() = 0;

		/**
		 * Sets the start time of input signal.  This must be called before
		 * the first ping is detected.
		 * @param t	Local timestamp of initial sample in ms since Unix epoch
		 */
		virtual void setStartTime(std::size_t t) = 0;

		/**
		 * Sets the output directory and filename format.
		 * @param dir Directory path
		 * @param fmt Format string - this must contain two integer fields,
		 *            first being run number, second being file number.
		 */
		virtual void setOutputDir(const std::string& dir, const std::string& fmt) = 0;
	};
}

#endif