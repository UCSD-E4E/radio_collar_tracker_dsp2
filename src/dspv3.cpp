#include "dspv3.hpp"
#include <fstream>
#include <iostream>
#include <cstdio>
#include <fftw3.h>
#include <cassert>
#include <float.h>
#include <boost/circular_buffer.hpp>
#include <boost/accumulators/accumulators.hpp>
#include <boost/accumulators/statistics.hpp>
#include <stdexcept>
#include "AbstractSDR.hpp"
#include <iomanip>
#include <sys/time.h>
#include <cstdint>
#include <limits>

#define DEBUG

#ifdef DEBUG
#include <fstream>
#endif

namespace RCT{
	DSP_V3::DSP_V3(const std::size_t sampling_freq, 
		const std::size_t center_freq,
		const std::vector<std::size_t>& target_freqs,
		const std::size_t width_ms,
		const double snr,
		const double max_len_threshold,
		const double min_len_threshold,
		const std::size_t input_block_size) : 
	target_freqs(target_freqs),
	nFreqs(target_freqs.size()),
	s_freq{sampling_freq},
	c_freq{center_freq},
	input_block_size(input_block_size),
	FRAMES_PER_FILE(SAMPLES_PER_FILE / input_block_size){

		ping_width_ms = width_ms;
		std::cout << "Constructing DSP with width of " << ping_width_ms << " ms" << std::endl;
		MIN_SNR = snr;
		HIGH_THRESHOLD = max_len_threshold;
		LOW_THRESHOLD = min_len_threshold;
		int_factor = int_time_s * sampling_freq / FFT_LEN;
		std::cout << "DSP int factor: " << int_factor << std::endl;
		clfr_input_freq = (double) sampling_freq / int_factor / FFT_LEN;
		maximizer_len = 0.1 * clfr_input_freq;
		median_len = 1 * clfr_input_freq;
		ping_width_samp = ping_width_ms / 1000. * sampling_freq / FFT_LEN / int_factor;
		data_len = ping_width_samp * 2;
		_ms_per_sample = 1/((double) sampling_freq / int_factor / FFT_LEN) * 1e3;

		#ifdef DEBUG
		std::ofstream _ostr1{"dspv3_freqs.log"};
		#endif


		for(auto it = target_freqs.begin(); it != target_freqs.end(); it++){
			if((std::size_t)std::abs((int64_t)*it - (int64_t)center_freq) > sampling_freq / 2){
				std::cerr << "Target frequency " << *it << " not reachable!" << std::endl;
				throw std::invalid_argument{"Target frequency not reachable!"};
			}
			if(*it >= center_freq){
				// upper half
				std::size_t target_bin = ((double)(*it - center_freq) / (sampling_freq / 2)) * FFT_LEN / 2;
				target_bins.push_back(target_bin);
				#ifdef DEBUG
				_ostr1 << *it << ", " << target_bin << std::endl;
				#endif
			}else{
				// lower half
				std::size_t target_bin = FFT_LEN + ((double)(*it - (double)center_freq) / (sampling_freq / 2)) * FFT_LEN / 2;
				target_bins.push_back(target_bin);
				#ifdef DEBUG
				_ostr1 << *it << ", " << target_bin << std::endl;
				#endif
			}
		}

		_unpack_fft_in = (fftw_complex*)fftw_malloc(sizeof(fftw_complex) * FFT_LEN);
		if(_unpack_fft_in == nullptr){
			std::cout << "Failed to allocate _unpack_fft_in!" << std::endl;
			return;
		}


		_unpack_fft_out = (fftw_complex*)fftw_malloc(sizeof(fftw_complex) * FFT_LEN);
		if(_unpack_fft_out == nullptr){
			std::cout << "Failed to allocation _unpack_fft_out!" << std::endl;
			return;
		}

		if(!fftw_init_threads()){
			std::cout << "Failed to initialize FFTW threads!" << std::endl;
			return;
		}
		fftw_plan_with_nthreads(1);
		_unpack_fft_plan = fftw_plan_dft_1d(FFT_LEN, _unpack_fft_in, _unpack_fft_out,
			FFTW_FORWARD, FFTW_MEASURE);

		#ifdef DEBUG
		_ostr1.close();
		#endif
	}

	DSP_V3::~DSP_V3(){
		fftw_destroy_plan(_unpack_fft_plan);
		fftw_free(_unpack_fft_out);
		fftw_free(_unpack_fft_in);
		fftw_forget_wisdom();
		fftw_cleanup();
		fftw_cleanup_threads();
		if(_output_fmt != nullptr){
			delete[] _output_fmt;
		}
	}

	const std::size_t DSP_V3::idxToFreq(const std::size_t idx) const{
		if(idx > FFT_LEN / 2){
			return -idx / FFT_LEN * s_freq + c_freq;
		}else{
			return idx / FFT_LEN * s_freq + c_freq;
		}
	}

	void DSP_V3::startProcessing(std::queue<std::complex<double>*>& i_q, std::mutex& i_m,
		std::condition_variable& i_v, std::queue<PingPtr>& o_q, std::mutex& o_m,
		std::condition_variable& o_v){
		_in_v = &i_v;
		_run = true;
		if(time_start_ms == 0){
			struct timeval start;
			gettimeofday(&start, NULL);
			time_start_ms = start.tv_sec * 1e3 + start.tv_usec / 1e3;
			std::cout << "Setting DSP Start to " << time_start_ms << " ms" << std::endl;
		}
		_thread = new std::thread(&DSP_V3::_unpack, this, std::ref(i_q), 
			std::ref(i_m), std::ref(i_v));
		_c_thread = new std::thread(&DSP_V3::classify, this, std::ref(_c_q),
			std::ref(_c_m), std::ref(_c_v), std::ref(o_q), std::ref(o_m),
			std::ref(o_v));
		// _fir.start(_iq_data_queue, _iq_mux, _iq_cv, _mag_data_queue, _mag_mux,
		// 	_mag_cv);
		// _int.start(_mag_data_queue, _mag_mux, _mag_cv, _candidate_queue, 
		// 	_can_mux, _can_cv);
		// _clfr.start(_candidate_queue, _can_mux, _can_cv, o_q, o_m, o_v);
	}

	void DSP_V3::stopProcessing(){
		#ifdef DEBUG
		std::cout << "DSP_V3 is stopping:" << std::endl;
		#endif
		_in_v->notify_all();
		_run = false;
		_thread->join();

		_c_v.notify_all();
		_c_thread->join();


		delete _thread;
	}

	std::shared_ptr<std::vector<double>> DSP_V3::max(boost::circular_buffer<std::shared_ptr<std::vector<double>>>& sig) const{
		std::shared_ptr<std::vector<double>> retVal = std::make_shared<std::vector<double>>();
		std::vector<double>& maxVal = *retVal;
		maxVal.resize(sig[0]->size());
		for(std::size_t i = 0; i < maxVal.size(); i++){
			maxVal[i] = -DBL_MAX;
		}
		for(auto it = sig.begin(); it != sig.end(); it++){
			for(std::size_t i = 0; i < maxVal.size(); i++){
				maxVal[i] = std::max((*(*it))[i], maxVal[i]);
			}
		}
		return retVal;
	}

	std::vector<double>* DSP_V3::sig_median(boost::circular_buffer<std::shared_ptr<std::vector<double>>>& sig) const{
		
		boost::accumulators::accumulator_set<double, boost::accumulators::features<boost::accumulators::tag::median> > acc[nFreqs];
		for(auto it = sig.begin(); it != sig.end(); it++){
			std::shared_ptr<std::vector<double>> ptr = *it;
			std::vector<double>& vec= *ptr;
			for(std::size_t i = 0; i < nFreqs; i++){
				acc[i](vec[i]);
			}
		}
		std::vector<double>* retval = new std::vector<double>{};
		std::vector<double>& median = *retval;
		median.resize(nFreqs);
		for(std::size_t i = 0; i < nFreqs; i++){
			median[i] = boost::accumulators::median(acc[i]);
		}
		return retval;
	}

	std::size_t _debug_ctr = 0;

	std::shared_ptr<std::vector<bool>> DSP_V3::compare(
		const std::vector<double>& data,
		const std::vector<double>& threshold, const double min_snr) const{

		std::shared_ptr<std::vector<bool>> retval(new std::vector<bool>(nFreqs));
		for(std::size_t i = 0; i < nFreqs; i++){
			(*retval)[i] = (data[i] > (threshold[i] + min_snr));
		}
		return retval;
	}

	std::shared_ptr<std::set<std::size_t>> DSP_V3::has_falling_edge(
		boost::circular_buffer<std::shared_ptr<std::vector<bool>>>::iterator it) const{
		std::vector<bool>& s1 = **(it - 1);
		std::vector<bool>& s2 = **it;

		std::shared_ptr<std::set<std::size_t>> retval_ptr = std::make_shared<std::set<std::size_t>>();
		std::set<std::size_t>& retval = *retval_ptr;

		for(std::size_t i = 0; i < nFreqs; i++){
			if(s1[i] == true && s2[i] == false){
				retval.insert(i);
			}
		}
		return retval_ptr;
	}

	bool is_rising_edge(boost::circular_buffer<std::shared_ptr<std::vector<bool>>>::iterator it, std::size_t i){
		if((**(it-1))[i] == false && (**it)[i] == true){
			return true;
		}else{
			return false;
		}
	}

	const double DSP_V3::get_pulse_magnitude(
			boost::circular_buffer<std::shared_ptr<std::vector<double>>>::iterator start,
			boost::circular_buffer<std::shared_ptr<std::vector<double>>>::iterator end, 
			std::size_t idx) const{
		double max_amplitude = std::numeric_limits<double>::lowest();
		for(;start != end; start++){
			if((**start)[idx] > max_amplitude){
				max_amplitude = (**start)[idx];
			}
		}
		return max_amplitude;
	}

	const std::size_t DSP_V3::get_pulse_width(
		boost::circular_buffer<std::shared_ptr<std::vector<bool>>>::iterator end,
		boost::circular_buffer<std::shared_ptr<std::vector<bool>>>::iterator begin,
		std::size_t i) const{

		std::size_t width = 0;
		if(end == begin){
			return -1;
		}

		while(!is_rising_edge(end, i)){
			end--;
			width++;
			if(end == begin){
				return -1;
			}
		}
		return width;
	}

	void DSP_V3::classify(std::queue<std::shared_ptr<std::vector<double>>>& i_q, std::mutex& i_m,
		std::condition_variable& i_v, std::queue<PingPtr>& o_q, std::mutex& o_m,
		std::condition_variable& o_v){
		
		// Local vars
		boost::circular_buffer<std::shared_ptr<std::vector<double>>> data{data_len};
		boost::circular_buffer<std::shared_ptr<std::vector<double>>> pk_hist{maximizer_len};
		boost::circular_buffer<std::shared_ptr<std::vector<double>>> peaks{median_len};
		

		std::size_t id_len = (std::size_t)(clfr_input_freq * 0.5);
		boost::circular_buffer<std::shared_ptr<std::vector<bool>>> id_signal{id_len};
		#ifdef DEBUG
		std::cout << id_len << " len id_len" << std::endl;
		std::cout << data_len << " len data" << std::endl;
		std::cout << maximizer_len << " len pk_hist" << std::endl;
		std::cout << median_len << " len peaks" << std::endl;
		#endif
		for(std::size_t i = 0; i < id_len; i++){
			std::shared_ptr<std::vector<bool>> id_sig(new std::vector<bool>(nFreqs));
			id_signal.push_back(id_sig);
		}

		std::size_t signal_idx = 0;
		std::size_t out_count = 0;
		std::size_t sample_counter = 0;
		std::cout << "DSP is alive" << std::endl;

		#ifdef DEBUG
		std::ofstream _ostr1{"classifier_in.log"};
		std::ofstream _ostr2{"classifier_compare.log"};
		std::ofstream _ostr3{"classifier_threshold.log"};
		// std::ofstream _ostr4{"classifier_sig_fft.log"};
		// std::ofstream _ostr5{"classifier_sig_in.log"};
		// std::ofstream _ostr6{"classifier_test.log"};
		#endif

		std::vector<double>* threshold_ptr = new std::vector<double>(nFreqs, 100);

		while(_run || !i_q.empty()){
			std::unique_lock<std::mutex> in_lock(i_m);
			if(i_q.empty()){
				i_v.wait(in_lock);
			}

			if(!i_q.empty()){
				std::shared_ptr<std::vector<double>> sig = i_q.front();
				i_q.pop();
				sample_counter++;

				if((*threshold_ptr)[0] != 100){
					data.push_back(sig);
					pk_hist.push_back(sig);
					peaks.push_back(max(pk_hist));
					delete threshold_ptr;
					threshold_ptr = sig_median(peaks);
				}else{
					for(std::size_t j = 0; j < median_len; j++){
						peaks.push_back(sig);
					}
					for(std::size_t j = 0; j < ping_width_samp; j++){
						pk_hist.push_back(sig);
					}
					for(std::size_t j = 0; j < data_len; j++){
						data.push_back(sig);
					}
					delete threshold_ptr;
					threshold_ptr = new std::vector<double>(*sig);
				}
				std::vector<double>& threshold = *threshold_ptr;

				#ifdef DEBUG
				for(std::size_t i = 0; i < nFreqs; i++){
					_ostr1 << (*sig)[i] << ", ";
					_ostr3 << threshold[i] + MIN_SNR << ", ";
				}
				_ostr1 << std::endl;
				_ostr3 << std::endl;
				#endif


				signal_idx++;
				std::shared_ptr<std::vector<bool>> sig_cmp = compare(*sig, threshold, MIN_SNR);
				id_signal.push_back(sig_cmp);
				#ifdef DEBUG
				for(std::size_t i = 0; i < nFreqs; i++){
					if((*sig_cmp)[1]){
						_ostr2 << 1.0 << ", ";
					}else{
						_ostr2 << 0.0 << ", ";
					}
				}
				_ostr2 << std::endl;
				#endif

				// std::cout << "Fail after falling edge" << std::endl;
				std::shared_ptr<std::set<std::size_t>> edge_ptr = has_falling_edge(id_signal.end() - 1);
				if(!edge_ptr->empty()){
					std::set<std::size_t>& edges = *edge_ptr;
					for(auto it = edges.begin(); it != edges.end(); it++){
						std::size_t pulse_width = get_pulse_width(id_signal.end() - 1, id_signal.begin(), *it);
						if(pulse_width + 1 > data.size()){
							pulse_width = data.size() - 1;
						}
						auto ping_start = data.end() - 1 - pulse_width;
						auto ping_end = data.end() - 1;
						double ping_start_ms = (std::size_t)((signal_idx - 
							pulse_width) * _ms_per_sample);
						const double amplitude = get_pulse_magnitude(ping_start, ping_end, *it);
						if(pulse_width < LOW_THRESHOLD * ping_width_samp){
							#ifdef DEBUG
							std::cout << "Ping " << out_count << " at " << std::setprecision(0) <<
							(ping_start_ms + time_start_ms) / 1e3 << "s " << std::setprecision(3) <<
							", amplitude " << amplitude << ", threshold: " << threshold[*it] + MIN_SNR <<
							", width: " << pulse_width * _ms_per_sample <<
							", freq: " << std::fixed << std::setprecision(0) <<
							target_freqs[*it] <<
							", bin: " << *it << 
							" was rejected for being too short!" << std::endl;
							#endif
							continue;
						}
						if(pulse_width > HIGH_THRESHOLD * ping_width_samp){
							#ifdef DEBUG
							std::cout << "Ping " << out_count << " at " << std::setprecision(0) <<
							(ping_start_ms + time_start_ms) / 1e3 << "s " << std::setprecision(3) <<
							", amplitude " << amplitude << ", threshold: " << threshold[*it] + MIN_SNR <<
							", width: " << pulse_width * _ms_per_sample <<
							", freq: " << std::fixed << std::setprecision(0) <<
							target_freqs[*it] <<
							", bin: " << *it << 
							" was rejected for being too long!" << std::endl;
							#endif
							continue;
						}

						// std::cout << "Fail after pulse magnitude" << std::endl;

						PingPtr ping = std::make_shared<Ping>(ping_start_ms + time_start_ms, amplitude, target_freqs[*it]);

						{
							std::unique_lock<std::mutex> out_lock(o_m);
							o_q.push(ping);
							out_count++;
							out_lock.unlock();
							o_v.notify_all();
							#ifdef DEBUG
							std::cout << "Ping " << out_count << 
								" at " << std::setprecision(3) << 
								ping->time_ms << "ms " << 
								", amplitude " << amplitude << 
								", threshold: " << threshold[*it] + MIN_SNR << 
								", width: " << pulse_width * _ms_per_sample << 
								", freq: " << std::fixed << std::setprecision(0) << 
								target_freqs[*it] << 
								", idx: " << *it <<
								", bin: " << target_bins[*it] << std::endl;
							#endif
						}
					}
				}
			}
		}
		#ifdef DEBUG
		// std::cout << "Threshold at " << threshold + MIN_SNR << std::endl;
		_ostr1.close();
		_ostr2.close();
		_ostr3.close();
		// _ostr4.close();
		// _ostr5.close();
		// _ostr6.close();
		#endif
		std::cout << "Classifier received " << sample_counter << " samples, estimated " << sample_counter * _ms_per_sample / 1e3 << " s" << std::endl;
	}

	const double DSP_V3::pow(const fftw_complex& sample) const{
		double real = sample[0];
		double imag = sample[1];
		std::complex<double> val{real, imag};
		return std::abs(val) * std::abs(val);
	}

	void DSP_V3::_unpack(std::queue<std::complex<double>*>& i_q, std::mutex& i_m, 
		std::condition_variable& i_v){
		
		// Local vars
		std::vector<std::complex<double>> double_data{};
		
		std::size_t file_counter = 1;
		std::size_t sample_counter = 0;
		std::size_t frame_counter = 0;
		std::size_t integrate_counter = 0;
		std::size_t fft_counter = 0;
		std::size_t write_counter = 0;
		std::size_t buffer_counter = 0;
		char fname[1024];
		std::ofstream data_str;
		std::complex<double>* leftoverData = new std::complex<double>[this->input_block_size];
		std::size_t leftoverCount = 0;


		if(!_output_dir.empty()){
			sprintf(fname, _output_fmt, file_counter);
			data_str.open(fname, std::ofstream::binary);
			#ifdef DEBUG
			std::cout << "Opening initial " << fname << std::endl;
			#endif
		}

		std::shared_ptr<std::vector<double>> integrator = std::make_shared<std::vector<double>>();
		integrator->resize(nFreqs);
		for(size_t i = 0; i < nFreqs; i++){
			(*integrator)[i] = 0;
		}

		int16_t* int_buf = new int16_t[2 * this->input_block_size];
		#ifdef DEBUG
		std::ofstream _ostr1{"unpack_in.log"};
		#endif

		// Loop
		while(_run || !i_q.empty()){
			// get data
			std::unique_lock<std::mutex> inputLock(i_m);
			if(i_q.empty()){
				i_v.wait(inputLock);
			}
			if(!i_q.empty()){
				const std::complex<double>* dataObj = i_q.front();
				i_q.pop();
				buffer_counter++;
				inputLock.unlock();
				std::size_t dataIdx = 0;

				for(dataIdx; dataIdx < this->input_block_size; dataIdx += FFT_LEN)
				{
					if(integrate_counter >= int_factor && nFreqs > 0){
						// push integrator to queue
						std::unique_lock<std::mutex> cLock(_c_m);
						_c_q.push(integrator);
						cLock.unlock();
						_c_v.notify_all();
						integrator.reset(new std::vector<double>());
						integrator->resize(nFreqs);
						for(size_t i = 0; i < nFreqs; i++){
							(*integrator)[i] = 0;
						}
						integrate_counter = 0;
					}
					integrate_counter += 1;
					sample_counter += FFT_LEN;


					// #ifdef DEBUG
					// for(std::size_t i = 0; i < FFT_LEN; i++){
					// 	_ostr1 << dataObj[dataIdx + i].real();
					// 	if(dataObj[dataIdx + i].imag() >= 0){
					// 		_ostr1 << '+';
					// 	}
					// 	_ostr1 << dataObj[i].imag() << "i" << std::endl;
					// }
					// #endif

					for(size_t i = 0; i < FFT_LEN; i++){
						_unpack_fft_in[i][0] = dataObj[dataIdx + i].real();
						_unpack_fft_in[i][1] = dataObj[dataIdx + i].imag();
					}
					fftw_execute(_unpack_fft_plan);
					fft_counter++;
					for(size_t i = 0; i < nFreqs; i++){
						(*integrator)[i] += pow(_unpack_fft_out[target_bins[i]]);
					}

				}
				if(!_output_dir.empty()){
					for(std::size_t i = 0; i < this->input_block_size; i++){
						int_buf[2*i] = dataObj[i].real() * INT16_MAX;
						int_buf[2*i + 1] = dataObj[i].imag() * INT16_MAX;
					}
					data_str.write((char*)int_buf, this->input_block_size * 2 * sizeof(int16_t));
					data_str.flush();
					if(frame_counter++ == FRAMES_PER_FILE){
						write_counter += data_str.tellp();
						data_str.close();
						sprintf(fname, _output_fmt, ++file_counter);
						#ifdef DEBUG
						std::cout << "Opening " << fname << std::endl;
						#endif
						data_str.open(fname, std::ofstream::binary);
						frame_counter = 0;
					}
				}
				// Handle leftover data
				for(dataIdx; dataIdx < this->input_block_size; dataIdx++)
				{
					std::cout << "Leftover data in pack!" << std::endl;
				}
				delete[] dataObj;
			}

		}
		if(!_output_dir.empty()){
			data_str.close();
		}
		std::cout << "Unpack received " << sample_counter << " samples, estimated " << (double)sample_counter / s_freq << " seconds of data" << std::endl;
		std::cout << "Unpack ran " << fft_counter << " ffts" << std::endl;
		std::cout << "Unpack wrote " << write_counter / 1024 / 1024 << " MB, estimated " << (double)write_counter / 4 / s_freq << " seconds of data" << std::endl;
		delete[] int_buf;
		delete[] leftoverData;
		#ifdef DEBUG
		_ostr1.close();
		#endif
	}

	void DSP_V3::setStartTime(const std::size_t start_time_ms){
		time_start_ms = start_time_ms;
	}

	void DSP_V3::setOutputDir(const std::string& dir, const std::string& fmt){
		_output_dir = dir;
		_output_fmt = new char[fmt.length() + dir.length() + 1];
		sprintf(_output_fmt, "%s/%s", dir.c_str(), fmt.c_str());
	}

	void DSP_V3::setPingWidth(const std::size_t width_ms){
		ping_width_ms = width_ms;
	}

	void DSP_V3::setMinSNR(const double snr){
		MIN_SNR = snr;
	}

	void DSP_V3::setHighThreshold(const double threshold){
		HIGH_THRESHOLD = threshold;
	}

	void DSP_V3::setLowThreshold(const double threshold){
		LOW_THRESHOLD = threshold;
	}
}