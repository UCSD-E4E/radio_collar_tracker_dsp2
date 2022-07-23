#include "hackrf.hpp"

#include <syslog.h>
#include <iostream>

#include <sys/time.h>

namespace RCT
{
    int rx_callback(hackrf_transfer* pTransfer)
    {
        HackRF* ctx = (HackRF*) pTransfer->rx_ctx;
        if(NULL != ctx)
        {
            ctx->rx_callback(pTransfer);
            return 0;
        }
        else
        {
            return 1;
        }
        return 0;
    }

    HackRF::HackRF(double gain, uint64_t rate, uint64_t freq) :
        device(0),
        total_rx_samples(0),
        sampling_rate(rate)
    {
        int retval;
        syslog(LOG_DEBUG, "Creating HackRF\n");

        // Initialize library
        retval = hackrf_init();
        if(HACKRF_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Failed to initialize HackRF: %s\n", hackrf_error_name((hackrf_error) retval));
            throw std::runtime_error("Failed to initialize HackRF");
        }

        // Create the handle
        retval = hackrf_open(&device);
        if(HACKRF_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Failed to open HackRF: %s\n", hackrf_error_name((hackrf_error) retval));
            throw std::runtime_error("Failed to open HackRF");
        }

        // set the sample rate
        retval = hackrf_set_sample_rate(device, rate);
        if(HACKRF_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Failed to set sampling rate: %s\n", hackrf_error_name((hackrf_error) retval));
            throw std::runtime_error("Failed to set HackRF sampling rate");
        }

        // Set the gain
        retval = hackrf_set_lna_gain(device, gain);
        if(HACKRF_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Failed to set LNA gain: %s\n", hackrf_error_name((hackrf_error) retval));
            throw std::runtime_error("Failed to set HackRF gain");
        }
        retval = hackrf_set_vga_gain(device, 62);
        if(HACKRF_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Failed to set VGA gain: %s\n", hackrf_error_name((hackrf_error)retval));
            throw std::runtime_error("Failed to set HacRF VGA gain");
        }
        
        // Set the center frequency
        retval = hackrf_set_freq(device, freq);
        if(HACKRF_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Failed to set center freq: %s\n", hackrf_error_name((hackrf_error) retval));
            throw std::runtime_error("Failed to set HackRF center freq");
        }
    }

    HackRF::~HackRF()
    {
        int retval;
        retval = hackrf_close(device);
        if(HACKRF_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Unable to close HackRF: %s\n", hackrf_error_name((hackrf_error)retval));
        }
        hackrf_exit();
    }

    void HackRF::startStreaming(std::queue<std::complex<double>*>& queue, std::mutex& mutex, std::condition_variable& cond_var)
    {
        int retval;
        struct timeval startime;

        this->output_queue = &queue;
        this->output_mutex = &mutex;
        this->output_var = &cond_var;

        gettimeofday(&startime, NULL);
        retval = hackrf_start_rx(device, RCT::rx_callback, this);
        if(HACKRF_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Failed to start receive: %s\n", hackrf_error_name((hackrf_error)retval));
            throw std::runtime_error("Failed to start received");
        }
        _start_ms = startime.tv_sec * 1e3 + startime.tv_usec * 1e-3;
    }

    void HackRF::stopStreaming()
    {
        int retval;

        retval = hackrf_stop_rx(device);
        if(HACKRF_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Failed to stop rx: %s\n", hackrf_error_name((hackrf_error)retval));
            throw std::runtime_error("Failed to stop rx");
        }

        std::cout << "SDR Received " << this->total_rx_samples << " samples, " 
            << (double)this->total_rx_samples / this->sampling_rate 
            << " seconds of data" << std::endl;
    }

    const size_t HackRF::getStartTime_ms() const{
        return this->_start_ms;
    }

    void HackRF::rx_callback(hackrf_transfer* pTransfer)
    {
        int8_t* pData;

        pData = (int8_t*) pTransfer->buffer;

        total_rx_samples += pTransfer->valid_length / 2;

        std::complex<double>* output_buffer = new std::complex<double>[pTransfer->valid_length];

        for(size_t idx = 0; idx < pTransfer->valid_length / 2; idx++)
        {
            output_buffer[idx] = std::complex<double>(pData[idx * 2] / 128.0, pData[idx * 2 + 1] / 128.0);
        }
        std::unique_lock<std::mutex> guard(*this->output_mutex);
        output_queue->push(output_buffer);
        guard.unlock();
        output_var->notify_all();
    }

}