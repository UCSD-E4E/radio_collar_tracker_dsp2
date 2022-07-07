#include "sdr.hpp"
#include "iq_data.hpp"
#include <syslog.h>
#include <signal.h>
#include <uhd.h>
#include <sys/time.h>
#include <error.h>
#include <iostream>
#include <stdexcept>
#include <complex>
#include <thread>
#include <memory>
#include <condition_variable>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/syscall.h>

namespace RCT{
	USRP::USRP(double gain, long int rate, long int freq) : device_args(""), 
			subdev("A:A"), ant("RX2"), ref("internal"), cpu_format("fc64"), 
			wire_format("sc16"), channel{0}, if_gain(gain), rx_rate(rate), 
			rx_freq(freq), _start_ms(0){
		double value{0};
		//create a usrp device
		syslog(LOG_DEBUG, "Creating USRP with args \"%s\"...\n", 
			device_args.c_str());
		uhd_error error = uhd_usrp_make(&usrp, device_args.c_str());
		if(error != UHD_ERROR_NONE){
			syslog(LOG_ERR, "UHD Error: %s", uhd_strerror(error).c_str());
			throw std::runtime_error(uhd_strerror(error).c_str());
		}
		uhd_rx_streamer_make(&rx_streamer);

		//set the sample rate
		if (rate <= 0.0) {
			syslog(LOG_ERR, "Please specify a valid sample rate\n");
			throw std::invalid_argument("invalid sample rate");
		}

		// set sample rate
		syslog(LOG_DEBUG, "Setting RX Rate: %f Msps...\n", (rate / 1e6));
		uhd_usrp_set_rx_rate(usrp, rate, channel);
		uhd_usrp_get_rx_rate(usrp, channel, &value);
		syslog(LOG_DEBUG, "Actual RX Rate: %f Msps...\n", (value / 1e6));

		if((value / rate) - 1.0 > 0.01){
			syslog(LOG_WARNING, "WARNING: RX rate not correctly set, actual is %f!", value);
		}

		// set the rf gain
		syslog(LOG_DEBUG, "Setting RX Gain: %f dB...\n", gain);
		uhd_usrp_set_rx_gain(usrp, gain, channel, ""); 
		uhd_usrp_get_rx_gain(usrp, channel, "", &value);
		syslog(LOG_DEBUG, "Actual RX Gain: %f dB...\n", value);
		
		// set freq
		syslog(LOG_DEBUG, "Setting RX Freq: %f MHz...\n", (freq / 1e6));
		uhd_tune_request_t tune_request{};
		tune_request.target_freq = freq;
		tune_request.rf_freq_policy = UHD_TUNE_REQUEST_POLICY_AUTO;
		tune_request.dsp_freq_policy = UHD_TUNE_REQUEST_POLICY_AUTO;
		
		uhd_tune_result_t tune_result{};

		uhd_usrp_set_rx_freq(usrp, &tune_request, channel, &tune_result);
		syslog(LOG_DEBUG, "Actual RX Freq: %f MHz...\n", (tune_result.actual_rf_freq / 1e6));

	}

	void USRP::startStreaming(std::queue<std::complex<double>*>& queue, std::mutex& mutex, 
		std::condition_variable& var){
		output_queue = &queue;
		output_mutex = &mutex;
		output_var = &var;
		run = true;
		stream_thread = new std::thread(&USRP::streamer, this);
	}

	void USRP::stopStreaming(){
		run = false;
		stream_thread->join();
		delete stream_thread;
	}

	std::string USRP::uhd_strerror(uhd_error err){
		switch(err){
			case UHD_ERROR_NONE:
				return "None";
			case UHD_ERROR_INVALID_DEVICE:
				return "Invalid device arguments";
			case UHD_ERROR_INDEX:
				return "uhd::index_error";
			case UHD_ERROR_KEY:
				return "uhd::key_error";
			case UHD_ERROR_NOT_IMPLEMENTED:
				return "uhd::not_implemented_error";
			case UHD_ERROR_USB:
				return "uhd::usb_error";
			case UHD_ERROR_IO:
				return "uhd::io_error";
			case UHD_ERROR_OS:
				return "uhd::os_error";
			case UHD_ERROR_ASSERTION:
				return "uhd::assertion_error";
			case UHD_ERROR_LOOKUP:
				return "uhd::lookup_error";
			case UHD_ERROR_TYPE:
				return "uhd::type_error";
			case UHD_ERROR_VALUE:
				return "uhd::value_error";
			case UHD_ERROR_RUNTIME:
				return "uhd::runtime_error";
			case UHD_ERROR_ENVIRONMENT:
				return "uhd::environment_error";
			case UHD_ERROR_SYSTEM:
				return "uhd::system_error";
			case UHD_ERROR_EXCEPT:
				return "uhd::exception";
			case UHD_ERROR_BOOSTEXCEPT:
				return "A boost::exception was thrown";
			case UHD_ERROR_STDEXCEPT:
				return "A std::exception was thrown.";
			case UHD_ERROR_UNKNOWN:
			default:
				return "An unknown error was thrown.";
		}
	}

	void USRP::streamer(){
		#ifdef DEBUG
		std::cout << "SDR Thread: " << syscall(__NR_gettid) << std::endl;
		#endif

		// Configure streamer
		syslog(LOG_DEBUG, "sdr streamer starting");
		uhd_error retval;
		uhd_stream_args_t stream_args{};
		stream_args.cpu_format = new char[1024];
		std::strcpy(stream_args.cpu_format, cpu_format.c_str());
		stream_args.otw_format = new char[1024];
		std::strcpy(stream_args.otw_format, wire_format.c_str());
		stream_args.args = new char[1024];
		std::strcpy(stream_args.args, "fullscale=1.0, num_recv_frames=512");
		size_t* channel_nums = new size_t[1];
		channel_nums[0] = 0;
		stream_args.channel_list = channel_nums;
		stream_args.n_channels = 1;
		
		syslog(LOG_DEBUG, "sdr streamer creating receive stream");
		retval = uhd_usrp_get_rx_stream(usrp, &stream_args, rx_streamer);
		if(retval != UHD_ERROR_NONE){
			syslog(LOG_ERR, "Error: %s", uhd_strerror(retval).c_str());
			char* errbuf = new char[1024];
			retval = uhd_get_last_error(errbuf, 1024);
			syslog(LOG_ERR, "UHD reports %s", errbuf);
			std::cout << "UHD Error! " << errbuf << std::endl;
			delete[] errbuf;
			return;
		}
		
		uhd_stream_cmd_t stream_cmd{};
		stream_cmd.stream_mode = UHD_STREAM_MODE_START_CONTINUOUS;
		stream_cmd.stream_now = true;
		
		uhd_rx_metadata_handle md{};
		uhd_rx_metadata_make(&md);
		size_t total_samples = 0;

		assert(run);

		struct timeval starttime;
		struct timeval stoptime;
		struct timeval finishtime;

		gettimeofday(&starttime, NULL);
		gettimeofday(&stoptime, NULL);
		gettimeofday(&finishtime, NULL);

		size_t num_samps = 0;
		uhd_rx_metadata_error_code_t error_code;

		syslog(LOG_DEBUG, "sdr streamer issuing stream command");
		uhd_rx_streamer_issue_stream_cmd(rx_streamer, &stream_cmd);
		struct timeval reftime;
		gettimeofday(&reftime, NULL);
		uhd_usrp_set_time_now(usrp, reftime.tv_sec, (double) reftime.tv_usec / 1e6, 0);

		syslog(LOG_DEBUG, "Starting main loop");
		#ifdef DEBUG
		std::cout << "Starting SDR main loop" << std::endl;
		#endif


		double time_inc = 0;
		double time_inc1 = 0;
		double time_reset = 0;
		uint64_t time_count = 0;
		uint64_t prev_finish = 0;
		
		while(run){
			std::complex<double>* raw_buffer = new std::complex<double>[rx_buffer_size * 2];
			
			gettimeofday(&starttime, NULL);

			// get a buffer of data from rx_streamer and put in raw_buffer
			uhd_rx_streamer_recv(rx_streamer, (void**) &raw_buffer, rx_buffer_size, &md, 1.0, false, &num_samps);
			gettimeofday(&stoptime, NULL);

			prev_finish = finishtime.tv_sec * 1e6 + finishtime.tv_usec;

			uhd_rx_metadata_error_code(md, &error_code);

			if(error_code == UHD_RX_METADATA_ERROR_CODE_TIMEOUT){
				syslog(LOG_NOTICE, "Timeout while streaming");
			}
			if(error_code == UHD_RX_METADATA_ERROR_CODE_OVERFLOW){
				syslog(LOG_EMERG, "Overflow indicator");
				// raise(SIGTERM);
				// return;
				break;
			}
			if(error_code != UHD_RX_METADATA_ERROR_CODE_NONE){
				char* strbuf = new char[1024];
				uhd_rx_metadata_strerror(md, strbuf, 1024);
				syslog(LOG_ERR, "Receiver error: %s", strbuf);
				delete[] strbuf;
			}
			
			// std::vector<std::complex<double>>& double_data = *(new std::vector<std::complex<double>>());
			// double_data.resize(rx_buffer_size);
			if(_start_ms == 0){
				_start_ms = starttime.tv_sec * 1e3 + starttime.tv_usec * 1e-3;
			}

			total_samples += num_samps;

			std::unique_lock<std::mutex> guard(*output_mutex);
			output_queue->push(raw_buffer);
			guard.unlock();
			output_var->notify_all();
			gettimeofday(&finishtime, NULL);

			uint64_t starttimeus = starttime.tv_sec * 1e6 + starttime.tv_usec;
			uint64_t stoptimeus = stoptime.tv_sec * 1e6 + stoptime.tv_usec;
			uint64_t finishtimeus = finishtime.tv_sec * 1e6 + finishtime.tv_usec;

			// syslog(LOG_DEBUG, "%lu us for record, %lu us for queue\n", stoptimeus - starttimeus, finishtimeus - stoptimeus);
			time_inc += stoptimeus - starttimeus;
			time_inc1 += finishtimeus - stoptimeus;
			time_reset += starttimeus - prev_finish;
			time_count++; 

		}
		#ifdef DEBUG
		std::cout << time_inc / time_count << " us for recording " << rx_buffer_size << " samples" << std::endl;
		std::cout << time_reset / time_count << " us for reset " << rx_buffer_size << " samples" << std::endl;
		std::cout << ((time_inc / time_count + time_inc1 / time_count) / 1e6) / ((double)rx_buffer_size / rx_rate) * 100 << "% of record time" << std::endl;
		std::cout << time_inc1 / time_count << " us for queue" << std::endl;
		#endif
		syslog(LOG_DEBUG, "Stopping loop");

		stream_cmd.stream_mode =  UHD_STREAM_MODE_STOP_CONTINUOUS;
		uhd_rx_streamer_issue_stream_cmd(rx_streamer, &stream_cmd);

		std::cout << "SDR Received "<< total_samples << " samples, " << (double)total_samples / rx_rate << " seconds of data" << std::endl;
		uhd_rx_metadata_free(&md);

		delete[] channel_nums;
		delete[] stream_args.args;
		delete[] stream_args.otw_format;
		delete[] stream_args.cpu_format;
	}

	USRP::~USRP(){
		uhd_usrp_free(&usrp);
		uhd_rx_streamer_free(&rx_streamer);
	}

	USRP::USRP(): device_args("num_recv_frames=512"), 
			subdev("A:A"), ant("RX2"), ref("internal"), cpu_format("sc16"), 
			wire_format("sc16"), channel{0}, if_gain(0), rx_rate(2000000), 
			rx_freq{0}{
		uhd_error error = uhd_usrp_make(&usrp, device_args.c_str());
		if(error != UHD_ERROR_NONE){
			syslog(LOG_ERR, "UHD Error: %s", uhd_strerror(error).c_str());
		}
		uhd_rx_streamer_make(&rx_streamer);


	}

	const size_t USRP::getStartTime_ms() const{
		return _start_ms;
	}
}