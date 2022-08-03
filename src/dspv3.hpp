#ifndef __DSPV3_H__
#define __DSPV3_H__
#include "dsp.hpp"
#include <complex>
#include <condition_variable>
#include <thread>
#include <fftw3.h>
#include <memory>
#include <set>
#include "AbstractSDR.hpp"
#include <boost/circular_buffer.hpp>

namespace RCT{
	/**
	 * DSP v3.0.  This uses a FFT to isolate the desired frequencies, then 
	 * dynamic thresholding to remove noise, then width analysis to determine
	 * ping candidacy.  Dynamic thresholding is accomplished by taking the
	 * median of the most recent set of maximums of multiple windows.
	 */
	class DSP_V3 final : public DSP{

	public:
		/**
		 * Constructor for this DSP class.  Specify the sampling frequency in
		 * samples per second, center frequency in Hz, target frequencies in Hz,
		 * ping width in ms, minimum SNR in dB, and max/min ping width 
		 * multipliers.
		 *
		 * Any detected ping will be in one of the target frequencies, with an
		 * amplitude of at least noise floor + snr, and a width no less than
		 * min_len_threshold * width_ms and no greater than max_len_threshold *
		 * width_ms.
		 * 
		 * @param sampling_freq		Input sampling frequency in samples per 
		 *                       	second
		 * @param center_freq		Input center frequency in Hz
		 * @param target_freqs		std::vector of target frequencies in Hz as
		 *                      	std::size_t
		 * @param width_ms			Nominal ping width in ms.
		 * @param snr				Minimum amount in dB above threshold that 
		 *               			ping must be
		 * @param max_len_threshold	Maximum multiplier for acceptable ping 
		 *                          widths.
		 * @param min_len_threshold	Minimum multipler for acceptable ping
		 *                          widths.
		 */
		DSP_V3(const std::size_t sampling_freq, const std::size_t center_freq,
			const std::vector<std::size_t>& target_freqs,
			const std::size_t width_ms,
			const double snr,
			const double max_len_threshold,
			const double min_len_threshold,
			const std::size_t input_block_size,
			const std::size_t bit_depth);

		/**
		 * Destructor for this DSP class.  This destructor will not deallocate
		 * provided queues, mutexes, conditional variables, input data, or
		 * outputted pings.
		 */
		~DSP_V3();

		/**
		 * Starts the processing threads.  This shall start processing the data
		 * samples from the input queue, and placing the detected pings into the
		 * output queue.
		 * @param inputQueue  std::queue of std::complex<double>* pointing at
		 *                    the input data sample array.
		 * @param inputMutex  std::mutex for protecting the inputQueue
		 * @param inputVar    std::condition_variable for notifying when the
		 *                    inputMutex is released
		 * @param outputQueue std::queue of RTT::PingPtr referencing the
		 *                    detected pings.
		 * @param outputMutex std::mutex for protecting the outputQueue
		 * @param outputVar   std::condition_variable for notifying when the
		 *                    outputMutex is released
		 */
		void startProcessing(std::queue<std::complex<double>*>& inputQueue,
			std::mutex& inputMutex, std::condition_variable& inputVar,
			std::queue<RCT::PingPtr>& outputQueue, std::mutex& outputMutex,
			std::condition_variable& outputVar);

		/**
		 * Stops the processing threads, then returns.  This will continue to
		 * process all available samples in the input queue before returning.
		 */
		void stopProcessing();

		/**
		 * Sets the start time of the first received sample in ms since Unix
		 * epoch.  This must be called before the samples of the first ping are
		 * processed.
		 * @param time_start_ms start time of first received sample in ms since
		 *                      Unix epoch.
		 */
		void setStartTime(const std::size_t time_start_ms);

		/**
		 * Sets the output directory and filename format.
		 * @param dir Directory path
		 * @param fmt Format string - this must contain two integer fields,
		 *            first being run number, second being file number.
		 */
		void setOutputDir(const std::string& dir, const std::string& fmt);

		/**
		 * Sets the nominal ping width to be identified.  This will take effect
		 * immediately.
		 * @param width_ms Nominal ping width in ms.
		 */
		void setPingWidth(const std::size_t width_ms);

		/**
		 * Sets the minimum acceptable SNR. This is the minimum SNR in dB above
		 * the noise floor that the ping must be to be accepted.
		 * @param snr minimum SNR in dB above noise floor for ping acceptance.
		 */
		void setMinSNR(const double snr);

		/**
		 * Sets the maximum accepted ping width multiplier.  Ping candidates
		 * with lengths greater than pingWidth_ms * threshold are rejected.
		 * @param threshold Maximum ping width multiplier.  Must be greater than
		 *                  1.0
		 */
		void setHighThreshold(const double threshold);

		/**
		 * Sets the minimum accepted ping width multiplier.  Ping candidates
		 * with lengths smaller than pingWidth_ms * threshold are rejected.
		 * @param threshold Minimum ping width multiplier.  Must be less than 
		 *                  1.0
		 */
		void setLowThreshold(const double threshold);
	private:
		/**
		 * Unpacks std::complex<double> objects and pushes them into the IQ data
		 * queue as a sequence of std::complex<double>
		 * @param i_q Input Queue
		 * @param i_m Input Mutex
		 * @param i_v Input Condition Variable
		 * @param run Run flag
		 */
		void _unpack(std::queue<std::complex<double>*>& i_q, std::mutex& i_m, 
			std::condition_variable& i_v);

		/**
		 * Takes from the input queue a vector of signal power samples and
		 * detects whether or not a ping is present.  Each vector must be of
		 * length target_freqs.size, and each element must correspond to the
		 * frequency power of the corresponding frequency in target_freqs.
		 * 
		 * @param i_q Input queue of target frequency component power
		 * @param i_m Input queue mutex
		 * @param i_v Input queue condition variable
		 * @param o_q Output queue of RTT::PingPtr
		 * @param o_m Output queue mutex
		 * @param o_v Output queue condition variable
		 */
		void classify(std::queue<std::shared_ptr<std::vector<double>>>& i_q, 
			std::mutex& i_m, std::condition_variable& i_v, 
			std::queue<PingPtr>& o_q, std::mutex& o_m, 
			std::condition_variable& o_v);
		/**
		 * Input queue condition variable pointer - use this to kick any 
		 * sleeping threads when DSP_V3::stopProcessing is called.
		 */
		std::condition_variable* _in_v;

		/**
		 * Internal pointer to the integrator thread.
		 */
		std::thread* _thread;

		/**
		 * Internal state flag.  When this is true, threads should continue
		 * to stay alive.  When false, threads should clean up and exit.
		 */
		volatile bool _run = false;

		/**
		 * Time of first sample
		 */
		std::size_t time_start_ms = 0;

		/**
		 * Internal queue - this links the integrator thread to the classifier
		 * thread.  Each element should be the target frequency energy during
		 * the integration period.
		 */
		std::queue<std::shared_ptr<std::vector<double>>> _c_q;

		/**
		 * _c_q mutex
		 */
		std::mutex _c_m;

		/**
		 * _c_q condition variable
		 */
		std::condition_variable _c_v;

		/**
		 * Classifier thread pointer.
		 */
		std::thread* _c_thread;

		/**
		 * Integration window in seconds.  FIXME!!!!
		 */
		const float int_time_s = 6e-3;

		/**
		 * This should hold the number of samples to integrate over to achieve
		 * the integration window.
		 */
		std::size_t int_factor;

		/**
		 * Output directory
		 */
		std::string _output_dir;

		/**
		 * Output file format string.  Should have two fields: an integer for
		 * run number, and an integer for file number.
		 */
		char* _output_fmt;

		/**
		 * The length of the maximization window for determining local noise 
		 * floor
		 */
		std::size_t maximizer_len;

		/**
		 * The length of the median filter for determining noise floor.
		 */
		std::size_t median_len;

		/**
		 * Length of the energy signal buffer for storing samples to measure
		 * amplitude.
		 */
		std::size_t data_len;
		
		// WARNING: these values are overridden in the command line arguments!
		// 2017 data
		// const static std::size_t ping_width_ms = 15;
		// const double MIN_SNR = 0.07;
		// const double HIGH_THRESHOLD = 2;
		// const double LOW_THRESHOLD = 0.75;

		// 2019 test data
		std::size_t ping_width_ms = 36;
		double MIN_SNR = 4;
		double HIGH_THRESHOLD = 1.5;
		double LOW_THRESHOLD = 0.75;

		/**
		 * Internal variable to store nominal ping width in samples after all
		 * processing steps
		 */
		std::size_t ping_width_samp;

		/**
		 * FFT Length
		 */
		const std::size_t FFT_LEN = 2048;

		/**
		 * Internal variable to store the input sample frequency of the 
		 * classifier signal (_c_q)
		 */
		double clfr_input_freq;

		/**
		 * Number of samples per output file
		 */
		const std::size_t SAMPLES_PER_FILE = 64*1024*1024/sizeof(int16_t) / 2;
		
		/**
		 * Number of receive frames per file, driven by DSP_V3::SAMPLES_PER_FILE
		 */
		const std::size_t FRAMES_PER_FILE;

		/**
		 * Determines the maxima of the provided signal, stored in a circular
		 * buffer.  Each element of the circular buffer shall be a 
		 * std::shared_ptr pointing to a std::vector<double> of the same shape
		 * as DSP_V3::target_freqs.  The return vector shall be the same shape
		 * as DSP_V3::target_freqs, and is the row-wise maximum for column
		 * vectors.
		 * @param sig	Input signal
		 * @returns		Row-wise maxima
		 */
		std::shared_ptr<std::vector<double>> max(
			boost::circular_buffer<std::shared_ptr<std::vector<double>>>& sig)
			const;

		/**
		 * Calculates the median of the provided signal.  The provided signal
		 * shall be stored in a circular buffer.  Each element of the circular
		 * buffer shall be a std::shared_ptr pointing to a std::vector<double>>
		 * of the same shape as DSP_V3::target_freqs.  The return vector shall
		 * be the same shape as DSP_V3::target_freqs, and is the row-wise median
		 * for column vectors.
		 * @param	sig	Input signal
		 * @returns		Row-wise median
		 */
		std::vector<double>* sig_median(
			boost::circular_buffer<std::shared_ptr<std::vector<double>>>& sig)
			const;

		/**
		 * Input FFT array
		 */
		fftw_complex* _unpack_fft_in;

		/**
		 * Output FFT array
		 */
		fftw_complex* _unpack_fft_out;

		/**
		 * FFTW plan
		 */
		fftw_plan _unpack_fft_plan;

		/**
		 * element-wise thresholding.  Essentially the boolean signal equivalent
		 * to data > threshold + min_snr.
		 * @param	data		Input data of length n
		 * @param	threshold	Threshold values of length n
		 * @param	min_snr		Minimum acceptance over threshold
		 * @returns				data > threshold + min_snr, length n
		 */
		std::shared_ptr<std::vector<bool>> compare(
			const std::vector<double>& data, 
			const std::vector<double>& threshold, double min_snr) const;

		/**
		 * Checks if the circular buffer has a falling edge at any of the target
		 * bins at the given position.
		 * @param	it	Iterator to the desired check position
		 * @returns		A set of indices that contain a falling edge.
		 */
		std::shared_ptr<std::set<std::size_t>> has_falling_edge(boost::circular_buffer<std::shared_ptr<std::vector<bool>>>::iterator it) const;

		/**
		 * Measures the width of the pulse at the given frequency index.  The end
		 * iterator must point to the end of the pulse.  The begin iterator must
		 * point to before the pulse.  If no positive pulse is found, returns -1,
		 * else the width of the pulse is returned.
		 * @param  pulse_end	Pulse end
		 * @param  sig_begin	Signal start
		 * @param  idx			Frequency index
		 * @return       		Length of pulse, or if no pulse, -1.
		 */
		const std::size_t get_pulse_width(
			boost::circular_buffer<std::shared_ptr<std::vector<bool>>>::iterator pulse_end,
			boost::circular_buffer<std::shared_ptr<std::vector<bool>>>::iterator sig_begin,
			std::size_t idx) const;

		/**
		 * Internal variable for ms per sample at the classifer input
		 */
		double _ms_per_sample;

		/**
		 * Vector of the target frequencies in Hz.
		 */
		const std::vector<std::size_t> target_freqs;

		/**
		 * Length of target_freqs
		 */
		const std::size_t nFreqs;

		/**
		 * Vector of target frequencies as FFT bin indices
		 */
		std::vector<std::size_t> target_bins;

		/**
		 * Calculates the power of the complex input sample.
		 * @param  sample Complex signal amplitude
		 * @return        Signal power
		 */
		const double signal_power(const fftw_complex& sample) const;

		/**
		 * Measures the maximum amplitude of the ping.
		 * @param  start Ping Start
		 * @param  end   Ping End
		 * @param  idx   Frequency index
		 * @return       Maximum amplitude
		 */
		const double get_pulse_magnitude(boost::circular_buffer<std::shared_ptr<std::vector<double>>>::iterator start,
			boost::circular_buffer<std::shared_ptr<std::vector<double>>>::iterator end, std::size_t idx) const;

		/**
		 * Calculates the frequency given the FFT index
		 * @param  idx FFT index
		 * @return     Frequency in Hz
		 */
		const std::size_t idxToFreq(const std::size_t idx) const;

		/**
		 * Input signal sampling frequency.
		 */
		const std::size_t s_freq;

		/**
		 * Input signal center frequency.
		 */
		const std::size_t c_freq;

		/**
		 * @brief Input block size
		 * 
		 * This is the size of data block in samples that should be expected.
		 * 
		 */
		const std::size_t input_block_size;

		/**
		 * @brief Fixed Point Scalar
		 * 
		 * This is the data scaling constant
		 * 
		 */
		const int32_t fixed_point_scalar;

		int input_hwm;
		int power_hwm;
	};
}
#endif